#!/usr/bin/python3
"""
opentrack_mouse - opentrack to Linux HID mouse events
=====================================================

Convert opentrack UDP-output to Linux-HID mouse events.

Usage:
======

    python3 opentrack-mouse-original.py [-z] [-d] [-f <float>]

Optional Arguments
------------------

    -z           Translate opentrack z-axis values to mouse wheel events.
    -d           Output mouse event x, y, z values to stdout for debugging purposes.
    -f <float>   Scale factor, alters sensitivity - defaults to 35.0
    -w <float>   Wait seconds for input, then interpolate - defaults to 0.001 (1000 MHz mouse)

Description
===========

Opentrack-mouse listens for opentrack-output UDP-packets and uses evdev
to inject them into Linux input subsystem as HID mouse events.

The evdev mouse events are introduced at the HID device level and are
independent of X11/Wayland, applications cannot differentiate them
from ordinary mouse events.  This means opentrack-mouse will work in
any application, including environments such as Steam Proton.

Opentrack-mouse can fill/smooth/interpolate a gap in input by reusing
the last mouse move. For example, if the mouse is moving left and new
data doesn't arrive in time, the mouse will continue to move left until
new data eventually arrives.  This should hopefully result in smoother
movement.

Quick Start
===========

Get the python (python-3) evdev library:

    pip install ebdev

Run this script:

    python3 opentrack-mouse-original.py

Start opentrack; select Output `UDP over network`; configure the
output option to IP address 127.0.0.1, port 5005; start tracking;
move head.

Opentrack Protocol
==================

Each opentrack UDP-packet is assumed to contain 6 doubles,
little-endian: x,y,z,yaw,pitch,roll.

Licence
=======

This licence is selected to be compatible with opentrack.

Copyright (c) 2022 Michael Hamilton

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import select
import struct
import sys
import time

import evdev
import socket

UDP_IP = "127.0.0.1"
UDP_PORT = 5005


class OpenTrackMouse():

    def __init__(self, enable_wheel=False, debug=False, scale_factor=35.0, wait_secs=0.001):
        self.previous = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.enable_wheel = enable_wheel
        self.debug = debug
        self.scale_factor = scale_factor
        self.wait_secs = wait_secs
        self.last_time = time.time_ns()
        print(f"Wheel enabled: {enable_wheel} Scale Factor: {scale_factor} Wait max secs for input: {wait_secs}")
        # Have to include the buttons for the hid device to work:
        self.hid_device = evdev.UInput(
            {
                evdev.ecodes.EV_REL: [evdev.ecodes.REL_X, evdev.ecodes.REL_Y, evdev.ecodes.REL_WHEEL],
                evdev.ecodes.EV_KEY: [evdev.ecodes.BTN_LEFT, evdev.ecodes.BTN_RIGHT],
            },
            name="opentrack_mouse")

    def start(self):
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        sock.bind((UDP_IP, UDP_PORT))
        sock.setblocking(0)
        f = self.scale_factor
        current = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        while True:
            # Use previous data value if none is ready - keeps the mouse moving smoothly in the current direction
            if select.select([sock], [], [], self.wait_secs)[0]:
                data, _ = sock.recvfrom(48)
                # Unpack 6 little endian doubles into a list:
                current = struct.unpack('<6d', data[0:48])
            # using pitch for x, yaw for y, z movement for z
            _, _, z, yaw, pitch, _ = self.previous
            _, _, zn, yaw_new, pitch_new, _ = current
            self.__send_to_hid__(round((yaw_new - yaw) * f), round((pitch - pitch_new) * f), round((z - zn) * f / 2))
            self.previous = current

    def __send_to_hid__(self, x, y, z):
        i = 0
        if x != 0:
            self.hid_device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_X, x)
            i += 1
        if y != 0:
            self.hid_device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_Y, y)
            i += 1
        if self.enable_wheel and z != 0:
            self.hid_device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, z)
            i += 1
        if self.debug:
            now = time.time_ns()
            print(f"[{i}] {(now - self.last_time) / 1_000_000} ms x={x}, y={y}, z={z}")
            self.last_time = now
        if i:
            self.hid_device.syn()
        return


def main():
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    scale_factor = float(sys.argv[sys.argv.index('-f') + 1]) if '-f' in sys.argv else 35.0
    wait_secs = float(sys.argv[sys.argv.index('-w') + 1]) if '-w' in sys.argv else 0.001
    mouse = OpenTrackMouse('-z' in sys.argv, '-d' in sys.argv, scale_factor=scale_factor, wait_secs=wait_secs)
    mouse.start()


if __name__ == '__main__':
    main()
