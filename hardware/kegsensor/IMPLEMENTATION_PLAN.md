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

## Phase 1 — Procure for one unit first, on perfboard, not the custom PCB yet

**Prototype on generic perfboard/stripboard first, not the custom
KegSensor PCB.** No fab turnaround, no fab cost, and no risk of paying
to fab a board around an assumption (J6 pin order, SIG_POS/SIG_NEG
pairing — see Phase 2) that turns out wrong. The custom PCB gets
ordered later, in Phase 6, once both the wiring assumptions *and* the
3.5mm-terminal-block layout change are validated.

- 1× generic perfboard/stripboard + hookup wire
- 1× HX711 breakout module
- 4× half-bridge load cells (one keg's worth — FL/FR/BR/BL)
- Screw terminals / headers / RJ14 jack per the Connectors table in
  `README.md` (same parts either way — perfboard or the eventual custom
  PCB, just hand-wired for now instead of routed copper)
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

## Phase 3 — Bench-test the perfboard wiring before mounting anything

- Continuity checks on the hand-wired perfboard (bus connections
  correct, no unwanted shorts) — same spirit as KegHub's own
  bench-test checklist, adapted for a single hand-wired KegSensor
  prototype
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

## Phase 6 — Only after Phase 5 passes: fab the real PCB, all 5 at once

The perfboard prototype (Phase 1-5) replaces the old "fab 1, validate,
fab 4 more" split — by the time Phase 5 passes, both the wiring
assumptions (Phase 2) and the board layout (3.5mm terminal blocks,
smaller footprint than the original 5.08mm design) are already
validated on perfboard, so there's no more reason to hold back on
ordering all 5 real boards at once.

- Fix `generate_schematic.py` / `generate_pcb.py` for whatever Phase 2
  found, and for the 3.5mm terminal block footprint (see design-change
  note in `README.md`), regenerate gerbers
- DRC/ERC clean check, order all 5 boards
- Assemble, repeat Phase 3's bench checks per board

## Phase 7 — Multi-keg bus validation (bleeds into KegHub/KegStation)

- Build KegHub ([`../keghub/README.md`](../keghub/README.md)), wire all
  5 KegSensor modules to it
- Confirm the shared-SCK / independent-DT bus reads all 5 modules
  cleanly at once
- This is where scope stops being "just KegSensor" and starts needing
  KegStation's real daemon — see
  [`../kegstation/README.md`](../kegstation/README.md) for that side.
