#!/usr/bin/python3
"""
opentrack-mouse - Linux opentrack UDP mouse-emulator
====================================================

Translate head-tracking opentrack UDP-output to Linux-evdev/HID mouse events.

Usage:
======

    python3 opentrack-mouse-original.py [-f <float>] -w <float> -a <steps> -t <float> [-z] [-d]

Optional Arguments
------------------

    -f <float>   Scale factor, alters sensitivity (default 30.0, 10.0 is good for games)
    -w <float>   Wait seconds for input, then interpolate (default 0.001
                 to simulate a 1000 MHz mouse)
    -s <int>     Smooth over n values (default 100)
    -q <float>   Smoothing alpha 0.0..1.0, smaller values smooth more (default 0.1)
    -a <zone>    Auto-center (press middle mouse button) if all tracking
                 values are in the -zone..+zone (default 0.0, suggest 5.0)
    -t <float>   Auto-center required seconds for all values remain in
                 the zone for this many millis (default 1.0)
    -z           Translate opentrack z-axis values to mouse wheel
                 events (default is off)
    -d           Output mouse event x, y, z values to stdout for
                 debugging purposes.

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

Auto-centering can be enabled for applications where the center
may drift from the true-center AND the application supports a
binding for a re-center command.  Bind the application's re-center
command to the middle mouse button and enable auto-centering by
using the opentrack-mouse -a option. When enabled, opentrack-mouse
will click the middle mouse button when the input-values from
opentrack remain in the middle zone for the time specified
by the -t option.

Quick Start
===========

Get the python (python-3) evdev library:

    pip install evdev

Run this script:

    python3 opentrack-mouse-original.py

Start opentrack; select Output `UDP over network`; configure the
output option to IP address 127.0.0.1, port 5005; start tracking;
move head.

Opentrack Protocol
==================

Each opentrack UDP-Output packet contains 6 little-endian
doubles: x, y, z, yaw, pitch, and roll.

Examples
========

Normal desktop settings:

    python3 opentrack-mouse.py

Flight sim low scale factor, auto-centering, center zone
of -8.0..+8.0 for 1.0 seconds:

    python3 opentrack-mouse.py -f 10 -a 8.0 -t 1.0  -z

Limitations
===========

Achieving the most appropriate settings is dependent on tweaking
the opentrack settings, the opentrack-mouse settings, and possibly
the end-application settings, the subtleties of which can be somewhat
opaque.

The resulting movement can sometimes be jerky depending on the device
generating the input and the timings of data exchanges.

Apart from interpolating during input gaps, and some simple smoothing,
opentrack-mouse doesn't perform any intelligent analysis of the data.
Opentrack  presents some more complex output filters with options
for smoothing.

Author
======

Michael Hamilton

License
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
import math
import select
import socket
import struct
import sys
import time
from pathlib import Path

import evdev

UDP_IP = "127.0.0.1"
UDP_PORT = 5005


class OpenTrackMouse:

    def __init__(self, scale_factor=35.0, wait_secs=0.001,
                 auto_center=0.0, auto_center_secs=1.0,
                 smoothing=100, smooth_alpha=0.1,
                 enable_wheel=False, debug=False):
        self.previous = self.current = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.enable_wheel = enable_wheel
        self.debug = debug
        self.scale_factor = scale_factor
        self.wait_secs = wait_secs
        self.smoothing = smoothing
        self.smooth_alpha = smooth_alpha
        self.auto_center = auto_center
        self.auto_center_ns = auto_center_secs * 1_000_000_000
        self.centered = True
        self.center_arrival_time_ns = 0
        self.previous_event_time = time.time_ns()
        print(f"Scale output by: {scale_factor}\nMaximum output interval: {wait_secs} seconds (then repeat previous values)\n"
              f"Wheel enabled: {enable_wheel}\nDebug: {debug}")
        print(f"Smoothing: n={self.smoothing} alpha={self.smooth_alpha}")
        print(f"Auto center when all values in zone: -{auto_center}..+{auto_center}"
              f" for {auto_center_secs} second(s)\n" if auto_center > 0.0 else "Auto center: off")
        # Have to include the buttons for the hid device to work:
        self.hid_device = evdev.UInput(
            {
                evdev.ecodes.EV_REL: [evdev.ecodes.REL_X, evdev.ecodes.REL_Y, evdev.ecodes.REL_WHEEL],
                evdev.ecodes.EV_KEY: [evdev.ecodes.BTN_LEFT, evdev.ecodes.BTN_RIGHT, evdev.ecodes.BTN_MIDDLE],
            },
            name="opentrack_mouse")

    def start(self, udp_ip=UDP_IP, udp_port=UDP_PORT):
        print(f"UDP IP={udp_ip} PORT={udp_port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,48)
        sock.bind((udp_ip, udp_port))
        sock.setblocking(False)
        self.current = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smoothers = [Smooth(n=self.smoothing, alpha=self.smooth_alpha) for i in range(len(self.current))]
        while True:
            # Use previous data value if none is ready - keeps the mouse moving smoothly in the current direction
            if select.select([sock], [], [], self.wait_secs)[0]:
                data, _ = sock.recvfrom(48)
                # Unpack 6 little endian doubles into a list:
                unpacked_data = struct.unpack('<6d', data[0:48])
                self.current = [smoother.smooth(datum) for datum, smoother in zip(unpacked_data, smoothers)]
                if self.auto_center > 0.0:
                    if self.__auto_center__(self.current):
                        continue  # Don't send the current data, we just centered, moving again might cause a jink
            # using pitch for x, yaw for y, z movement for z
            _, _, z, yaw, pitch, _ = self.previous
            _, _, zn, yaw_new, pitch_new, _ = self.current
            # Note the hacky scale factor for Z, probably needs a better algorithm that also consults pitch
            self.__send_to_hid__(self.convert_to_mouse_value(yaw_new, yaw, self.scale_factor),
                                 self.convert_to_mouse_value(pitch, pitch_new, self.scale_factor),
                                 self.convert_to_mouse_value(z, zn, self.scale_factor / 3))
            self.previous = self.current

    def convert_to_mouse_value(self, v1, v2, scale_factor):
        diff = scale_factor * (v1 - v2)
        # Does a crude wrapping check
        return 0 if abs(diff) > (180.0 * scale_factor) else round(diff)

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
            self.hid_device.write(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_MIDDLE, 1)
            self.hid_device.syn()
            time.sleep(0.05)  # Apparently, a mouse click interval is about 0.05 seconds.
            self.hid_device.write(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_MIDDLE, 0)
            self.hid_device.syn()
            self.centered = True
            self.center_arrival_time_ns = 0
            return True
        return False

    def __send_to_hid__(self, x, y, z):
        i = 0
        if x != 0:
            self.hid_device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_X, x)
            i += 1
        if y != 0:
            self.hid_device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_Y, y)
            i += 1
        if self.enable_wheel and z != 0:
            # Z is a wheel - treat differently
            self.hid_device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, -1 if z < 0 else 1)
            i += 1
        now = time.time_ns()
        if self.debug:
            print(f"[{i}] {(now - self.previous_event_time) / 1_000_000} ms x={x}, y={y}, z={z} {self.current}")
        self.previous_event_time = now
        if i:
            self.hid_device.syn()
        return


class Smooth:
    def __init__(self, n, alpha=0.1):
        self.length = n
        self.values = [0] * n
        self.alpha = alpha
        self.total = sum(self.values)

    def smooth(self, v):
        return self.smooth_lp_filter(v)

    def smooth_simple(self, v):
        # Simple moving average - very efficient
        if self.length <= 1:
            return v
        self.total -= self.values[0]
        self.values.pop(0)
        self.values.append(v)
        self.total += v
        return self.total / self.length

    def smooth_lp_filter(self, v):
        # https://stackoverflow.com/questions/4611599/smoothing-data-from-a-sensor
        # https://en.wikipedia.org/wiki/Low-pass_filter#Simple_infinite_impulse_response_filter
        # The smaller the alpha, the more each previous value affects the following value.
        # So a smaller alpha results in more smoothing.
        # y[1] := alpha * x[1]
        # for i from 2 to n
        #     y[i] := y[i-1] + alpha * (x[i] - y[i-1])
        if self.length <= 1:
            return v
        self.values.pop(0)
        self.values.append(v)
        a = 0.1
        p = self.values[0] * a
        for i in range(1, len(self.values)):
            p = p + a * (self.values[i] - p)
        return p


def main():
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    if '--make-md' in sys.argv:
        with open(Path(__file__).with_suffix('.md').name, 'w') as md:
            md.write(__doc__)
        sys.exit(0)
    scale_factor = float(sys.argv[sys.argv.index('-f') + 1]) if '-f' in sys.argv else 35.0
    wait_secs = float(sys.argv[sys.argv.index('-w') + 1]) if '-w' in sys.argv else 0.001
    smooth_n = int(sys.argv[sys.argv.index('-s') + 1]) if '-s' in sys.argv else 100
    smooth_alpha = float(sys.argv[sys.argv.index('-q') + 1]) if '-q' in sys.argv else 0.1
    auto_center = float(sys.argv[sys.argv.index('-a') + 1]) if '-a' in sys.argv else 0.0
    auto_center_secs = float(sys.argv[sys.argv.index('-t') + 1]) if '-t' in sys.argv else 1.0
    mouse = OpenTrackMouse(scale_factor=scale_factor,
                           wait_secs=wait_secs,
                           auto_center=auto_center,
                           auto_center_secs=auto_center_secs,
                           smoothing=smooth_n,
                           smooth_alpha=smooth_alpha,
                           enable_wheel='-z' in sys.argv,
                           debug='-d' in sys.argv)
    udp_ip = sys.argv[sys.argv.index('-i') + 1] if '-i' in sys.argv else UDP_IP
    udp_port = int(sys.argv[sys.argv.index('-p') + 1]) if '-p' in sys.argv else UDP_PORT
    mouse.start(udp_ip=udp_ip, udp_port=udp_port)


if __name__ == '__main__':
    main()
