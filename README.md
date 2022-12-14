
opentrack-opal - Output to Python And Linux 
===========================================

Opentrack UDP-Output to python-Linux-evdev mouse and stick.  Two examples
of head-tracking using [opentrack](https://github.com/opentrack/opentrack/blob/master/README.md)
and the Linux evdev library via the [python evdev](https://python-evdev.readthedocs.io/en/latest/) wrapper.

opentrack UDP-Output protocol
-----------------------------

opentrack's UDP-Output protocol is used as a language neutral interface
to python.  Each opentrack UDP-Output packet contains 6 little-endian 
doubles: x, y, z, yaw, pitch, and roll.

Linux evdev - Event Device
--------------------------

The evdev subsystem is a generic input event interface in Linux kernel.
Userspace applications can interact with evdev to create and intercept
keyboard, mouse, and joystick events.  Events may be raised by both
real and virtual devices.

The opentrack-opal python scripts make use of the python evdev wrapper
to libevdev which is in turn a wrapper for evdev devices and the kernel's
evdev subsystem.   

opentrack-mouse - UDP-Output to mouse-events
============================================

Translate opentrack UDP-output to Linux-evdev/HID mouse 
events.  

Opentrack-mouse is easy to set up, all existing 
games/apps will automatically receive its mouse events.
The downside is that head-tracking via a mouse is subject
to drift, the tracking and the on-screen orientation
drift apart (necessitating the periodic use of a re-center
button).

See [opentrack-mouse.md](opentrack-mouse.md).

opentrack-stick - UDP-Output to joystick-events
===============================================

Translate opentrack UDP-output to Linux-evdev joystick events
emulating a `Microsoft X-Box 360 pad`.

Opentrack-stick provides an accurate head tracking experience,
positioning is absolute, and not subject to drift.  However,
opntrack-stick requires the targeted game/app to support mapping 
joystick-axes to in-app view-changes/head-turns.  The user will 
have to use the games key/button/axes mapping system to 
individually bind opentrack-axes to view-changes/head-turns.

See [opentrack-stick.md](opentrack-stick.md).

Limitations
===========

There needs to be more research into the best settings to 
achieve a smooth result.

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
