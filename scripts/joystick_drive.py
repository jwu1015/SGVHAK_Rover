#!/usr/bin/env python3
"""
USB gamepad → same drive math as the web UI (control_mapping + move_velocity_radius).

Run on the machine wired to the motors (usually the Pi), from repo root, venv on:

  source venv/bin/activate
  pip install -e ".[joystick]"    # first time only
  python scripts/joystick_drive.py

Do NOT run this at the same time as something else that commands the same motors
(e.g. Flask drive page). Stop Flask first.

Default layout (Xbox-like): Left stick X → turn, Left stick Y → forward/back.
Hold bumper LB (button 4) to enable drive. Button 1 (B) = emergency stop (motors off).
Use --help to remap axes/buttons.
"""
from __future__ import print_function

import argparse
import os
import sys
import time


def _repo_root():
  return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_repo_path():
  root = _repo_root()
  if root not in sys.path:
    sys.path.insert(0, root)


def stop_all_motors(chassis):
  chassis.ensureready()
  for wheel in chassis.wheels.values():
    wheel.poweroff()


def main(argv=None):
  parser = argparse.ArgumentParser(description="Drive rover via USB gamepad.")
  parser.add_argument("--rate", type=float, default=20.0, help="Max commands per second (default 20)")
  parser.add_argument("--deadband", type=float, default=0.12, help="Stick deadzone 0..1 (default 0.12)")
  parser.add_argument("--axis-angle", type=int, default=0, help="Joystick axis index for turn (default 0)")
  parser.add_argument("--axis-speed", type=int, default=1, help="Joystick axis index for forward/back (default 1)")
  parser.add_argument("--invert-speed", action="store_true", help="Flip forward/back if rover runs backward")
  parser.add_argument("--deadman-button", type=int, default=4, help="Hold this button to enable drive (default 4 = LB)")
  parser.add_argument("--no-deadman", action="store_true", help="DANGEROUS: drive without hold-to-enable (testing only)")
  parser.add_argument("--estop-button", type=int, default=1, help="Press to cut motor power (default 1 = B)")
  parser.add_argument("--list", action="store_true", help="List connected joysticks and exit")
  args = parser.parse_args(argv)

  _ensure_repo_path()

  try:
    import pygame
  except ImportError:
    print("Install pygame first:  pip install -e \".[joystick]\"")
    return 1

  from SGVHAK_Rover import control_mapping
  from SGVHAK_Rover.roverchassis import chassis

  pygame.init()
  pygame.joystick.init()
  n = pygame.joystick.get_count()
  if args.list or n == 0:
    if n == 0:
      print("No joysticks detected.")
    for i in range(n):
      j = pygame.joystick.Joystick(i)
      j.init()
      print("%d: %s" % (i, j.get_name()))
      j.quit()
    return 0 if n else 1

  js = pygame.joystick.Joystick(0)
  js.init()
  print("Using joystick 0: %s" % (js.get_name(),))
  print("Hold button %d to drive; button %d = stop motors. Ctrl+C to quit." % (
      args.deadman_button, args.estop_button))

  ch = chassis()
  ch.ensureready()

  min_interval = 1.0 / max(1.0, args.rate)
  last_cmd = 0.0
  deadband = max(0.0, min(0.99, args.deadband))

  def apply_deadband(v):
    if abs(v) < deadband:
      return 0.0
    # rescale so edge past deadband maps to full range
    sign = 1.0 if v > 0 else -1.0
    u = (abs(v) - deadband) / (1.0 - deadband)
    return sign * max(-1.0, min(1.0, u))

  try:
    running = True
    while running:
      pygame.event.pump()

      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False

      if js.get_button(args.estop_button):
        stop_all_motors(ch)
        last_cmd = time.monotonic()
        time.sleep(0.05)
        continue

      enable = True if args.no_deadman else js.get_button(args.deadman_button)
      try:
        ax_turn = float(js.get_axis(args.axis_angle))
        ax_speed = float(js.get_axis(args.axis_speed))
      except pygame.error:
        ax_turn = 0.0
        ax_speed = 0.0

      ax_turn = apply_deadband(ax_turn)
      ax_speed = apply_deadband(ax_speed)
      if args.invert_speed:
        ax_speed = -ax_speed

      pct_angle = max(-100.0, min(100.0, ax_turn * 100.0))
      magnitude = max(-100.0, min(100.0, ax_speed * 100.0))

      if not enable:
        pct_angle = 0.0
        magnitude = 0.0

      now = time.monotonic()
      if now - last_cmd < min_interval:
        time.sleep(0.005)
        continue
      last_cmd = now

      try:
        velocity, radius = control_mapping.polar_to_motion(ch, pct_angle, magnitude)
        ch.move_velocity_radius(velocity, radius)
      except ValueError as ex:
        # Turn too tight for geometry — hold last safe command or coast
        print("Drive command skipped: %s" % (ex,))

  except KeyboardInterrupt:
    print("\nInterrupted.")
  finally:
    stop_all_motors(ch)
    js.quit()
    pygame.quit()
    print("Motors stopped, joystick closed.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
