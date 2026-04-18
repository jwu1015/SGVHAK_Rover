#!/usr/bin/env bash
# One-shot dev environment for Phase 1 (see workshops/joystick-interface-workshop.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate
python -m pip install -U pip
pip install -e .

echo ""
echo "Bootstrap complete. From this directory (repo root) run:"
echo "  source venv/bin/activate"
echo "  export FLASK_APP=SGVHAK_Rover"
echo "  flask run"
echo "Then open http://127.0.0.1:5000"
