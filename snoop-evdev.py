#!/usr/bin/python3
"""
snoop-evdev - listen to evdev events for the specified device
==============================================================

Lists the device capabilities and events

Usage:
======

    python3 snoop-evdev.py /dev/input/event<N>

Credits
=======
Based on https://python-evdev.readthedocs.io/en/latest/tutorial.html

"""
import sys

from evdev import InputDevice, categorize, ecodes

dev = InputDevice(sys.argv[1])

print(dev)
for key, item in dev.capabilities(verbose=True).items():
    print(key)
    for ev in item:
        print(f"    {ev}")

for event in dev.read_loop():
    # Only interested in KEY, ABS and REL
    if event.type in [ecodes.EV_KEY, ecodes.EV_ABS, ecodes.EV_REL]:
        print(categorize(event), event.value)
