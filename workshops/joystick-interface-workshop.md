# Workshop: Joystick → Rover (SGVHAK_Rover)

## The easy explanation

**What the rover software does**

- It knows where each wheel sits on the robot (`config_roverchassis.json`).
- When you say “drive forward a bit and turn left a bit,” one function — **`move_velocity_radius`** in `roverchassis.py` — figures out each wheel’s speed and steer angle, then sends commands to the motor libraries (RoboClaw, LewanSoul, etc.).

**What the web pages do**

- The browser sends “knob” or slider values to Flask (`menu.py`).
- Flask converts those numbers into **velocity** + **turn radius**, then calls **`move_velocity_radius`**.

**What a joystick would do**

- Same end point: read a gamepad, turn stick position into **velocity** + **radius**, call **`move_velocity_radius`**.
- There is **no** joystick code in the repo today; you add a small program (or a background thread) that does that.

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
- [ ] **Stubs for later phases (already in repo):** `SGVHAK_Rover/control_mapping.py` (Phase 4), `scripts/joystick_drive.py` (Phase 5) — placeholders only until you implement those phases.

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
- [ ] Copy (on paper or in comments) the **radius** calculation from `drive_command` in `menu.py` from `pct_angle` (same formulas you will reuse for a stick).

**Done when:** you can explain in one sentence: “left/right on stick changes *radius*, forward/back changes *velocity*.”

---

## Phase 4 — Extract “stick → motion” into one place (recommended)

**Goal:** One function used by both Flask and the joystick driver so they never disagree.

- [ ] Add a small module, e.g. `SGVHAK_Rover/control_mapping.py`, with a pure function:

  `def polar_to_motion(pct_angle, magnitude):`  
  `→` returns `(velocity, radius)` matching today’s `drive_command` behavior (including `pct_angle == 0` → straight).

- [ ] Change **`drive_command`** in `menu.py` to call that function instead of inlining the math.
- [ ] Re-test all three drive UIs in the browser.

**Done when:** `menu.py` has no duplicated radius math; browser still works.

---

## Phase 5 — Minimal joystick process (first real joystick)

**Goal:** A standalone script on the **same machine that owns the motors** reads axes and calls **`move_velocity_radius`**.

- [ ] Choose a library (**`pygame`** is common; **`inputs`** is another). Add it to `setup.py` or document `pip install pygame` for the workshop.
- [ ] New script, e.g. `scripts/joystick_drive.py` (or `SGVHAK_Rover/joystick_drive.py`), structure:

  1. `import roverchassis` (ensure working directory / `PYTHONPATH` matches how you run Flask so configs load the same way).
  2. `chassis = roverchassis.chassis()` then **`chassis.ensureready()`** once.
  3. Init joystick; in a loop at ~10–20 Hz:
     - read left stick (or chosen axes),
     - map X/Y to `pct_angle` / `magnitude` (same ranges as the web UI, -100..100),
     - `velocity, radius = polar_to_motion(pct_angle, magnitude)`,
     - **`chassis.move_velocity_radius(velocity, radius)`**,
     - on quit or released “deadman”, send **stop** (`velocity=0`, straight radius, or call the same path the **Stop motors** route uses).

- [ ] Add **deadband** (small stick wiggle → zero) so the rover does not crawl from noise.
- [ ] Add a **deadman** (e.g. hold shoulder button or key) so motion only applies while held.

**Done when:** with **Path A** stub, running the script while Flask is **not** commanding motors still shows sensible behavior in logs or optional prints; with **Path B**, wheels move smoothly.

**Conflict rule:** Do **not** run the joystick script and the web drive at the same time unless you add explicit locking; simplest workshop rule: **only one driver at a time**.

---

## Phase 6 — Make it “workshop safe”

- [ ] **Rate limit:** do not send commands faster than ~20–50 ms; merge or drop intermediate frames.
- [ ] **E-stop:** map a button to **`wheel.poweroff()`** for all wheels (see `stop_motors` in `menu.py`) or `velocity=0` + safe steering behavior you prefer.
- [ ] **Logging:** one line per second with velocity/radius for field debugging.

**Done when:** someone else can run the script with a short README section (commands + “hold this button to enable”).

---

## Phase 7 — Pi deployment (when hardware exists)

- [ ] Copy project to Pi, install deps, verify **`flask run --host=0.0.0.0`** still works on your network.
- [ ] Run `joystick_drive.py` on the Pi with the real `config_roverchassis.json`.
- [ ] Optional: **`systemd`** unit to start the joystick script at boot (only if you want joystick *instead of* browser by default).

**Done when:** robot drives from the gamepad without opening a browser.

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
| `SGVHAK_Rover/menu.py` | Today’s HTTP → motion; later calls shared mapper |
| `SGVHAK_Rover/control_mapping.py` | **New:** shared stick/slider → `(velocity, radius)` |
| `scripts/joystick_drive.py` | **New:** pygame loop |
| `config_roboclaw.json` | `"port": "TEST"` for laptop stub |
| `config_roverchassis.json` | Wheel layout + which controller backs each wheel |
| `scripts/bootstrap_dev.sh` | Creates venv + editable install (Phase 1) |
| `scripts/joystick_drive.py` | Stub entrypoint for Phase 5 |

---

## Success criteria (whole workshop)

1. Browser drive still works after refactor.  
2. `joystick_drive.py` drives the same `chassis` API with a USB gamepad.  
3. Deadman + deadband + rate limit documented.  
4. On Pi, same script works with real hardware configs.
