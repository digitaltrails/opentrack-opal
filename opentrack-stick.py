#!/usr/bin/python3
"""
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
axes to button presses results in an experience more like
a snap action rather than a smooth motion along an axis. It's
much like that experienced with a physical three-state HAT
axis control.

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

When in the game, after any other virtual-button triggered motion,
moving your head to roughly center/straight neutral position will
automatically trigger the control.

The auto-center control won't be triggered after any virtual-stick
motions. Stick motion is precise and absolute. Returning to the stick
neutral position does not require any assistance.


Quick Start
===========

Get the python (python-3) ebdev library:

    pip install ebdev

Requires udev rule for access:

    sudo cat > /etc/udev/rules.d/65-opentrack-evdev.rules <EOF
    KERNEL=="event*", SUBSYSTEM=="input", ATTRS{name}=="opentrack*",  TAG+="uaccess"
    EOF
    sudo udevadm control --reload-rules ; udevadm trigger

Start the 'opentrack-stick', 'opentrack':

  1. Run this script:  `python3 opentrack-stick.py`
  2. Start opentrack+head-tracking-device.
  3. Select Output `UDP over network`; configure the
     output option to IP address 127.0.0.1, port 5005.
  3. Move your head to the neutral orientation in the center position.
  4. Start opentrack tracking.
  5. Start a game/application that makes use of a joystick, It's best
     to start the game last so that the stick is detectable
     when it initialises.
  6. In the game/application map game actions to axes, hat, and buttons
     for the new joystick called `Microsoft X-Box 360`.

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

Configuring the neutral center position requires sitting
at center when opentrack-stick is started.  It also requires
agreed alignment with 'opentrack' - move your head to the
neutral position before starting/re-starting tracking in either.

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
"""
import math
import select
import socket
import struct
import sys
import time
from collections import namedtuple
from pathlib import Path

import evdev
from evdev import AbsInfo
from evdev import ecodes

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

OpenTrackDataItem = namedtuple("OpenTrackDataItem", "name value min max")

auto_center_needed = False


class OpenTrackStick:

    def __init__(self, wait_secs=0.001, smoothing=500, smooth_alpha=0.1, bindings=(1, 2, 3, 4, 5, 6), debug=False):
        self.wait_secs = wait_secs
        self.debug = debug
        self.show_activity = False  # Summarises activity in one char outputs.
        self.start_time = time.time_ns()
        self.smoothing = smoothing
        self.smooth_alpha = smooth_alpha
        self.activity_count = 0
        self.center = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.center_found = False
        print(f"Input wait max: {wait_secs * 1000} ms - will then feed the smoother with repeat values.")
        print(f"Smoothing: n={self.smoothing} alpha={self.smooth_alpha}")
        self.opentrack_data_items = [OpenTrackDataItem('x', 0, -75, 75),
                                     OpenTrackDataItem('y', 0, -75, 75),
                                     OpenTrackDataItem('z', 0, -75, 75),
                                     OpenTrackDataItem('yaw', 0, -90, 90),
                                     OpenTrackDataItem('pitch', 0, -90, 90),
                                     OpenTrackDataItem('roll', 0, -90, 90)]
        self.abs_outputs_def_list = [
            StickOutputDef(ecodes.ABS_RX, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0),
                           smoothing=smoothing, smooth_alpha=smooth_alpha),
            StickOutputDef(ecodes.ABS_RY, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0),
                           smoothing=smoothing, smooth_alpha=smooth_alpha),
            StickOutputDef(ecodes.ABS_RZ, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0),
                           smoothing=smoothing, smooth_alpha=smooth_alpha, functional=False),
            StickOutputDef(ecodes.ABS_X, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0),
                           smoothing=smoothing, smooth_alpha=smooth_alpha),
            StickOutputDef(ecodes.ABS_Y, AbsInfo(value=0, min=-32767, max=32767, fuzz=16, flat=128, resolution=0),
                           smoothing=smoothing, smooth_alpha=smooth_alpha),
            StickOutputDef(ecodes.ABS_Z, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0),
                           smoothing=smoothing, smooth_alpha=smooth_alpha, functional=False),
            HatOutputDef(ecodes.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
            HatOutputDef(ecodes.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)), ]
        self.btn_output_def_list = [
            BtnPairOutputDef(ecodes.BTN_A, ecodes.BTN_B),  # This pair works
            BtnPairOutputDef(ecodes.BTN_X, ecodes.BTN_Y),
            BtnPairOutputDef(ecodes.BTN_TL, ecodes.BTN_TR),
            BtnPairOutputDef(ecodes.BTN_SELECT, ecodes.BTN_START),
            BtnPairOutputDef(ecodes.BTN_MODE, ecodes.BTN_TR),
        ]
        self.all_output_def_list = self.abs_outputs_def_list + self.btn_output_def_list
        print(f"Opentrack inputs:", ",".join([otd.name for otd in self.opentrack_data_items]))
        print(f"Available outputs:\n   ",
              ",\n    ".join(["0. discard/ignore input"] + [f"{i + 1}. {d.name}{'' if d.functional else ' (Not tested!)'}"
                                                            for i, d in enumerate(self.all_output_def_list)]))
        print("Bound outputs: -b {} => ({})".format(
            ','.join(str(i) for i in bindings),
            ','.join((f"{ot.name}->discard" if i == 0 else f"{ot.name}->{self.all_output_def_list[i - 1].name}") for i, ot in
                     zip(bindings[0:6], self.opentrack_data_items))))
        # Have to include the buttons for the hid device to be ID'ed as a joystick:
        ui_input_capabilities = {
            ecodes.EV_KEY: [ecodes.BTN_A, ecodes.BTN_GAMEPAD, ecodes.BTN_SOUTH,
                            ecodes.BTN_B, ecodes.BTN_EAST, ecodes.BTN_NORTH, ecodes.BTN_X,
                            ecodes.BTN_WEST, ecodes.BTN_Y, ecodes.BTN_TL, ecodes.BTN_TR,
                            ecodes.BTN_SELECT, ecodes.BTN_START, ecodes.BTN_MODE, ecodes.BTN_THUMBL, ecodes.BTN_THUMBR,
                            ],
            ecodes.EV_ABS: [(output_def.evdev_code, output_def.evdev_abs_info) for output_def in self.abs_outputs_def_list],
            ecodes.EV_FF: [ecodes.FF_EFFECT_MIN, ecodes.FF_RUMBLE]
        }
        self.hid_device = evdev.UInput(ui_input_capabilities, name="Microsoft X-Box 360 pad 0", vendor=0x0738, product=0x028F)
        self.destination_list = []
        for destination_num, opentrack_cap in zip(bindings[0:6], self.opentrack_data_items):
            if destination_num == 0:
                self.destination_list.append(None)
                print(f"Binding opentrack {opentrack_cap.name} to discard output")
            else:
                index = destination_num - 1
                destination = self.all_output_def_list[index]
                destination.bind(opentrack_cap)
                self.destination_list.append(destination)
                print(f"Binding opentrack {opentrack_cap.name} to {destination.name} output")
        self.auto_center_destination = None
        self.auto_center_training = all(d is None for d in self.destination_list)
        if len(bindings) == 7:
            self.auto_center_training = all(btn.opentrack_info is None for btn in self.btn_output_def_list)
            ac_def_index = bindings[6] - 1
            self.auto_center_destination = self.all_output_def_list[ac_def_index]
            print(f"Binding auto-center event to to {self.auto_center_destination.name} output")
            if self.auto_center_training:
                print(f"Auto center training is on - to map, nod when in game mapping dialog.")
                dummy_index = 10 if ac_def_index != 10 else 11
                dummy_destination_def = AcdTrainingDummyOutputDef(ecodes.BTN_A, ecodes.BTN_B)
                dummy_destination_def.bind(self.opentrack_data_items[4])
                self.destination_list[4] = dummy_destination_def
        print("\n*** CENTER CALIBRATION - PLEASE SIT STILL AND CENTERED (you have 5 seconds to get into position) ***")
        time.sleep(5.0)

    def start(self, udp_ip=UDP_IP, udp_port=UDP_PORT):
        print(f"UDP IP={udp_ip} PORT={udp_port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 48)
        sock.bind((udp_ip, udp_port))
        data_exhausted = True
        current = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        previous_send_time = 0
        min_send_nanos = int(1_000_000_000 * self.wait_secs / 2)
        while True:
            self.print_activity("B" if data_exhausted else None) if self.show_activity else None
            sock.setblocking(data_exhausted)
            # Use previous data value if none is ready - keeps the mouse moving smoothly in the current direction
            if data_exhausted or select.select([sock], [], [], self.wait_secs)[0]:
                data, _ = sock.recvfrom(48)
                self.print_activity("R") if self.show_activity else None
                # Unpack 6 little endian doubles into a list:
                current = struct.unpack('<6d', data[:48])
                data_exhausted = False
            # Stop and wait if the data has settled down and is not changing.
            # Note: smoothing will keep changing the data for a while even though input may have stopped arriving.
            now = time.time_ns()
            if not data_exhausted:
                if now - previous_send_time < min_send_nanos:
                    self.print_activity(".") if self.show_activity else None
                    time.sleep(min_send_nanos / 1_000_000_000.0)
                data_exhausted = self.__send_to_hid__(current)
                self.print_activity("+") if self.show_activity else None
                previous_send_time = now
            else:
                if self.debug:
                    print(f"@{(time.time_ns() - self.start_time) / 1_000_000_000:.3f} sec waiting for new data...", )

    def print_activity(self, indicator_char):
        if indicator_char:
            self.activity_count += 1
            print(indicator_char, end='\n' if self.activity_count % 100 == 0 else '')

    def all_output_defs(self):
        return self.abs_outputs_def_list + self.btn_output_def_list

    def __send_to_hid__(self, values):
        global auto_center_needed
        data_exhausted = True
        send_t = time.time_ns() if self.debug else 0
        sent_any = False
        debug_msg = []
        for i, destination_def, raw_value in zip(range(6), self.destination_list, values):
            if destination_def:
                cooked_value = destination_def.cooked_value(raw_value, self.center[i])
                data_exhausted &= destination_def.data_exhausted
                sent_any |= destination_def.send_to_hid(self.hid_device, cooked_value)
                debug_msg.append(destination_def.debug_value(raw_value, cooked_value)) if self.debug and cooked_value else None
        if self.auto_center_training:
            sent_any = True
        if sent_any:
            self.hid_device.syn()
            now = time.time_ns()
            if self.__auto_center__(values):
                pass
                #debug_msg.append(self.auto_center_destination.debug_value(0.0, 1)) if self.debug else None
            if self.debug:
                messages = ", ".join(debug_msg)
                if messages != '':
                    print(f"@{(now - self.start_time) / 1_000_000_000:.3f} sec, {(now - send_t) / 1_000_000:.2f} ms,"
                          f"data_exhausted={data_exhausted}",
                          messages)

        return data_exhausted

    def __auto_center__(self, values):
        if not self.center_found:
            # Assume centered at the start
            self.center = values
            self.center_found = True
            print("*** CENTER CALIBRATED TO ",
                  ", ".join([f"{d.name}={v:.2f}" for d,v in zip(self.opentrack_data_items, values)]),
                  " ***")
            print(f"\nAuto centering is enabled.") if self.auto_center_destination is not None else None
        if self.auto_center_destination is None:
            return False
        global auto_center_needed
        if auto_center_needed:
            for i, center_value, value in zip(range(6), self.center, values):  # Ignore z - forward backward offset
                if abs(center_value - value) > 15.0:
                    print(f"Off center {time.strftime('%H:%M:%S')}") if self.debug else False
                    return False
            self.auto_center_destination.reset()
            self.auto_center_destination.send_to_hid(self.hid_device, 1)
            self.hid_device.syn()
            time.sleep(0.02)  # Time necessary for the key to register
            self.auto_center_destination.send_to_hid(self.hid_device, 0)
            self.hid_device.syn()
            auto_center_needed = False
            return True
        return False

class OutputDef:
    def __init__(self, evdev_type, evdev_code, evdev_name, functional=True):
        self.evdev_type = evdev_type
        self.evdev_code = evdev_code
        self.opentrack_info = None
        self.name = str(evdev_name).replace("'", "").replace(' ', '')
        self.data_exhausted = True
        self.functional = functional

    def bind(self, opentrack_info):
        self.opentrack_info = opentrack_info

    def cooked_value(self, raw_value, center_value):
        pass

    def send_to_hid(self, hid_device, cooked_value):
        if cooked_value is not None:
            hid_device.write(self.evdev_type, self.evdev_code, cooked_value)
            return True
        return False

    def reset(self):
        pass

    def debug_value(self, raw_value, value):
        return f"{self.name}->{value} ({self.opentrack_info.name}={raw_value:.4f})"


class StickOutputDef(OutputDef):

    def __init__(self, evdev_code, evdev_abs_info, smoothing=500, smooth_alpha=0.1, output_plot_data=False, functional=True):
        super().__init__(ecodes.EV_ABS, evdev_code, ecodes.ABS[evdev_code], functional)
        self.evdev_abs_info = evdev_abs_info
        self.previous_smoothed_value = 0.0
        self.smoother = Smooth(n=smoothing, alpha=smooth_alpha)
        self.output_plot_data = output_plot_data

    def cooked_value(self, raw_value, center_value):
        ev_info = self.evdev_abs_info
        ot_info = self.opentrack_info
        # This may feed repeat data into the smoother, that should result in the latest value becoming stronger over time.
        smoothed = self.smoother.smooth(raw_value)
        self.data_exhausted = math.isclose(smoothed, self.previous_smoothed_value, abs_tol=0.1)
        self.previous_smoothed_value = smoothed
        cooked = ev_info.min + round(((smoothed - ot_info.min) / (ot_info.max - ot_info.min)) * (ev_info.max - ev_info.min))
        if self.output_plot_data:
            print("EVENT_DATA", self.name, raw_value, smoothed, cooked)
        return cooked

    def send_to_hid(self, hid_device, cooked_value):
        hid_device.write(self.evdev_type, self.evdev_code, cooked_value)
        return True


class HatOutputDef(OutputDef):

    def __init__(self, evdev_code, evdev_abs_info, functional=True):
        super().__init__(ecodes.EV_ABS, evdev_code, ecodes.ABS[evdev_code], functional)
        self.evdev_abs_info = evdev_abs_info
        self.sent_previous_cooked = 0

    def cooked_value(self, raw_value, center_value):
        dif = round(raw_value - center_value)
        return 0 if -15 < dif < 15 else dif // abs(dif)

    def send_to_hid(self, hid_device, cooked_value):
        if cooked_value == self.sent_previous_cooked:
            # Don't send again until the key value changes to a different value (-1/0/1)
            return False
        self.sent_previous_cooked = cooked_value
        super().send_to_hid(hid_device, cooked_value)
        if cooked_value == 0:
            global auto_center_needed
            auto_center_needed = True
        return True

class BtnPairOutputDef(OutputDef):

    def __init__(self, evdev_code_minus, evdev_code_plus, functional=True):
        super().__init__(ecodes.EV_KEY, evdev_code_minus, f"{ecodes.BTN[evdev_code_minus]} <=> {ecodes.BTN[evdev_code_plus]}",
                         functional)
        self.name_minus = str(ecodes.BTN[evdev_code_minus]).replace(' ', '')
        self.name_plus = str(ecodes.BTN[evdev_code_plus]).replace(' ', '')
        self.evdev_code_minus = evdev_code_minus
        self.evdev_code_plus = evdev_code_plus
        self.previous_cooked_value = None
        self.previous_code = None
        self.start_time = time.time_ns()

    def cooked_value(self, raw_value, center_value):
        dif = round(raw_value - center_value)
        direction = 0 if -15 < dif < 15 else dif // abs(dif)
        if direction != 0:
            self.evdev_code = self.evdev_code_plus if direction > 0 else self.evdev_code_minus
            return 1  # Button down
        return 0  # Button up

    def send_to_hid(self, hid_device, cooked_value=None):
        if self.evdev_code == self.previous_code and cooked_value == self.previous_cooked_value:
            # Don't send again until the key value changes to a different value
            return super().send_to_hid(hid_device, None)
        self.previous_code = self.evdev_code
        self.previous_cooked_value = cooked_value
        super().send_to_hid(hid_device, cooked_value)
        if cooked_value == 0:
            global auto_center_needed
            auto_center_needed = True
        return True

    def reset(self):
        self.previous_cooked_value = None
        self.previous_code = None

    def debug_value(self, raw_value, value):
        name = self.name_plus if self.evdev_code == self.evdev_code_plus else self.name_minus
        source = self.opentrack_info.name if self.opentrack_info is not None else "auto-centering"
        return f"{self.name}->{name} {value} ({source}={raw_value})"


class AcdTrainingDummyOutputDef(BtnPairOutputDef):

    def __init__(self, evdev_code_minus, evdev_code_plus, functional=True):
        super().__init__(evdev_code_minus, evdev_code_plus, functional)

    def send_to_hid(self, hid_device, cooked_value=None):
        repeating = self.evdev_code == self.previous_code and cooked_value == self.previous_cooked_value
        if repeating:
            return False
        self.previous_code = self.evdev_code
        self.previous_cooked_value = cooked_value
        if cooked_value == 0:
            global auto_center_needed
            auto_center_needed = True
        return True
    def debug_value(self, raw_value, value):
        return ''

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
    destinations = [int(c) for c in (sys.argv[sys.argv.index('-b') + 1] if '-b' in sys.argv else "1,2,3,4,5,6").split(',')]
    stick = OpenTrackStick(wait_secs=wait_secs,
                           smoothing=smooth_n,
                           smooth_alpha=smooth_alpha,
                           bindings=destinations,
                           debug='-d' in sys.argv)
    udp_ip = sys.argv[sys.argv.index('-i') + 1] if '-i' in sys.argv else UDP_IP
    udp_port = sys.argv[sys.argv.index('-p') + 1] if '-p' in sys.argv else UDP_PORT
    stick.start(udp_ip=udp_ip, udp_port=udp_port)


if __name__ == '__main__':
    main()
