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


Game Training Example: IL2 BoX
==============================

These are the steps I followed to get the controller to work for
head yaw and pitch in IL-2 BoX.

What I did:

1. Backup `.../IL-2 Sturmovik Battle of Stalingrad/data/input/`
2. Start opentrack-stick (do not use `-q`).
3. Start opentrack receiving `Output` `UDP over network`
   with the port and address from step 1.
4. Check that the above is working.
5. Open the opentrack `Mapping` graphs and make every
   curve, except for the pitch, dead flat (to silence any noise
   from the tracking).
6. Change the pitch curve so that head movement easily
   ramps between the min and max output values. It's import
   that it can ramp up and reach the max value (or near to it),
   if it doesn't ramp up or doesn't get high enough, the game
   will ignore it as noise.
7. Start Steam and IL2 BoX and use the games key mapping
   menu to map pilot-head pitch to actual head pitch.
8. Back in opentrack, turn off the pitch by flattening
   its curve, repeat 6 and 7 for yaw.
9, Return the opentrack curves to a usable normal.

Rather than restarting IL-2 BoX, I used two monitors. I
used `alt-tab` between monitors displaying the game and the
opentrack-UI.

In IL-2 BoX it doesn't seem possible to map an axis to side/back
head movement.  At this time the emulator doesn't have any
mappings for axes to hat/button events.

Mapping the z to camera zoom might be possible.

Instead, in opentrack, change all the mapping
curves to be dead flat to stop any data making it through.

Current training option is of no use
------------------------------------
I found the current training `-q` option is of no use in
IL-2 BoX - I think the game is looking for the ramp up of
values from middle to high and low.  The current training
option steps the values from middle to min or max without a
ramping transition.  So there is no avoiding using `alt-tab`
and manually altering the curves at this time.

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

1. Connect a real stick.
2. Start an opentrack, set the `Input` to `Linux joystick input`, then
   open the input option and choose the real joystick as the
   input `Device`.
3. Send the `opentrack` `UPD-Output` to UDP 127.0.0.1 Port 5005
   and start tracking.
4. Run `opentrack-stick.py`.
5. Start a second `opentrack`, under `Input` `Linux joystick input`, the
   `Device` options should now include `opentrack-stick`, choose this
   as the input.  Set up a UDP `Output` that goes nowhere by picking a port
   nothing is listening on.  Start it tracking.
6. The stick moves from the first opentrack should be passed to
   opentrack-stick, which should then be echoed by the second
   opentrack.

Or stop after step-4 and run an evdev listener on `/dev/input/event<N>`
device associated with the stick (see snoop-evdev.py).

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
from collections import namedtuple
from pathlib import Path

import evdev
from evdev import AbsInfo
from evdev import ecodes as ec

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

OpenTrackCap = namedtuple("OpenTrackCap", "name value min max")

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
        self.opentrack_caps = [OpenTrackCap('x', 0, -75, 75),
                               OpenTrackCap('y', 0, -75, 75),
                               OpenTrackCap('z', 0, -75, 75),
                               OpenTrackCap('yaw', 0, -90, 90),
                               OpenTrackCap('pitch', 0, -90, 90),
                               OpenTrackCap('roll', 0, -90, 90)]
        self.abs_caps = [
            (ec.ABS_RX,    AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_RY,    AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_RZ,    AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            (ec.ABS_X,     AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_Y,     AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_Z,     AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            (ec.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
            (ec.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
        ]
        # Have to include the buttons for the hid device to be ID'ed as a joystick:
        capabilities = {
            ec.EV_KEY: [ec.BTN_A, ec.BTN_GAMEPAD, ec.BTN_SOUTH, ec.BTN_B,
                        ec.BTN_A,ec.BTN_GAMEPAD,ec.BTN_SOUTH,
                        ec.BTN_B,ec.BTN_EAST,
                        ec.BTN_NORTH,ec.BTN_X,
                        ec.BTN_WEST,ec.BTN_Y,
                        ec.BTN_TL,
                        ec.BTN_TR,
                        ec.BTN_SELECT,
                        ec.BTN_START,
                        ec.BTN_MODE,
                        ec.BTN_THUMBL,
                        ec.BTN_THUMBR,
                        ],
            ec.EV_ABS: self.abs_caps,
            ec.EV_FF: [ec.FF_EFFECT_MIN, ec.FF_RUMBLE]
        }
        self.hid_device = evdev.UInput(capabilities, name="Microsoft X-Box 360 pad 0")

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
                self.__send_to_hid__(current)

    def __send_to_hid__(self, values):
        for cap, value, ot_info in zip(self.abs_caps[:6], values, self.opentrack_caps):
            ev_info = cap[1]
            scaled = ev_info.min + round(((value - ot_info.min) / (ot_info.max - ot_info.min)) * (ev_info.max - ev_info.min))
            if self.training:
                # Only send extreme values (to stop noise interfering in the training).
                training_value = self.__training_value__(scaled, ev_info, ot_info.name)
                print(f"{datetime.datetime.now()}: {ot_info.name} received-value={value} "
                      f"device-scaled-value={scaled} training-value={training_value}")
                scaled = training_value
            elif self.debug:
                print(f"{datetime.datetime.now()}: {ot_info.name} received-value={value} device-scaled-value={scaled}")
            self.hid_device.write(ec.EV_ABS, cap[0], scaled)
        self.hid_device.syn()

    def __training_value__(self, value, abs_info, name):
        if self.training:
            middle_value = (abs_info.min + abs_info.max) // 2
            range_constraint = 0.2 * (abs_info.max - abs_info.min)
            if (abs_info.min + range_constraint) <= value <= (abs_info.max - range_constraint):
                training_value = middle_value
            else:
                # Send the min or max value depending on +-ve of the original value
                training_value = abs_info.min if value < middle_value else abs_info.max
                print(f"Training: {name} scaled output value={value} -> training value={training_value} "
                      f"device range is ({abs_info.min}..{middle_value}..{abs_info.max})")
            return training_value
        return value

    def __auto_center__(self, values):
        for value in values[0:2] + values[3:6]:  # Ignore z - forward backward offset
            if not (-self.auto_center < value < self.auto_center):
                if self.centered:
                    print(f"Off center {time.strftime('%H:%M:%S')}") if self.debug else False
                self.centered = False  # Currently off centre
                self.center_arrival_time_ns = 0
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
            self.hid_device.write(ec.EV_KEY, ec.BTN_TRIGGER, 1)
            self.hid_device.syn()
            time.sleep(0.05)  # Apparently, a mouse click interval is about 0.05 seconds.
            self.hid_device.write(ec.EV_KEY, ec.BTN_TRIGGER, 0)
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
