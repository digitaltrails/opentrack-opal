#!/usr/bin/python3
"""
opentrack-stick - opentrack to Linux HID stick events
=====================================================

Translate opentrack UDP-output to Linux-HID joystick events.

Usage:
======

    python3 opentrack-stick.py [-d] [-q]

Optional Arguments
------------------

    -a <zone>    Auto-center (press middle mouse button) if all tracking
                 values are in the -zone..+zone (default 0.0, suggest 5.0)
    -t <float>   Auto-center required seconds for all values remain in
                 the zone for this many millis (default 1.0)
    -i <ip-addr> The ip-address to listen on for the UDP feed from opentrack
    -p <port>    The UDP port number to listen on for the UDP feed from opentrack
    -d           Output joystick event x, y, z values to stdout for debugging purposes.
    -q           Training: limit each axis to large changes to eliminate other-axis "noise"
                 when mapping an axis within a game.

Description
===========

opentrack-stick listens for opentrack-output UDP-packets and uses evdev
to inject them into Linux input subsystem as HID joystick events.

The evdev joystick events are introduced at the HID device level and are
independent of X11/Wayland, applications cannot differentiate them
from ordinary joystick events.  This means opentrack-stick will work in
any application, including environments such as Steam Proton.

Auto-centering can be enabled for applications where the center
may drift from the true-center AND the application supports a
binding for a re-center command.  Bind the application's re-center
command to the middle mouse button and enable auto-centering by
using the opentrack-mouse -a option. When enabled, opentrack-mouse
will pull the stick's trigger when the input-values from
opentrack remain in the middle zone for the time specified
by the -t option.

Quick Start
===========

Get the python (python-3) ebdev library:

    pip install ebdev

Requires udev rule for access:

    sudo cat > /etc/udev/rules.d/65-opentrack-evdev.rules <EOF
    KERNEL=="event*", SUBSYSTEM=="input", ATTRS{name}=="opentrack*",  TAG+="uaccess"
    EOF
    sudo udevadm control --reload-rules ; udevadm trigger

Run this script:

    python3 opentrack-stick.py

Start opentrack; select Output `UDP over network`; configure the
output option to IP address 127.0.0.1, port 5005; start tracking.
Now start a game/application that makes use of a joystick;
in the game/application choose the joystick called `openstack-stick`.
If the app/game requires you to configure the stick, you may find the
`-q` training option useful.

Opentrack Protocol
==================

Each opentrack UDP-Output packet contains 6 little-endian
doubles: x, y, z, yaw, pitch, and roll.

Limitations
===========

Opentrack-stick is relatively new and hasn't undergone sufficient
testing to establish what is required to make it of practical use.
It has not been tested in a gaming environment, it has only been
tested in a desktop test rig.

Some games support specific models of controller, they may not
recognise some aspects of the `opentrack-stick` controller.  In
those cases, you may need to search for ways to define new
controllers.

Testing
=======

The following test rig can be employed:

1. Connect a real stick and use it as the input to `opentrack`.
2. Send the `opentrack` `UPD-Output` to UDP 127.0.0.1 Port 5005.
3. Start `opentrack-stick`.
4. Start a second `opentrack` with a `UDP-Input` foo 127.0.0.1 Port 5005,
   but don't connect any outputs.
5  On the second `opentrack`, under `Input` `Linux joystick input`, click
   the right options box, the dropdown of joystick choices should include
   `opentrack-stick` as a possible joystick.
6. Start the second `opentrack`.
7. Use the first opentrack to guide your use of the real stick, and
   use the second opentrack to confirm that the correct events are passed.


Licence
=======

Copyright 2022 Michael Hamilton

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import datetime
import socket
import struct
import sys
import time
from pathlib import Path

import evdev
from evdev import AbsInfo

UDP_IP = "127.0.0.1"
UDP_PORT = 5005


class OpenTrackStick:

    def __init__(self, debug=False, training=False, auto_center=0.0, auto_center_secs=1.0):
        self.debug = debug
        self.training = training
        self.last_time = time.time_ns()
        self.previous = None
        self.auto_center = auto_center
        self.auto_center_ns = auto_center_secs * 1_000_000_000
        self.centered = True
        self.center_arrival_time_ns = 0
        self.previous_training_value = 0
        print(f"Training: {self.training}")
        print(f"Auto center when all values in zone: -{auto_center}..+{auto_center}"
              f" for {auto_center_secs} second(s)\n" if not self.training and auto_center > 0.0 else "Auto center: off")
        self.order = ('x', 'y', 'z', 'yaw', 'pitch', 'roll')
        self.abs_caps = [
            (evdev.ecodes.ABS_HAT0X, AbsInfo(value=0, min=-90, max=90, fuzz=0, flat=0, resolution=0)),
            (evdev.ecodes.ABS_HAT0Y, AbsInfo(value=0, min=-90, max=90, fuzz=0, flat=0, resolution=0)),
            (evdev.ecodes.ABS_RZ, AbsInfo(value=0, min=-90, max=90, fuzz=0, flat=0, resolution=0)),
            (evdev.ecodes.ABS_X, AbsInfo(value=0, min=-90, max=90, fuzz=0, flat=0, resolution=0)),
            (evdev.ecodes.ABS_Y, AbsInfo(value=0, min=-90, max=90, fuzz=0, flat=0, resolution=0)),
            (evdev.ecodes.ABS_Z, AbsInfo(value=0, min=-90, max=90, fuzz=0, flat=0, resolution=0)),
        ]
        # Have to include the buttons for the hid device to be ID'ed as a joystick:
        capabilities = {
            evdev.ecodes.EV_KEY: [evdev.ecodes.BTN_TRIGGER, evdev.ecodes.BTN_TRIGGER_HAPPY],
            evdev.ecodes.EV_ABS: self.abs_caps
        }
        self.hid_device = evdev.UInput(capabilities, name="opentrack-stick")

    def start(self, udp_ip=UDP_IP, udp_port=UDP_PORT):
        print(f"UDP IP={udp_ip} PORT={udp_port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((udp_ip, udp_port))

        while True:
            data, _ = sock.recvfrom(48)
            # Unpack 6 little endian doubles into a list:
            current = tuple([int(f) for f in struct.unpack('<6d', data[0:48])])
            if self.auto_center > 0.0 and not self.training:
                if self.__auto_center__(current):
                    continue  # We just moved to the center, don't send the current data, it might cause jinking
            if current != self.previous:
                # print(current, self.previous) if debug else False
                self.previous = current
                if self.training:
                    # Only send extreme values (to stop noise interfering in the training).
                    current = self.__training__restrictions__(current)
                self.__send_to_hid__(current)

    def __training__restrictions__(self, current):
        training_data = []
        for i, (cap, v, name) in enumerate(zip(self.abs_caps, current, self.order)):
            abs_info = cap[1]
            if 0.5 * abs_info.min < v < 0.5 * abs_info.max:
                training_value = abs_info.value
            else:
                training_value = abs_info.min if v < abs_info.value else abs_info.max
                if training_value == self.previous_training_value:
                    continue  # Don't send the same value twice - might confuse the target application/game
                else:
                    print(f"Training: {name} input={v} -> send={training_value} "
                          f"range is ({abs_info.min}..{abs_info.value}..{abs_info.max})")
                    self.previous_training_value = training_value
            training_data.append(training_value)
        current = tuple(training_data)
        return current

    def __send_to_hid__(self, values):
        for cap, value, name in zip(self.abs_caps, values, self.order):
            v = int(value)
            if self.debug and abs(v) > 0:
                print(datetime.datetime.now(), name, v)
            self.hid_device.write(evdev.ecodes.EV_ABS, cap[0], v)
        self.hid_device.syn()

    def __auto_center__(self, values):
        for value in values[0:2] + values[3:6]:  # Ignore z - forward backward offset
            if not (-self.auto_center < value < self.auto_center):
                self.centered = False  # Currently off centre
                self.center_arrival_time_ns = 0
                print(f"Off center {time.strftime('%H:%M:%S')}") if self.debug else False
                return False
        if not self.centered:
            now_ns = time.time_ns()
            if self.center_arrival_time_ns == 0:
                print(f"Arrival in center {time.strftime('%H:%M:%S')}") if self.debug else False
                self.center_arrival_time_ns = now_ns
            if (now_ns - self.center_arrival_time_ns) < self.auto_center_ns:
                # Waiting to see if we stay in the center long enough
                print(f"Time in center: {(now_ns - self.center_arrival_time_ns) / 1_000_000_000} secs") if self.debug else False
                return False
            print(f"Middle click (centering) {time.strftime('%H:%M:%S')}")
            self.hid_device.write(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_TRIGGER, 1)
            self.hid_device.syn()
            time.sleep(0.05)  # Apparently, a mouse click interval is about 0.05 seconds.
            self.hid_device.write(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_TRIGGER, 0)
            self.hid_device.syn()
            self.centered = True
            self.center_arrival_time_ns = 0
            return True
        return False


def main():
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    if '--make-md' in sys.argv:
        with open(Path(__file__).with_suffix('.md').name, 'w') as md:
            md.write(__doc__)
        sys.exit(0)
    auto_center = float(sys.argv[sys.argv.index('-a') + 1]) if '-a' in sys.argv else 5.0
    auto_center_secs = float(sys.argv[sys.argv.index('-t') + 1]) if '-t' in sys.argv else 1.0
    stick = OpenTrackStick(debug='-d' in sys.argv,
                           training='-q' in sys.argv,
                           auto_center=auto_center,
                           auto_center_secs=auto_center_secs)
    udp_ip = sys.argv[sys.argv.index('-i') + 1] if '-i' in sys.argv else UDP_IP
    udp_port = sys.argv[sys.argv.index('-p') + 1] if '-p' in sys.argv else UDP_PORT
    stick.start(udp_ip=udp_ip, udp_port=udp_port)


if __name__ == '__main__':
    main()
