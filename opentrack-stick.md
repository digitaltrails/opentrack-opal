
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
output option to IP address 127.0.0.1, port 5005; start tracking;
move head.

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
