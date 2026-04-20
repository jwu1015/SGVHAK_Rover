#!/usr/bin/env bash
# Install editable package + optional joystick extra on a Raspberry Pi (or Linux).
# Run from repo root after git clone:  bash scripts/pi_install_rover.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate
python -m pip install -U pip
pip install -e ".[joystick]"

echo ""
echo "Installed SGVHAK_Rover + pygame. Next steps:"
echo "  1) ./scripts/activate_sawppy_config.sh   (if this is a Sawppy)"
echo "  2) Edit config_lewansoul.json → connect.port (see CONNECT_ROVER.txt)"
echo "  3) Web UI:  source venv/bin/activate && export FLASK_APP=SGVHAK_Rover && flask run --host=0.0.0.0"
echo "  OR gamepad CLI:  python scripts/joystick_drive.py   (stop other drivers first)"
echo "  OR desktop app:  ./scripts/rover_desktop.sh   (Tk window; Pi needs: sudo apt install python3-tk)"
