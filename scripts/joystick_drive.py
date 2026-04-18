#!/usr/bin/env python3
"""
Workshop Phase 5 — read a USB gamepad and call chassis.move_velocity_radius.

TODO:
  - import roverchassis, chassis.ensureready(), pygame joystick init
  - map axes -> pct_angle / magnitude (same ranges as web UI, -100..100)
  - optional: from SGVHAK_Rover.control_mapping import polar_to_motion (after Phase 4)
  - deadband, deadman button, rate limit (~20 Hz), E-stop
  - run only on the machine that owns motor serial (usually the Pi)

Run from repo root with venv active, e.g.:
  PYTHONPATH=SGVHAK_Rover python3 scripts/joystick_drive.py
"""
from __future__ import print_function


def main():
  print("joystick_drive.py is a stub — complete Phase 5 in workshops/joystick-interface-workshop.md")
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
