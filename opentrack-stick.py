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

    -w <float>   Wait seconds for input, then interpolate (default 0.001
                 to simulate a 1000 MHz mouse)
    -s <int>     Smooth over n values (default 250)
    -q <float>   Smoothing alpha 0.0..1.0, smaller values smooth more (default 0.05)
    -i <ip-addr> The ip-address to listen on for the UDP feed from opentrack
    -p <port>    The UDP port number to listen on for the UDP feed from opentrack
    -d           Output joystick event x, y, z values to stdout for debugging purposes.
    -q           Training: limit each axis to large changes to eliminate other-axis "noise"
                 when mapping an axis within a game.

Description
===========

opentrack-stick listens for opentrack-output UDP-packets and uses evdev
to inject them into Linux input subsystem as HID joystick events.

The virtual-stick claims to have the same evdev capabilities as a
`Microsoft X-Box 360 pad` - but not all of them are functional (just the
stick axes at this stage)

The evdev joystick events are introduced at the HID device level and are
independent of X11/Wayland, applications cannot differentiate them
from ordinary joystick events.  This means opentrack-stick will work in
any application, including environments such as Steam Proton.

Opentrack-stick will fill/smooth/interpolate a gap in input by feeding
the last move back into the smoothing algorithm. This will result in
the most recent value becoming dominant as time progresses.

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
in the game/application choose the joystick called `Microsoft X-Box 360 pad 0`.
If the app/game requires you to configure the stick, you may find the
`-q` training option useful.


Game Training Example: IL2 BoX
==============================

These are the steps I followed to get the controller to work for
head yaw and pitch in IL-2 BoX.

What I did:

1. Backup `.../IL-2 Sturmovik Battle of Stalingrad/data/input/`
2. Start opentrack-stick and your head tracker.
3. Start opentrack sending `Output` `UDP over network`
   with the port and address from step 1.
4. Check that the above is working (perhaps just run ``opentrack-stick -d``
   at first to see if logs the events coming from opentrack).
5. Open the opentrack `Mapping` graphs and make every
   curve dead flat except for pitch (this silences any
   noise from other axes).
6. Change the pitch curve so that head movement easily
   moves between the min and max output values. It's import
   that it ramps up smoothly and reaches the max value (or near
   to it).  If it doesn't ramp smoothy or doesn't get high
   enough, the game will ignore it as noise.
7. Start Steam and IL2 BoX and use the games key mapping
   menu to map pilot-head pitch to actual head pitch by
   moving your head appropriately.
8. Back in opentrack, turn off the pitch by flattening
   its curve, repeat 6 and 7 for yaw.
9, Return the opentrack curves to a usable normal.

Rather than restarting IL-2 BoX, I used two monitors. I
used `alt-tab` between monitors displaying the game and the
opentrack-UI.

In IL-2 BoX it doesn't seem possible to map an axis to side/back
head movement.  It expects to use the hat or buttons - at this
time the emulator doesn't have any mappings for opentrack
axes to hat/button events.

Setting the smoothing to 0 might help during training. It
probably won't make a different, but I didn't have smoothing
implemented when I performed this process, so I can't be
sure.

Opentrack Protocol
==================

Each opentrack UDP-Output packet contains 6 little-endian
doubles: x, y, z, yaw, pitch, and roll.

Limitations
===========

Only pitch and yaw is implemented at this time.

The smoothing values need more research, as do other smoothing
methods.  A small alpha (less than 0.1) seems particularly good
at allowing smooth transitions.

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
import select
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

    def __init__(self, wait_secs=0.001, smoothing=500, smooth_alpha=0.1, debug=False):
        self.wait_secs = wait_secs
        self.debug = debug
        self.last_time = time.time_ns()
        self.previous = None
        self.smoothing = smoothing
        self.smooth_alpha = smooth_alpha
        print(f"Input wait max: {wait_secs * 1000} ms - will then feed the smoother with repeat values.")
        print(f"Smoothing: n={self.smoothing} alpha={self.smooth_alpha}")
        self.opentrack_caps = [OpenTrackCap('x', 0, -75, 75),
                               OpenTrackCap('y', 0, -75, 75),
                               OpenTrackCap('z', 0, -75, 75),
                               OpenTrackCap('yaw', 0, -90, 90),
                               OpenTrackCap('pitch', 0, -90, 90),
                               OpenTrackCap('roll', 0, -90, 90)]
        self.abs_caps = [
            (ec.ABS_RX, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_RY, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_RZ, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            (ec.ABS_X, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_Y, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0)),
            (ec.ABS_Z, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            (ec.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
            (ec.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
        ]
        # Have to include the buttons for the hid device to be ID'ed as a joystick:
        capabilities = {
            ec.EV_KEY: [ec.BTN_A, ec.BTN_GAMEPAD, ec.BTN_SOUTH, ec.BTN_B,
                        ec.BTN_A, ec.BTN_GAMEPAD, ec.BTN_SOUTH,
                        ec.BTN_B, ec.BTN_EAST,
                        ec.BTN_NORTH, ec.BTN_X,
                        ec.BTN_WEST, ec.BTN_Y,
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
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 48)
        sock.bind((udp_ip, udp_port))
        sock.setblocking(False)
        current = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smoothers = [Smooth(n=self.smoothing, alpha=self.smooth_alpha) for i in range(len(current))]
        while True:
            # Use previous data value if none is ready - keeps the mouse moving smoothly in the current direction
            if select.select([sock], [], [], self.wait_secs)[0]:
                data, _ = sock.recvfrom(48)
                # Unpack 6 little endian doubles into a list:
                current = struct.unpack('<6d', data[0:48])
            # This may feed repeat data into the smoother, that should result in the latest value becoming stronger over time.
            current = [smoother.smooth(datum) for datum, smoother in zip(current, smoothers)]
            if current != self.previous:
                # print(current, self.previous) if debug else False
                self.previous = current
                self.__send_to_hid__(current)

    def __send_to_hid__(self, values):
        for cap, value, ot_info in zip(self.abs_caps[:6], values, self.opentrack_caps):
            ev_info = cap[1]
            scaled = ev_info.min + round(((value - ot_info.min) / (ot_info.max - ot_info.min)) * (ev_info.max - ev_info.min))
            if self.debug:
                print(f"{datetime.datetime.now()}: {ot_info.name} received-value={value} device-scaled-value={scaled}")
            self.hid_device.write(ec.EV_ABS, cap[0], scaled)
        self.hid_device.syn()


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
        smoothed = self.values[0] * self.alpha
        for value in self.values[1:]:
            smoothed = smoothed + self.alpha * (value - smoothed)
        return smoothed


def main():
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    if '--make-md' in sys.argv:
        with open(Path(__file__).with_suffix('.md').name, 'w') as md:
            md.write(__doc__)
        sys.exit(0)
    wait_secs = float(sys.argv[sys.argv.index('-w') + 1]) if '-w' in sys.argv else 0.001
    smooth_n = int(sys.argv[sys.argv.index('-s') + 1]) if '-s' in sys.argv else 250
    smooth_alpha = float(sys.argv[sys.argv.index('-q') + 1]) if '-q' in sys.argv else 0.05
    stick = OpenTrackStick(wait_secs=wait_secs,
                           smoothing=smooth_n,
                           smooth_alpha=smooth_alpha,
                           debug='-d' in sys.argv)
    udp_ip = sys.argv[sys.argv.index('-i') + 1] if '-i' in sys.argv else UDP_IP
    udp_port = sys.argv[sys.argv.index('-p') + 1] if '-p' in sys.argv else UDP_PORT
    stick.start(udp_ip=udp_ip, udp_port=udp_port)


if __name__ == '__main__':
    main()
