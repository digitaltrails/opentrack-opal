
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
                 (default 1,2,3,4,5,6,0), the seventh binding is for a snap centre button.
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

Opentrack-stick will fill/smooth/interpolate a gap in opentrack/joystick axes
input by feeding the last move back into the smoothing algorithm. The
parameters of the algorithm can be adjusted to suit your own situation.

Some games don't support axes assignment to x, y, and z, but they may
be able to be assigned to +/- virtual button mappings instead.

The evdev joystick events are injected at the HID device level and are
independent of X11/Wayland, applications cannot differentiate them
from ordinary joystick events.  This means opentrack-stick will work in
any application, including environments such as Steam Proton.

Mapping axis assignments
========================

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

Each HAT axis functions like a button with three states (-1,0,1),
it can effectively serve as a pair of mutually exclusive button
actions. See the following section on Virtual Button mappings.

Virtual Button mappings
-----------------------

The BTN mappings correspond to pairs of buttons.  For example,
mapping an opentrack-x movement to `BTN-A<=>BTN-B` would result in
the virtual-stick generating a BTN-A event when you move one
way and a BTN-B event when you move the other way.  When setting
up buttons it pays to set the opentrack mapping curves with
a large dead zone. That way you can be certain of which key will be
sent to the game.  The `-d` parameter may be useful to see what
is being sent in response to your movements.

Any of the button-pairs can be bound the seventh recentering action.

The button bindings, and the heuristics for translating from
axes to button presses, is currently alpha level implementation.
It works, but the experience is not that great.

Snap Center Seventh Binding
---------------------------

Because button presses are an inexact positioning method, a seventh
binding can be assigned for a snap-center action. When bound, the
seventh binding generates a center event following other button actions,
when x, y, and z are near center.  To assign this button in a game:

  1. Choose unassigned button-pair, for example, number 12.
  2. Temporarily make it the only button-pair mapped, for
     example, `-b 0,0,0,0,0,0,12.
  3. Start `opentrack-stick`, it will output the message that
     `Auto center training is on`
  4. Start `opentrack` and the game.
  5. In the game key-mappings, find the key-mapping for
     move-head-to-centre and choose to map it to a new key.
  6. When the game is waiting for the new key to be input,
     nod your head fully up and down (change your head pitch).
  7. The game should bind a new key.
  8. At this point you are done and can now run opentrack-stick
     with auto-centering by passing the seventh binding along
     with your other bindings, for example `-b 9,10,11,4,5,0,12`


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

1. While training, temporarily, configure the game to run
   non-full-screen at a resolution that allows you to easily
   alt-tab opentrack's control-window and to an xterm/konsole
   in which is running opentrack-stick.
2. Backup `.../IL-2 Sturmovik Battle of Stalingrad/data/input/`
3. Start opentrack-stick with only one axis mapped. For example,
   to enable yaw output to virtual-control-4, pass -b 0,0,0,4,0,0..
4. Start opentrack, configure `Output` `UDP over network`
   with the port and address from step 1.
5. Check that the above is working (perhaps just run
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
8. Repeat for next desired mapping.

As long as they are started before the targeted game or
application, both opentrack-stick and opentrack can be
terminated and restarted without restarting the game.
Providing you can use alt-tab to switch between the
game, opentrack, and opentrack-stick, there is no
need to restart the game as you move through the training
process.

Having setup head yaw and pitch, I assigned opentrack-z to
virtual-control-1 and bound that to the game's head-zoom.
That's a relatively useful combo, and the one I find works best.
These bindings correspond to `-b 0,0,1,4,5,0`

The game doesn't support using axes for x, y, z head motion,
it expects these to be assigned to buttons.  I used the
pair `9. BTN_A<=>BTN_B,BTN` for x, side to side movement;
`10` for y, and `11` for z. And finally, 12 for auto-centering.

My final IL-2 BoX mappings are `-b 9,10,1,4,5,0,12`.
I additionally mapped head zoom to axis 1, so I can optionally
switch to the mapping `-b 9,10,1,4,5,0,12`.  The 9,10 and
12 button binds are just for beta testings at the moment,
feel free to try them, but I'm not sure thet

Opentrack Protocol
==================

Each opentrack UDP-Output packet contains 6 little-endian
doubles: x, y, z, yaw, pitch, and roll.

Limitations
===========

Discovering the neutral center position requires sitting
at center when opentrack-stick is started.

In the current implementation, the BTN's behave like snap actions.
There is almost no control over the magnitude of the action, for
example, once off center it's near impossible to make a small
series of moves to return to the center, hence the 7th binding
for auto-centering.

The smoothing values need more research, as do other smoothing
methods.  A small alpha (less than 0.1) seems particularly good
at allowing smooth transitions.

Axis virtual-controls `3` and `6` are untested.  Please use the
other axes and button actions if you can.

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
