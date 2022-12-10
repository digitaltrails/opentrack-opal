#!/usr/bin/python3
"""
opentrack-stick - opentrack to Linux HID stick events
=====================================================

Translate opentrack UDP-output to Linux-HID joystick events.

Usage:
======

    python3 opentrack-stick.py [-d] [-t]

Optional Arguments
------------------

    -d           Output joystick event x, y, z values to stdout for debugging purposes.
    -t           Training: limit each axis to large changes to eliminate other-axis "noise"
                 when mapping an axis within a game.

Description
===========

opentrack-stick listens for opentrack-output UDP-packets and uses evdev
to inject them into Linux input subsystem as HID joystick events.

The evdev joystick events are introduced at the HID device level and are
independent of X11/Wayland, applications cannot differentiate them
from ordinary joystick events.  This means opentrack-stick will work in
any application, including environments such as Steam Proton.

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
output option to IP address 127.0.0.1, port 5005; start tracking;
move head.

Opentrack Protocol
==================

Each opentrack UDP-Output packet contains 6 little-endian
doubles: x, y, z, yaw, pitch, and roll.

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

    def __init__(self, debug=False, training=False):
        self.debug = debug
        self.training = training
        self.last_time = time.time_ns()
        self.previous = None
        print(f"Training: {self.training}")
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

    def start(self):
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        sock.bind((UDP_IP, UDP_PORT))
        # sock.setblocking(1)
        base_values = (self.abs_caps[0][1].value,
                       self.abs_caps[1][1].value,
                       self.abs_caps[2][1].value,
                       self.abs_caps[3][1].value,
                       self.abs_caps[4][1].value,
                       self.abs_caps[5][1].value,)
        while True:
            data, _ = sock.recvfrom(48)
            # Unpack 6 little endian doubles into a list:
            current = tuple([int(f) for f in struct.unpack('<6d', data[0:48])])

            if current != self.previous:
                print(current, self.previous)
                self.previous = current
                if self.training:
                    # Only send extreme values (to stop noise interfering in the training).
                    training_data = []
                    for i, (cap, v, bv) in enumerate(zip(self.abs_caps, current, base_values)):
                        abs_info = cap[1]
                        training_data.append(bv if 0.1 * abs_info.min < v < 0.1 * abs_info.max else v)
                    current = tuple(training_data)
                self.__send_to_hid__(current)

    def __send_to_hid__(self, values):
        for cap, value, name in zip(self.abs_caps, values, self.order):
            v = int(value)
            if abs(v) > 0:
                print(datetime.datetime.now(), name, v)
            self.hid_device.write(evdev.ecodes.EV_ABS, cap[0], v)
        self.hid_device.syn()


def main():
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    if '--make-md' in sys.argv:
        with open(Path(__file__).with_suffix('.md').name, 'w') as md:
            md.write(__doc__)
        sys.exit(0)
    stick = OpenTrackStick(debug='-d' in sys.argv, training='-t' in sys.argv)
    stick.start()


if __name__ == '__main__':
    main()
