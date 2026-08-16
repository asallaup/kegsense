# KegSensor — Implementation Plan

Part of **Sallaup KegSense**. Weight measurement is the foundational
feature of the whole system — without it, KegDisplay/KegStation/KegTag
have nothing to show. KegSensor is the furthest-along module (PCB
routed, DRC-clean, fab-ready gerbers already exported, see
[`README.md`](README.md)) but **nothing has been built or tested
against real hardware yet**. This plan gets from "designed" to
"validated, measuring a real keg" — one unit first, not all 5 at once,
so the two known hardware assumptions get confirmed before committing
to 5x the cost.

## Phase 1 — Procure for one unit first

- 1× KegSensor PCB (order qty **1**, not 5, from
  `KegSensor_RevA_gerbers.zip`)
- 1× HX711 breakout module
- 4× half-bridge load cells (one keg's worth — FL/FR/BR/BL)
- Screw terminals / headers / RJ14 jack per the Connectors table in
  `README.md`
- 1× RJ14 cable
- 4× prints of `load-cell-platform/load_cell_holder.scad` (already
  designed) — a base plate to bolt them to is **not** designed yet, see
  Phase 5

## Phase 2 — Resolve the two known assumptions before trusting the board

See "Known assumptions to confirm against real hardware" in
`README.md`:
- Check the actual HX711 module's silkscreen against
  `generate_schematic.py`'s assumed J6 pin order (GND/DT/SCK/VCC) — fix
  and regenerate if different
- Wire per the load-cell kit's own included diagram, note which
  physical corner is which — SIG_POS/SIG_NEG pairing (J1+J3 vs J2+J4)
  depends on this; fix the pairing in `generate_schematic.py` if the
  reading comes out inverted or dead-flat

## Phase 3 — Bench-test the bare board before mounting anything

- Continuity checks on this one board (bus connections correct, no
  unwanted shorts) — same spirit as KegHub's own bench-test checklist,
  adapted for a single KegSensor board
- Solder one load cell on, confirm the HX711 output changes sensibly
  under hand pressure — no real weight math yet, just "is this alive"

## Phase 4 — Minimal read-out software (throwaway, not the real daemon)

- A quick script (existing Python HX711 library, or a small bit-bang
  test) on a spare Pi/dev board — just enough to print raw ADC values
  changing under load
- **Not** KegStation's real `pigpio` C daemon (see
  [`../kegstation/README.md`](../kegstation/README.md)) — that's a
  later, separate effort. This is the earliest point "can we measure
  weight at all" gets a real yes/no answer.

## Phase 5 — Full 4-load-cell keg platform + calibration

- Design the base plate the 4 printed holders bolt to (not designed
  yet — only the individual holder is)
- Mount all 4 load cells, wire the complete diagonal pairing, get a
  real combined weight reading
- Validate tare + a known calibration weight → sane, repeatable grams
  reading. This proves the *math* `kegcal` will later formalize (see
  KegStation's README) — the calibration tool itself isn't needed yet,
  just confirmation the sensor+HX711 combination produces trustworthy
  numbers.

## Phase 6 — Only after Phase 5 passes: fab the remaining 4 boards

- Fix `generate_schematic.py` / `generate_pcb.py` for whatever Phase 2
  found, regenerate gerbers
- Order 4 more boards
- Assemble, repeat Phase 3's bench checks per board

## Phase 7 — Multi-keg bus validation (bleeds into KegHub/KegStation)

- Build KegHub ([`../keghub/README.md`](../keghub/README.md)), wire all
  5 KegSensor modules to it
- Confirm the shared-SCK / independent-DT bus reads all 5 modules
  cleanly at once
- This is where scope stops being "just KegSensor" and starts needing
  KegStation's real daemon — see
  [`../kegstation/README.md`](../kegstation/README.md) for that side.
