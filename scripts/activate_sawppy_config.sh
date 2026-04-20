#!/usr/bin/env bash
# Point config_roverchassis.json at the Sawppy + LewanSoul wheel layout.
# Run once on the Pi before first drive (after backing up any custom layout).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SRC="config_roverchassis.json.sawppy"
DST="config_roverchassis.json"
if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC"
  exit 1
fi
if [[ -f "$DST" && ! -f "${DST}.pre_sawppy.bak" ]]; then
  cp "$DST" "${DST}.pre_sawppy.bak"
  echo "Backed up previous layout to ${DST}.pre_sawppy.bak"
fi
cp "$SRC" "$DST"
echo "Active chassis config is now Sawppy ($SRC → $DST)."
echo "Next: set config_lewansoul.json connect.port to your USB serial device."
