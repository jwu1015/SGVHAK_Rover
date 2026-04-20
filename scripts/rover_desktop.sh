#!/usr/bin/env bash
# Native desktop UI (Tkinter): sliders + optional USB gamepad. No Flask.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
[[ -f venv/bin/activate ]] && source venv/bin/activate
exec python -m SGVHAK_Rover.desktop_app
