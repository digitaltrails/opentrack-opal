
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
                 the zone for this many seconds (default 1.0)
    -z           Translate opentrack z-axis values to mouse wheel
                 events (default is off)
    -i <ip-addr> The ip-address to listen on for the UDP feed from opentrack
    -p <port>    The UDP port number to listen on for the UDP feed from opentrack
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
