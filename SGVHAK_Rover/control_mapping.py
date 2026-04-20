"""
Shared mapping from browser / gamepad inputs to chassis motion.

Keeps Flask (drive_command) and scripts/joystick_drive.py using the same math.
"""


def polar_to_motion(chassis, pct_angle, magnitude):
  """
  Convert polar pad style inputs to (velocity, radius) for move_velocity_radius.

  Args:
    chassis: roverchassis.chassis instance (uses minRadius / maxRadius only).
    pct_angle: -100..100 steering hint; 0 = straight (infinite radius).
    magnitude: -100..100 velocity percent (same sign convention as web UI).

  Returns:
    (velocity, radius) suitable for chassis.move_velocity_radius.
  """
  pct_angle = float(pct_angle)
  magnitude = float(magnitude)

  if pct_angle == 0:
    radius = float("inf")
  elif pct_angle > 0:
    radius = chassis.minRadius + (chassis.maxRadius - chassis.minRadius) * (100 - pct_angle) / 100.0
  else:
    radius = -chassis.minRadius - (chassis.maxRadius - chassis.minRadius) * (100 + pct_angle) / 100.0

  return (magnitude, radius)
