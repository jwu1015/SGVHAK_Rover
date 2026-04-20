#!/usr/bin/env python3
"""Quick sanity check for polar_to_motion (no hardware, no Flask)."""
from __future__ import print_function

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
  sys.path.insert(0, ROOT)

from SGVHAK_Rover import control_mapping


class _FakeChassis(object):
  minRadius = 17.75
  maxRadius = 250.0


def main():
  c = _FakeChassis()
  v, r = control_mapping.polar_to_motion(c, 0, 50)
  assert v == 50 and r == float("inf"), (v, r)

  v, r = control_mapping.polar_to_motion(c, 100, -30)
  assert v == -30 and abs(r - c.minRadius) < 1e-6, (v, r)

  v, r = control_mapping.polar_to_motion(c, -100, 10)
  assert v == 10 and abs(r + c.minRadius) < 1e-6, (v, r)

  v, r = control_mapping.polar_to_motion(c, 50, 0)
  assert v == 0 and r != float("inf"), (v, r)

  print("control_mapping.polar_to_motion: OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
