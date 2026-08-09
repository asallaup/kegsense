# KegSensor — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegSensor** is the per-keg carrier board: hosts the HX711 breakout
module, terminates the 4 half-bridge sensor leads (bussed/paired per
`wiring.md`), and exits to the in-keezer hub over RJ11. One board
per keg.

KiCad 9 project. Both schematic and PCB (footprints placed, fully routed,
2-layer) are done and validated (see Validation below).

## Fabrication

**Send `KegSensor_RevA_gerbers.zip` to the PCB manufacturer.** That's the
complete, standard deliverable — a fab house doesn't need the `.kicad_pcb`
file itself (though most modern ones, e.g. JLCPCB/PCBWay, also accept it
directly if you'd rather skip the export step). It contains, generated via
`kicad-cli pcb export gerbers`/`export drill`:

| File | Contents |
|------|----------|
| `*-F_Cu.gtl` / `*-B_Cu.gbl` | Copper layers (top/bottom) |
| `*-F_Mask.gts` / `*-B_Mask.gbs` | Soldermask |
| `*-F_Silkscreen.gto` / `*-B_Silkscreen.gbo` | Silkscreen (incl. the KegSensor/Rev A branding) |
| `*-F_Paste.gtp` / `*-B_Paste.gbp` | Solder paste stencil (only matters if you're getting a stencil cut too) |
| `*-Edge_Cuts.gm1` | Board outline |
| `*-job.gbrjob` | Gerber job file (metadata some fabs use to auto-detect stackup) |
| `*-PTH.drl` / `*-NPTH.drl` | Drill files — plated (component holes) and non-plated (J7's 2 mounting bosses) separately |

The individual files are also in `fab/` (not zipped) if a fab's upload
tool wants them one at a time rather than as an archive, along with
`*-drl_map.pdf` drill maps (human-readable cross-reference of hole
sizes/positions — not needed by the fab, just useful if you want to
sanity-check the drill file yourself).

**Order quantity**: 5 (one per keg) — check the fab's pricing breaks
first, since many charge nearly the same for 5 as for 10.

**Before ordering**: resolve the two items under Known assumptions below
(J6 pin order, SIG_POS/SIG_NEG diagonal pairing) if you haven't already —
both require rerouting, which is easy to do before fabrication and
annoying after.

Regenerate the fab package after any board changes:
```
kicad-cli pcb export gerbers --layers "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" -o fab/ keg_sensor_module.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-separate-th --excellon-units mm --generate-map --map-format pdf -o fab/ keg_sensor_module.kicad_pcb
```

## Files

- `keg_sensor_module.kicad_pro` — project file, open this in KiCad
- `keg_sensor_module.kicad_sch` — schematic (see `keg_sensor_module.pdf` for
  a quick look without opening KiCad)
- `keg_sensor_module.kicad_pcb` — routed board, 155×90mm outline, 4× M3
  clearance mounting holes at the corners (6,6)/(150,6)/(6,84)/(150,84)
  board-local (see `keg_sensor_module_top.png` / `_bottom.png` for a quick
  look, or `keg_sensor_module_3d.png` for an isometric render with real
  component shapes)
- `case.scad`, `case_base.stl`, `case_lid.stl` — 3D-printable enclosure,
  see Case below
- `generate_schematic.py` / `generate_pcb.py` — the scripts that generated
  the two files above. If a pin-order assumption turns out wrong once you
  have the real hardware in hand (see Known assumptions below), fix it in
  the script and rerun rather than hand-editing the `.kicad_sch`/`.kicad_pcb`
  text. Requires `pip install sexpdata` and a local KiCad 9 install (the
  scripts read symbol/footprint definitions straight out of
  `/Applications/KiCad/KiCad.app/Contents/SharedSupport/`).
  **If you have this project open in KiCad while regenerating, close and
  reopen the PCB editor afterward** — the scripts overwrite the file on
  disk directly, which KiCad won't pick up in an already-open editor.

## Connectors

| Ref | Part | Pins |
|-----|------|------|
| J1 | Screw terminal, sensor "FL" corner | 1=E+ 2=E- 3=Signal |
| J2 | Screw terminal, sensor "FR" corner | 1=E+ 2=E- 3=Signal |
| J3 | Screw terminal, sensor "BR" corner | 1=E+ 2=E- 3=Signal |
| J4 | Screw terminal, sensor "BL" corner | 1=E+ 2=E- 3=Signal |
| J5 | Female header, HX711 load-cell side | 1=E+ 2=E- 3=A+ 4=A- |
| J6 | Female header, HX711 digital/power side | 1=GND 2=DT 3=SCK 4=VCC |
| J7 | RJ11 jack to hub (RJ14 6P4C) | 1=GND 2=VCC 3=SCK 4=DT |

Nets: `EXC_POS`/`EXC_NEG` bus J1–J4 pin1/pin2 into J5; `SIG_POS` ties
J1+J3's signal leads (diagonal) into J5.A+, `SIG_NEG` ties J2+J4's into
J5.A-; J6↔J7 pass GND/DT/SCK/VCC straight through to the hub cable.

## Known assumptions to confirm against real hardware

- **J6 pin order (GND,DT,SCK,VCC)** is a common layout for these HX711
  breakouts but varies by manufacturer — check your module's silkscreen
  before soldering the header, fix in `generate_schematic.py` if different.
- **Diagonal pairing (J1+J3→SIG_POS, J2+J4→SIG_NEG)** depends on which
  corner each sensor physically sits at and its mounting orientation —
  follow the kit's included wiring diagram; if the reading comes out
  inverted or dead-flat, swap the SIG_POS/SIG_NEG pairing.
- **J7 uses KiCad's stock RJ14 (Connfly DS1133-S4) footprint** — a genuine
  6P4C connector (6-position body, 4 contacts), which is mechanically what
  "RJ11" means in practice for a 4-wire line cord (RJ9, used in an earlier
  draft of this board, is a different 4P4C body meant for phone handset
  cords, not line cords — swapped out after review). Still worth checking
  the exact part you buy against this footprint's dimensions before
  ordering the board, since real-world RJ11 jacks vary in body/pin
  spacing between manufacturers.

## Physical layout

Sensor terminals (J1–J4) are placed FL/BR/FR/BL top-to-bottom (not source
order) so the diagonal pairs (SIG_POS = J1+J3, SIG_NEG = J2+J4) sit next to
each other. J5 (HX711 load-cell side) sits close by on the same side —
these are the noise-sensitive analog connections, kept short and away from
the digital/power section. J6 (HX711 digital side) sits with J5; J7 (RJ11
to hub) is rotated -90° and placed flush with the board's right edge
(x=155) — it was originally placed mid-board with no edge access at all
(a case built around that position would have made the connector
unreachable from outside — caught and fixed; see git history), and any
edge-mounted connector belongs at the board edge as a matter of course,
independent of the case.

Routing uses both copper layers: the analog bus (EXC_POS/EXC_NEG spanning
all 4 sensors, plus the SIG_POS/SIG_NEG diagonal pairs) runs on F.Cu with
short B.Cu jogs into J5. The J6↔J7 digital/power nets were the fiddliest
part of this board — RJ14's 4 pads are packed into roughly 3×2.5mm, so
GND/SCK/DT/VCC needed carefully routed detours (a couple of vias) to avoid
grazing each other's pads at that pitch, made harder by J7 sitting right at
the board edge; see the comments in `generate_pcb.py` for the reasoning
behind each one if you need to adjust it once you swap in your actual RJ11
part's footprint.

**Note on KiCad footprint rotation**: got this wrong once already — KiCad's
`(at x y angle)` rotation is the opposite sign of the standard math
convention (confirmed empirically by checking DRC's reported pad
coordinates against a hand-rotated prediction, the same way the schematic's
Y-axis quirk was caught earlier). J7 uses `angle=-90` to point its cable
face toward +X; don't assume `+90` does that without checking actual
reported pad positions first.

## Next steps

1. Confirm the two assumptions above against your actual HX711 modules and
   kit wiring diagram; adjust and rerun `generate_schematic.py` (and
   `generate_pcb.py`, since its net assignments mirror the schematic's) if
   either turns out different.
2. Once you've bought the actual RJ11 jack, double-check its footprint
   against RJ14 (Connfly DS1133-S4) — if the pad spacing/count differs,
   swap it in `generate_pcb.py` and re-route just that connector's traces.
3. Add a ground pour on the analog section if you want extra noise
   margin (not done here — the board routes clean without one, but it's a
   cheap improvement for a load-cell signal).
4. Order 5 (one per keg).

## Case

`case.scad` is a parametric OpenSCAD design: an open-top base plus a
separate flat lid, screwed together at 4 corner posts (M3 self-tapping,
2.5mm pilot holes) — see `case_base_preview.png` / `case_base_preview_2.png`
/ `case_lid_preview.png` for renders.

- Sized around the board's actual footprint (155×90×1.6mm) with a 3mm gap
  to the inner walls and 2mm walls, so it should print fine on a standard
  FDM printer with no supports needed (lid is flat, base has no overhangs
  beyond straight vertical walls).
- The board sits on 4 short standoff posts (5mm, at the PCB's own mounting
  holes) held down by M3 screws from above; the lid attaches separately at
  the box's 4 corners, also M3.
- Component clearance above the board is a flat 15mm assumption (covers
  the tallest part here, the RJ14 jack, with margin) — I don't have exact
  height dimensions for any of these parts from datasheets, so treat this
  as a reasonable guess, not a verified fit. If a first print is too
  cramped, bump `component_clear` in `case.scad` and reprint just the base.
- **Left wall has an open cutout** spanning the J1–J4 sensor terminal row,
  for the 4 sensor cables to exit.
- **Right wall has a cutout matching J7's position** (board-local y=26-47,
  the right wall since J7 sits flush with the board edge there — see
  Physical layout above). Earlier drafts had J7 positioned mid-board with
  a *top*-wall cutout nowhere near it — caught by directly computing J7's
  courtyard position against the case's wall coordinates rather than
  assuming the cutout I'd already built was in the right place. Fixed by
  moving J7 to the board edge (the correct fix — any case built around the
  original position would need an internal tunnel to reach a mid-board
  connector, which isn't good practice regardless of the case).
- **Base is branded, engraved (not raised)**, both lines on the front
  wall (the only wall without a connector cutout): "KegSensor" (bold,
  size 5) above "Sallaup Electronics" (italic, size 2.6, smaller as a
  subtitle). Recessed 0.6mm into the 2mm wall (1.4mm remains, plenty
  strong), centered horizontally and stacked vertically in the safe
  z-band shared with the connector cutouts. See
  `case_engrave_front_preview.png` — rendered as a true 2D orthographic
  projection from the wall's own outside-viewer perspective, not a 3D
  angle shot, because that's what actually caught a real bug (below).
  Text is generated with OpenSCAD's `text()` primitive directly from the
  strings in `case.scad`, not hand-drawn, so there's no typo risk — but
  getting an engraved letter *oriented* correctly on a vertical wall
  needed two rounds of actually rendering and checking, not assuming: an
  earlier attempt (briefly split across front and back walls) read
  upside-down at first; the fix that came from reasoning about a 3D
  perspective render (a 180° rotation) turned out to correct the vertical
  flip but introduce a horizontal mirror instead, only caught by
  switching to a true top-down 2D projection. `wall_text_back()` is still
  in `case.scad`, unused, in case a wall ever carries text again — it
  needs a *different* fix than the front wall for a real reason, not
  just a different wrong guess: a viewer standing behind the box faces
  the opposite direction, so their own left/right is reversed relative to
  the box's coordinate frame even when the raw geometry isn't mirrored.

Regenerate with `./generate_case.sh` after editing `case.scad` (needs
OpenSCAD: `brew install --cask openscad`; this cask fails macOS Gatekeeper,
so also run `xattr -dr com.apple.quarantine "/Applications/OpenSCAD-2021.01.app"`
once after installing). Print at 0.2mm layers, 3+ perimeters, 20%+ infill;
PETG or ABS recommended over PLA since this lives inside a keezer at
fridge/freezer temperature and PLA gets brittle cold.

## Validation performed

- `kicad-cli sch erc` → 0 errors, 0 warnings
- `kicad-cli sch export netlist` → all 8 nets manually checked against the
  intended design (see table above)
- `kicad-cli sch export pdf` → visually reviewed, no overlapping labels or
  stray connections
- `kicad-cli pcb drc` on the fully routed board → 0 violations, 0
  unconnected pads (iterated repeatedly: the first full layout pass found
  17 real clearance/short issues from too-tight spacing; switching J7 from
  the RJ9 to the RJ14 footprint reset the J6↔J7 routing and took several
  more DRC-guided rounds to clear, since RJ14's pads are much more tightly
  packed)
- `kicad-cli pcb render` → top and bottom copper renders visually reviewed
  for sane, non-overlapping routing
- Case: OpenSCAD's CGAL export reports both `case_base.stl` and
  `case_lid.stl` as `Simple: yes` (valid, manifold, watertight solids —
  the check that predicts whether a slicer will handle a model cleanly).
  OpenSCAD's own GUI preview render didn't work headlessly in this
  environment (Gatekeeper/OpenGL context issue), so I rendered the actual
  exported STLs with a separate tool (matplotlib) from multiple angles
  and reviewed them for the checks that matter here: box walls intact
  where expected, both cutouts present at plausible positions, and the
  two post types (corner lid-posts vs. PCB standoffs) landing at distinct,
  non-colliding locations.
- J7-reachability fix: computed J7's courtyard bounding box in case-outer
  coordinates directly (not eyeballed) and checked it against the right
  wall cutout's coordinates before re-rendering, then re-rendered the
  updated STL and visually confirmed an actual opening lines up with the
  connector from two angles.
- Wall engraving: `case_base.stl` still reports `Simple: yes` after the
  text cutouts. Orientation specifically verified with true 2D orthographic
  projections of each wall (not 3D perspective renders, which is what
  produced a wrong first read) from that wall's actual outside-viewer
  angle — caught and fixed a vertical-flip bug and a horizontal-mirror
  bug this way before calling it done (see Case section above for the
  detail).
