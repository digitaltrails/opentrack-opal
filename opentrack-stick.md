
opentrack-stick - opentrack to Linux HID stick events
=====================================================

Translate opentrack UDP-output to Linux-HID joystick events.

Usage:
======

    python3 opentrack-stick.py [-h] [-s <int>] [-a <float>] [-b <csv>] [-i ip-addr] [-o <port>] [-d]

Optional Arguments
------------------

    -w <float>   Wait seconds for input, then interpolate (default 0.001
                 to simulate a 1000 MHz mouse)
    -s <int>     Smooth over n values (default 250)
    -a <float>   Smoothing alpha 0.0..1.0, smaller values smooth more (default 0.05)
    -b <csv>     Bindings for opentrack-axis to virtual-control-number, must be 6 integers
                 (default 1,2,3,4,5,6)
    -i <ip-addr> The ip-address to listen on for the UDP feed from opentrack
    -p <port>    The UDP port number to listen on for the UDP feed from opentrack
    -h           Help
    -d           Output joystick event values to stdout for debugging purposes.

Description
===========

opentrack-stick listens for opentrack-output UDP-packets and uses evdev
to inject them into Linux input subsystem as HID joystick events.

The virtual-stick claims to have the same evdev capabilities as a
`Microsoft X-Box 360 pad`.

By default, the x, y, z, yaw, pitch, and roll opentrack values are sent
to the virtual controller's left stick x, y, z and right stick x, y, z
Z is some kind of trigger based axes with a limited range.

Some games don't support axes assignment to x, y, and z, but they may
be able to be assigned to +/- button mappings instead.  Several pairings
of buttons are supported for mapping pairs of moves, for example head
move to the left, and head move to the right.

The evdev joystick events are injected at the HID device level and are
independent of X11/Wayland, applications cannot differentiate them
from ordinary joystick events.  This means opentrack-stick will work in
any application, including environments such as Steam Proton.

Opentrack-stick will fill/smooth/interpolate a gap in input by feeding
the last move back into the smoothing algorithm. This will result in
the most recent value becoming dominant as time progresses.

Re-Mapping axis assignments
===========================

The binding of the virtual-controls to opentrack-track control can
be changed by using the `-b` option.

Opentrack controls in mapping order: x, y, z, yaw, pitch, roll.

A mapping specification allocates a numbered virtual control to each
opentrack axes in the mapping order: x, y, z, yaw, pitch, roll.

Virtual control numbers
-----------------------

    1. ABS_RX,
    2. ABS_RY,
    3. ABS_RZ,
    4. ABS_X,
    5. ABS_Y,
    6. ABS_Z,
    7. ABS_HAT0X,
    8. ABS_HAT0Y,
    9. BTN_A<=>BTN_B,BTN  (a pair of buttons - use for -/+ key mappings)
    10. BTN_NORTH<=>BTN_WEST,
    11. BTN_TL<=>BTN_TR,
    12. BTN_SELECT<=>BTN_START,
    13. BTN_MODE<=>BTN_TR,

For example: `-b 9,0,1,4,5,0` binds opentrack-x to control-9,
opentrack-y to nothing, opentrack-z to control-1, opentrack-yaw
to control-4, opentrack-pitch to control-5 to, and opentrack-roll
to nothing.

The ABS (absolute position) mappings correspond to individual
joystick and HAT axes.

The BTN mappings correspond to pairs of buttons.  For example,
mapping an opentrack-x movement to `BTN-A<=>BTN-B` would result in
the virtual-stick generating a BTN-A event when you move one
way and a BTN-B event when you move the other way.  When setting
up buttons it pays to set the opentrack mapping curves with
a large dead zone. That way you can be certain of which key will be
sent to the game.  The `-d` parameter may be useful to see what
 is being sent in response to your movements.


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


Game Training Example: IL2 BoX
==============================

These are the steps I followed to get the controller to work for
head yaw and pitch in IL-2 BoX.

On the game tested (IL-2 BoX in Steam), only 1, 2, 4, 5, 9 were
recognised and mappable by the in-game key-mapping system.

What I did:

I mapped opentrack head-z, head-yaw, and head-pitch to
virtual-control-1, virtual-control-4, and virtual-control-5,
that corresponds to `-b 0,0,1,4,5,0`.

1. Backup `.../IL-2 Sturmovik Battle of Stalingrad/data/input/`
2. Start opentrack-stick with only one axis mapped. For example,
   to enable yaw output to virtual-control-4, pass -b 0,0,0,4,0,0..
3. Start opentrack, configure `Output` `UDP over network`
   with the port and address from step 1.
4. Check that the above is working (perhaps just run
   ``opentrack-stick -d`` at first to see if logs the events
   coming from opentrack).
6. In the opentrack GUI, change the target curve so that head
   movement easily moves between the min and max output values.
   It's import that it ramps up smoothly and reaches the max
   value (or near to it).  If it doesn't ramp smoothy or doesn't
   get high enough, the game will ignore it as noise.
7. Start Steam and IL2 BoX and use the game's key mapping
   menu to map your head movement axis.  For example,
   choose the IL-2 pilot-head-turn mapping, bind it
   to virtual-control-4 by yawing your head appropriately.
8. Repeat for next target mapping.

Rather than restarting IL-2 BoX to perform each mapping,
I used two monitors. I used `alt-tab` between monitors
displaying the game and an xterm. Without restarting
IL-BoX or opentrack, I switched to the xterm,
interrupted (control-C) opentrack-stick, then started a
new opentrack-stick with the next `-b` value, for
example `opentrack-stick -b 0,0,0,5,0` to map opentrack-pitch
to virtual-control-5.

Having setup head yaw and pitch, I assigned opentrack-z to
virtual-control-1 and bound that to head-zoom.

The game doesn't support using axes for x, y, z head motion,
it expects these to be assigned to buttons.  I used the
pair `9. BTN_A<=>BTN_B,BTN` for x, side to side movement;
`10` for y, and `11` for z.

My final IL-2 BoX mappings are `-b 9,10,11,4,5,0`.
I additionally mapped head zoom to axis 1, so I can optionally
switch to the mapping `-b 9,10,1,4,5,0`.

Opentrack Protocol
==================

Each opentrack UDP-Output packet contains 6 little-endian
doubles: x, y, z, yaw, pitch, and roll.

Limitations
===========

The smoothing values need more research, as do other smoothing
methods.  A small alpha (less than 0.1) seems particularly good
at allowing smooth transitions.

Axis mappings `3` and `6` are not tested.

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
