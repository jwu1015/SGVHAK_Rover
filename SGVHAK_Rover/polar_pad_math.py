"""
Polar control pad math — matches static/drive.js Knob.moveTo (ui_angle, maxRadius).

Coordinates: x right, y down, origin at pad center (same as browser canvas).
Returns knob position for drawing and (pct_angle, magnitude) for the rover API.
"""
from __future__ import print_function

import math


def polar_pad_compute(x, y, ui_angle, max_radius):
  """
  Args:
    x, y: pointer position relative to pad center (pixels).
    ui_angle: max left/right wedge in degrees (drive.html uses 70).
    max_radius: max stick deflection in pixels.

  Returns:
    (knob_x, knob_y, magnitude, pct_angle) — same semantics as web Knob.
  """
  hypot = math.hypot(x, y)
  if hypot > max_radius:
    hypot = max_radius

  if hypot < 1e-6:
    return 0, 0, 0, 0

  if x == 0:
    calc_angle = 180.0 if y > 0 else 0.0
  else:
    arctan = math.degrees(math.atan(y / x))
    if x > 0:
      calc_angle = arctan + 90.0
    else:
      calc_angle = arctan - 90.0

  knob_x = 0.0
  knob_y = 0.0

  if calc_angle == 0:
    knob_x = 0.0
    knob_y = -hypot
  elif calc_angle == 180:
    knob_x = 0.0
    knob_y = hypot
  else:
    if calc_angle > ui_angle and calc_angle <= 90:
      calc_angle = float(ui_angle)
    elif calc_angle < -ui_angle and calc_angle > -90:
      calc_angle = float(-ui_angle)
    elif calc_angle < -90 and calc_angle > ui_angle - 180:
      calc_angle = float(ui_angle - 180)
    elif calc_angle > 90 and calc_angle < 180 - ui_angle:
      calc_angle = float(180 - ui_angle)
    rad = math.radians(calc_angle)
    knob_x = round(math.sin(rad) * hypot)
    knob_y = round(math.cos(rad) * -hypot)

  calc_a = calc_angle
  if calc_a >= -90 and calc_a <= 90:
    magnitude = int(round(100.0 * hypot / max_radius))
    pct_angle = int(round(100.0 * calc_a / ui_angle))
  else:
    if calc_a > 90:
      calc_adj = 180.0 - calc_a
    else:
      calc_adj = -180.0 - calc_a
    magnitude = int(round(-100.0 * hypot / max_radius))
    pct_angle = int(round(100.0 * calc_adj / ui_angle))

  magnitude = max(-100, min(100, magnitude))
  pct_angle = max(-100, min(100, pct_angle))
  return int(knob_x), int(knob_y), magnitude, pct_angle
