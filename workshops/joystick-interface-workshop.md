# Workshop: Joystick → Rover (SGVHAK_Rover)

## Status on this branch

Software path through **shared mapping** and **USB gamepad** is implemented:

- `SGVHAK_Rover/control_mapping.py` — `polar_to_motion(chassis, pct_angle, magnitude)`
- `menu.py` — `drive_command` calls that helper (same math as browser pads)
- `scripts/joystick_drive.py` — pygame loop, deadband, deadman, E-stop, rate limit
- `SGVHAK_Rover/desktop_app.py` — Tkinter window: polar pad + sliders + optional gamepad (no Flask / no browser)
- `SGVHAK_Rover/polar_pad_math.py` — same polar math as `static/drive.js` Knob
- `scripts/rover_desktop.sh` — launcher for the desktop app
- `scripts/verify_control_mapping.py` — quick math sanity check (no hardware)
- `setup.py` — optional extra: `pip install -e ".[joystick]"` (pulls in pygame)
- `CONNECT_ROVER.txt` — what to do when you plug in the real rover

**Next real step:** follow `CONNECT_ROVER.txt` (wiring, serial port, Sawppy config, drive).

---

## The easy explanation

**What the rover software does**

- It knows where each wheel sits on the robot (`config_roverchassis.json`).
- When you say “drive forward a bit and turn left a bit,” one function — **`move_velocity_radius`** in `roverchassis.py` — figures out each wheel’s speed and steer angle, then sends commands to the motor libraries (RoboClaw, LewanSoul, etc.).

**What the web pages do**

- The browser sends “knob” or slider values to Flask (`menu.py`).
- Flask converts those numbers into **velocity** + **turn radius**, then calls **`move_velocity_radius`**.

**What the USB gamepad script does**

- Same end point as the browser: read sticks, convert to **velocity** + **radius**, call **`move_velocity_radius`** via `control_mapping.polar_to_motion`.
- Implemented as **`scripts/joystick_drive.py`** (run on the Pi; stop Flask first if you use the web UI instead).

**What runs where**

- **On the robot computer** (usually a Pi): the code that talks to motors must run *there*, because USB/serial/I2C to controllers is on that machine.
- Your laptop is only for writing/testing until the Pi is attached.

---

## How to use this workshop

- Complete tasks **in order** when possible; later tasks assume earlier ones.
- Check off `[ ]` → `[x]` as you finish.
- Estimated time is rough; skip deep dives until the path works end-to-end.

---

## Phase 0 — Pick your path

- [ ] **Path A — Laptop only (no Pi, no motors):** use default `config_roboclaw.json` with `"port": "TEST"` so RoboClaw uses the **stub** (fake hardware). Good for UI + logic.
- [ ] **Path B — Pi + real hardware:** use your real `config_roverchassis.json` + motor configs when the robot is available.

---

## Phase 1 — Run the stock web UI

**Goal:** Prove Flask + chassis + stub work from the repo root.

- [ ] **Environment:** from repo root, run **`./scripts/bootstrap_dev.sh`** (creates `venv/`, upgrades pip, `pip install -e .`). Or do the same steps manually.
- [ ] **Run server:** `source venv/bin/activate`, `export FLASK_APP=SGVHAK_Rover`, **`flask run`** from the **repo root** (so `config_*.json` loads). Open `http://127.0.0.1:5000/`.
- [ ] **Smoke test in browser:** open `/`, try **Polar** and **Cartesian** pads, open **Chassis configuration** and confirm wheel numbers change when you move controls.
- [ ] **Read the code path:** in `menu.py`, find route **`drive_command`**: note `pct_angle`, `magnitude`, and **`chassis.move_velocity_radius`**.
- [ ] **Optional:** run `python scripts/verify_control_mapping.py` (checks shared math).
- [ ] **Optional:** `pip install -e ".[joystick]"` then `python scripts/joystick_drive.py --list` (needs a USB controller plugged in).

**Done when:** you can drive in the browser and see chassis status update (stub is fine).

---

## Phase 2 — Python 3 on your dev machine (optional but common)

**Goal:** Run cleanly on Python 3 (this repo may already satisfy these on your branch).

- [ ] If `flask run` fails with **`iteritems`**, replace dict **`.iteritems()`** with **`.items()`** in `menu.py` and in Jinja templates (e.g. `input_voltage.html`).
- [ ] If motor init logs **`StandardError`**, use **`Exception`** in `except` clauses (see `roverchassis.py` motor controller setup).
- [ ] If imports fail with **`No module named 'roverchassis'`**, ensure in-package imports use **`from . import …`** under `SGVHAK_Rover/` (see `menu.py`, `roverchassis.py`, `*_wrapper.py`).
- [ ] Re-run Phase 1 smoke test.

**Done when:** Flask runs on the Python version you actually use day to day.

---

## Phase 3 — Understand the control numbers

**Goal:** Be able to mimic the browser in code.

- [ ] Read **`move_velocity_radius`** in `roverchassis.py`: note **velocity** range **±100** and what **radius** means (`minRadius`, `maxRadius`, straight = infinity).
- [ ] Open **`control_mapping.polar_to_motion`** — that is the same radius math the browser and gamepad both use.

**Done when:** you can explain in one sentence: “left/right on stick changes *radius*, forward/back changes *velocity*.”

---

## Phase 4 — Shared mapping (DONE in repo — verify)

**Goal:** One function used by both Flask and the joystick driver.

- [x] Module `SGVHAK_Rover/control_mapping.py` with **`polar_to_motion(chassis, pct_angle, magnitude)`**.
- [x] **`drive_command`** in `menu.py` calls that helper.
- [ ] Re-test Polar, Cartesian, and Angle/Velocity drive pages in the browser.

**Done when:** `python scripts/verify_control_mapping.py` passes and browser driving still feels normal.

---

## Phase 5 — USB gamepad (DONE in repo — verify on hardware)

**Goal:** `scripts/joystick_drive.py` on the Pi reads pygame axes and calls **`move_velocity_radius`**.

- [x] **`pygame`** optional extra in `setup.py` (`pip install -e ".[joystick]"`).
- [x] Deadband, deadman (default hold button 4), E-stop (default button 1), rate limit (~20 Hz).
- [ ] On the Pi with a real controller: `python scripts/joystick_drive.py --list` then run without `--list`.

**Done when:** wheels follow sticks on the bench; E-stop always cuts power.

**Conflict rule:** Do **not** run the joystick script and the web drive at the same time; **only one driver at a time**.

---

## Phase 6 — Optional polish

- [x] Basic rate limit and E-stop are in `joystick_drive.py`.
- [ ] **Logging:** optional print of velocity/radius once per second for field debugging.
- [ ] **`systemd`** unit to start Flask or joystick at boot (team-specific).

---

## Phase 7 — Pi deployment (when hardware exists)

- [ ] Copy project to Pi, then **`bash scripts/pi_install_rover.sh`** (venv + package + pygame).
- [ ] Follow **`CONNECT_ROVER.txt`** (Sawppy config script, serial port, one drive mode).
- [ ] Verify **`flask run --host=0.0.0.0`** on your network, or gamepad-only with **`python scripts/joystick_drive.py`**.
- [ ] Optional: **`systemd`** unit to start Flask or the joystick script at boot.

**Done when:** robot drives from browser or gamepad on the bench, supervised.

---

## Phase 8 — Optional stretch goals

- [ ] **Merge with Flask:** background thread that reads joystick only when a `/joystick_enable` flag is true (harder; only if you need browser + stick switching).
- [ ] **HTTP API:** `POST /api/drive` with JSON `{velocity, radius}` for phone apps; same `polar_to_motion` or direct `move_velocity_radius`.
- [ ] **Unit tests:** `polar_to_motion` with fixed inputs vs current `menu.py` golden values.

---

## Quick reference — files you will touch

| File | Why |
|------|-----|
| `SGVHAK_Rover/roverchassis.py` | `move_velocity_radius`, geometry |
| `SGVHAK_Rover/menu.py` | HTTP routes; `drive_command` uses `control_mapping` |
| `SGVHAK_Rover/control_mapping.py` | Shared stick/slider → `(velocity, radius)` |
| `scripts/joystick_drive.py` | pygame gamepad loop (terminal) |
| `SGVHAK_Rover/desktop_app.py` | Tk desktop UI + optional gamepad |
| `scripts/rover_desktop.sh` | Launch desktop app from repo root |
| `CONNECT_ROVER.txt` | Hardware hookup checklist |
| `scripts/pi_install_rover.sh` | Pi/Linux venv + `pip install -e ".[joystick]"` |
| `scripts/activate_sawppy_config.sh` | Copy Sawppy `config_roverchassis.json` |
| `config_roboclaw.json` | `"port": "TEST"` for laptop stub |
| `config_roverchassis.json` | Wheel layout + which controller backs each wheel |
| `scripts/bootstrap_dev.sh` | Creates venv + editable install (Phase 1) |

---

## Success criteria (whole workshop)

1. Browser drive still works after refactor.  
2. `joystick_drive.py` drives the same `chassis` API with a USB gamepad.  
3. Deadman + deadband + rate limit documented.  
4. On Pi, same script works with real hardware configs.
