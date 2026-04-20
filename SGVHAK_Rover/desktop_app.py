"""
Native desktop rover control (no browser, no Flask).

  — On-screen polar joystick (same math as the web Polar pad / drive.js).
  — Sliders (same as Angle/Velocity web page).
  — Optional USB gamepad (pygame), same defaults as scripts/joystick_drive.py.

Pick one input source at a time: Polar pad | Sliders | USB gamepad.

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

from . import polar_pad_math


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

    self._tk = tk
    self.messagebox = messagebox
    self.root = tk.Tk()
    self.root.title("SGVHAK Rover — Desktop control")
    self.root.minsize(460, 520)

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
    self.source = tk.StringVar(value="pad")
    self.last_cmd = 0.0
    self.min_interval = 1.0 / max(1.0, self.rate_hz)

    # Polar pad (matches drive.html ui_angle=70, Knob sizes vs padSize)
    self.pad_size = 280
    self.pad_ui_angle = 70
    self.pad_max_r = self.pad_size * 0.425
    self.pad_knob_r = self.pad_size * 0.1
    self.pad_cx = self.pad_size // 2
    self.pad_cy = self.pad_size // 2
    self.pad_kx = 0
    self.pad_ky = 0
    self.pad_mag = 0
    self.pad_pct = 0
    self.pad_tracking = False

    self.status = tk.StringVar(value="Ready — choose Polar pad, Sliders, or USB gamepad.")

    main = ttk.Frame(self.root, padding=12)
    main.grid(row=0, column=0, sticky="nsew")
    self.root.columnconfigure(0, weight=1)
    self.root.rowconfigure(0, weight=1)

    ttk.Label(main, text="Input source", font=("Helvetica", 11, "bold")).grid(row=0, column=0, sticky="w")
    src = ttk.Frame(main)
    src.grid(row=1, column=0, sticky="w", pady=(0, 6))
    ttk.Radiobutton(src, text="Polar pad (on-screen joystick)", variable=self.source, value="pad",
                    command=self._on_source_change).pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(src, text="Sliders", variable=self.source, value="sliders",
                    command=self._on_source_change).pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(src, text="USB gamepad", variable=self.source, value="gamepad",
                    command=self._on_source_change).pack(side=tk.LEFT)

    self.pad_canvas = tk.Canvas(main, width=self.pad_size, height=self.pad_size, highlightthickness=1,
                                highlightbackground="#888")
    self.pad_canvas.grid(row=2, column=0, pady=(0, 10))
    self._oval_bg = None
    self._oval_knob = None
    self._bind_pad_events()

    ttk.Label(main, text="Velocity % (used when Sliders is selected, or mirrors pad)",
              font=("Helvetica", 10)).grid(row=3, column=0, sticky="w")
    self.var_vel = tk.DoubleVar(value=0.0)
    self.scale_vel = ttk.Scale(main, from_=-100, to=100, variable=self.var_vel, orient=tk.HORIZONTAL, length=360)
    self.scale_vel.grid(row=4, column=0, sticky="ew", pady=(0, 6))
    main.columnconfigure(0, weight=1)

    ttk.Label(main, text="Angle %", font=("Helvetica", 10)).grid(row=5, column=0, sticky="w")
    self.var_ang = tk.DoubleVar(value=0.0)
    self.scale_ang = ttk.Scale(main, from_=-100, to=100, variable=self.var_ang, orient=tk.HORIZONTAL, length=360)
    self.scale_ang.grid(row=6, column=0, sticky="ew", pady=(0, 6))

    ttk.Checkbutton(main, text="Invert forward/back on USB gamepad stick",
                    variable=self.invert_speed).grid(row=7, column=0, sticky="w", pady=2)

    btn_row = ttk.Frame(main)
    btn_row.grid(row=8, column=0, sticky="ew", pady=8)
    ttk.Button(btn_row, text="Stop motors", command=self._stop_clicked).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(btn_row, text="Center pad & zero sliders", command=self._center_pad).pack(side=tk.LEFT)

    ttk.Label(main, textvariable=self.status, wraplength=420, foreground="#333").grid(row=9, column=0, sticky="w", pady=6)

    self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    self._tick_after = None
    self._on_source_change()
    self._pad_redraw()

  def _bind_pad_events(self):
    tk = self._tk
    self.pad_canvas.bind("<ButtonPress-1>", self._pad_press)
    self.pad_canvas.bind("<B1-Motion>", self._pad_drag)
    self.pad_canvas.bind("<ButtonRelease-1>", self._pad_release)
    # Enter pad with click on knob only (same as web); motion only when tracking
    self.pad_canvas.bind("<Leave>", self._pad_leave)
    self.root.bind_all("<ButtonRelease-1>", self._global_mouse_release)

  def _global_mouse_release(self, event):
    if self.pad_tracking:
      self._pad_release(event)

  def _pad_contains_knob(self, x, y):
    """Hit test in pad coordinates (center-relative), like drive.js Knob.contains."""
    return (x > (self.pad_kx - self.pad_knob_r) and x < (self.pad_kx + self.pad_knob_r) and
            y > (self.pad_ky - self.pad_knob_r) and y < (self.pad_ky + self.pad_knob_r))

  def _pad_event_xy(self, event):
    return event.x - self.pad_cx, event.y - self.pad_cy

  def _pad_press(self, event):
    if self.source.get() != "pad":
      return
    x, y = self._pad_event_xy(event)
    if self._pad_contains_knob(x, y):
      self.pad_tracking = True
      self._pad_move(x, y)

  def _pad_drag(self, event):
    if self.source.get() != "pad" or not self.pad_tracking:
      return
    x, y = self._pad_event_xy(event)
    self._pad_move(x, y)

  def _pad_move(self, x, y):
    self.pad_kx, self.pad_ky, self.pad_mag, self.pad_pct = polar_pad_math.polar_pad_compute(
        x, y, self.pad_ui_angle, self.pad_max_r)
    self.var_vel.set(float(self.pad_mag))
    self.var_ang.set(float(self.pad_pct))
    self._pad_redraw()

  def _pad_release(self, event):
    if not self.pad_tracking:
      return
    self.pad_tracking = False
    self.pad_kx = 0
    self.pad_ky = 0
    self.pad_mag = 0
    self.pad_pct = 0
    self.var_vel.set(0.0)
    self.var_ang.set(0.0)
    self._pad_redraw()

  def _pad_leave(self, event):
    # Do not cancel drag when pointer leaves canvas while dragging
    pass

  def _pad_redraw(self):
    tk = self._tk
    c = self.pad_canvas
    c.delete("all")
    r = int(self.pad_size * 0.85 / 2)
    c.create_oval(self.pad_cx - r, self.pad_cy - r, self.pad_cx + r, self.pad_cy + r, fill="#0000FF", outline="#000088")
    fill = "#00FF00" if self.pad_tracking else "#FF0000"
    kx = self.pad_cx + self.pad_kx
    ky = self.pad_cy + self.pad_ky
    kr = int(self.pad_knob_r)
    c.create_oval(kx - kr, ky - kr, kx + kr, ky + kr, fill=fill, outline="#660000")

  def _center_pad(self):
    self.pad_tracking = False
    self.pad_kx = 0
    self.pad_ky = 0
    self.pad_mag = 0
    self.pad_pct = 0
    self.var_vel.set(0.0)
    self.var_ang.set(0.0)
    self._pad_redraw()
    stop_all_motors(self.ch)
    self.status.set("Pad centered and sliders zeroed; motors stopped.")

  def _on_source_change(self):
    self.pad_tracking = False
    src = self.source.get()
    if src == "gamepad":
      if not self._init_pygame():
        self.source.set("pad")
        self.messagebox.showerror("Gamepad", "Install pygame: pip install -e \".[joystick]\"")
        return
      self._open_joystick()
      if self.js is None:
        self.source.set("pad")
        self.messagebox.showwarning("Gamepad", "No USB controller found.")
      else:
        self.status.set("USB: %s — hold button %d to drive; button %d = stop." % (
            self.js.get_name(), self.deadman_button, self.estop_button))
    else:
      if self.js is not None:
        try:
          self.js.quit()
        except Exception:
          pass
        self.js = None
      if src == "pad":
        self.status.set("Polar pad — drag the red knob (click knob to grab). Release to stop.")
      else:
        self.status.set("Sliders — adjust Velocity %% and Angle %%.")
    self._pad_redraw()

  def _zero_sliders(self):
    self.var_vel.set(0)
    self.var_ang.set(0)

  def _stop_clicked(self):
    stop_all_motors(self.ch)
    self.status.set("Motors stopped.")

  def _on_close(self):
    try:
      self.root.unbind_all("<ButtonRelease-1>")
    except Exception:
      pass
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
    src = self.source.get()
    if src == "gamepad" and self.js is not None:
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

    if src == "pad":
      return float(self.pad_pct), float(self.pad_mag), True, False

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
        self.status.set("Driving: vel=%.0f angle%%=%.0f  [%s]" % (
            magnitude, pct_angle, self.source.get()))
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
