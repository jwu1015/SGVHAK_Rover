"""
Native desktop rover control (no browser, no Flask).

  — Sliders for velocity % and angle % (same meaning as the web “Angle/Velocity” page).
  — Optional USB gamepad (pygame): same defaults as scripts/joystick_drive.py.

Run from the project root (folder with config_*.json):

  source venv/bin/activate
  pip install -e ".[joystick]"    # only if you want USB gamepad support
  python -m SGVHAK_Rover.desktop_app

On Raspberry Pi OS you may need:  sudo apt install python3-tk

Do not run this while Flask or scripts/joystick_drive.py is also commanding the same motors.
"""
from __future__ import print_function

import os
import sys
import time


def _repo_root():
  here = os.path.dirname(os.path.abspath(__file__))
  return os.path.dirname(here)


def stop_all_motors(chassis):
  chassis.ensureready()
  for wheel in chassis.wheels.values():
    wheel.poweroff()


def apply_deadband(v, deadband):
  deadband = max(0.0, min(0.99, deadband))
  if abs(v) < deadband:
    return 0.0
  sign = 1.0 if v > 0 else -1.0
  u = (abs(v) - deadband) / (1.0 - deadband)
  return sign * max(-1.0, min(1.0, u))


class RoverDesktopApp(object):
  def __init__(self):
    try:
      import tkinter as tk
      from tkinter import ttk, messagebox
    except ImportError:
      print("Tkinter is required. On Debian/Ub Raspberry Pi: sudo apt install python3-tk")
      raise

    self.messagebox = messagebox
    self.root = tk.Tk()
    self.root.title("SGVHAK Rover — Desktop control")
    self.root.minsize(420, 320)

    repo = _repo_root()
    if os.getcwd() != repo:
      os.chdir(repo)

    from . import control_mapping
    from .roverchassis import chassis

    self.control_mapping = control_mapping
    self.ch = chassis()
    self.ch.ensureready()

    self._pygame = None
    self._pygame_inited = False
    self.js = None

    self.rate_hz = 20.0
    self.deadband = 0.12
    self.axis_angle = 0
    self.axis_speed = 1
    self.invert_speed = tk.BooleanVar(value=False)
    self.deadman_button = 4
    self.estop_button = 1
    self.use_gamepad = tk.BooleanVar(value=False)
    self.last_cmd = 0.0
    self.min_interval = 1.0 / max(1.0, self.rate_hz)

    self.status = tk.StringVar(value="Ready — use sliders or enable USB gamepad.")

    main = ttk.Frame(self.root, padding=12)
    main.grid(row=0, column=0, sticky="nsew")
    self.root.columnconfigure(0, weight=1)
    self.root.rowconfigure(0, weight=1)

    ttk.Label(main, text="Velocity % (forward / back)", font=("Helvetica", 11)).grid(row=0, column=0, sticky="w")
    self.var_vel = tk.DoubleVar(value=0.0)
    self.scale_vel = ttk.Scale(main, from_=-100, to=100, variable=self.var_vel, orient=tk.HORIZONTAL, length=360)
    self.scale_vel.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    main.columnconfigure(0, weight=1)

    ttk.Label(main, text="Angle % (left / right turn hint)", font=("Helvetica", 11)).grid(row=2, column=0, sticky="w")
    self.var_ang = tk.DoubleVar(value=0.0)
    self.scale_ang = ttk.Scale(main, from_=-100, to=100, variable=self.var_ang, orient=tk.HORIZONTAL, length=360)
    self.scale_ang.grid(row=3, column=0, sticky="ew", pady=(0, 8))

    ttk.Checkbutton(main, text="Use USB gamepad (left stick; hold LB / button 4; B / button 1 = stop)",
                    variable=self.use_gamepad, command=self._on_gamepad_toggle).grid(row=4, column=0, sticky="w", pady=4)
    ttk.Checkbutton(main, text="Invert forward/back on gamepad stick",
                    variable=self.invert_speed).grid(row=5, column=0, sticky="w", pady=2)

    btn_row = ttk.Frame(main)
    btn_row.grid(row=6, column=0, sticky="ew", pady=8)
    ttk.Button(btn_row, text="Stop motors", command=self._stop_clicked).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(btn_row, text="Zero sliders", command=self._zero_sliders).pack(side=tk.LEFT)

    ttk.Label(main, textvariable=self.status, wraplength=400, foreground="#333").grid(row=7, column=0, sticky="w", pady=8)

    self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    self._tick_after = None

  def _zero_sliders(self):
    self.var_vel.set(0)
    self.var_ang.set(0)

  def _stop_clicked(self):
    stop_all_motors(self.ch)
    self.status.set("Motors stopped.")

  def _on_close(self):
    if self._tick_after is not None:
      self.root.after_cancel(self._tick_after)
    stop_all_motors(self.ch)
    if self.js is not None:
      try:
        self.js.quit()
      except Exception:
        pass
      self.js = None
    if self._pygame_inited and self._pygame is not None:
      try:
        self._pygame.quit()
      except Exception:
        pass
    self.root.destroy()

  def _on_gamepad_toggle(self):
    if not self.use_gamepad.get():
      if self.js is not None:
        try:
          self.js.quit()
        except Exception:
          pass
        self.js = None
      self.status.set("Gamepad off — using sliders only.")
      return
    if not self._init_pygame():
      self.use_gamepad.set(False)
      self.messagebox.showerror("Gamepad", "Install pygame: pip install -e \".[joystick]\"")
      return
    self._open_joystick()
    if self.js is None:
      self.use_gamepad.set(False)
      self.messagebox.showwarning("Gamepad", "No USB controller found. Using sliders only.")
    else:
      self.status.set("Gamepad: %s — hold button %d to drive." % (self.js.get_name(), self.deadman_button))

  def _init_pygame(self):
    if self._pygame_inited:
      return True
    try:
      import pygame
      self._pygame = pygame
      pygame.init()
      pygame.joystick.init()
      self._pygame_inited = True
      return True
    except ImportError:
      return False

  def _open_joystick(self):
    pygame = self._pygame
    pygame.joystick.quit()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
      self.js = None
      return
    self.js = pygame.joystick.Joystick(0)
    self.js.init()

  def _read_inputs(self):
    """Returns (pct_angle, magnitude, enable_motion, estop)."""
    if self.use_gamepad.get() and self.js is not None:
      pygame = self._pygame
      pygame.event.pump()
      if self.js.get_button(self.estop_button):
        return 0.0, 0.0, False, True
      enable = self.js.get_button(self.deadman_button)
      try:
        ax_turn = float(self.js.get_axis(self.axis_angle))
        ax_speed = float(self.js.get_axis(self.axis_speed))
      except Exception:
        ax_turn = 0.0
        ax_speed = 0.0
      ax_turn = apply_deadband(ax_turn, self.deadband)
      ax_speed = apply_deadband(ax_speed, self.deadband)
      if self.invert_speed.get():
        ax_speed = -ax_speed
      pct = max(-100.0, min(100.0, ax_turn * 100.0))
      mag = max(-100.0, min(100.0, ax_speed * 100.0))
      if not enable:
        pct, mag = 0.0, 0.0
      return pct, mag, True, False

    pct = float(self.var_ang.get())
    mag = float(self.var_vel.get())
    return pct, mag, True, False

  def tick(self):
    now = time.monotonic()
    try:
      pct_angle, magnitude, _, estop = self._read_inputs()
      if estop:
        stop_all_motors(self.ch)
        self.last_cmd = now
        self.status.set("E-stop (gamepad) — motors off.")
      elif now - self.last_cmd >= self.min_interval:
        self.last_cmd = now
        velocity, radius = self.control_mapping.polar_to_motion(self.ch, pct_angle, magnitude)
        self.ch.move_velocity_radius(velocity, radius)
        self.status.set("Driving: vel=%.0f angle%%=%.0f (radius math in chassis)" % (magnitude, pct_angle))
    except ValueError as ex:
      self.status.set("Command skipped: %s" % (ex,))
    except Exception as ex:
      self.status.set("Error: %s" % (ex,))

    self._tick_after = self.root.after(50, self.tick)

  def run(self):
    self._tick_after = self.root.after(50, self.tick)
    self.root.mainloop()


def main():
  repo = _repo_root()
  if not os.path.isfile(os.path.join(repo, "config_roverchassis.json")):
    print("config_roverchassis.json not found. Run from project root or see NEW_HELPERS_READ_THIS.txt")
    return 1
  if os.getcwd() != repo:
    os.chdir(repo)
  app = RoverDesktopApp()
  app.run()
  return 0


if __name__ == "__main__":
  sys.exit(main())
