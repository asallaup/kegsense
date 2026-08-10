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

Sensor terminals (J1–J4) sit in a horizontal row close to the board's top
edge (y≈10, 30mm pitch), ordered FL/BR/FR/BL left-to-right (not source
order) so the diagonal pairs (SIG_POS = J1+J3, SIG_NEG = J2+J4) sit next to
each other. Unrotated (angle=0, the library's default orientation) — an
earlier version rotated each part -90° to make the bus routing trivial
(every part's pins landing on their own single x instead of sharing a y
with every other part's pins), but that was a routing convenience, not a
requirement; unrotated works too, it just needs more deliberate lane/layer
routing (see below). J5 (HX711 load-cell side) sits below the row, on the
same side — these are the noise-sensitive analog connections, kept short
and away from the digital/power section. J6 (HX711 digital side) sits with
J5; J7 (RJ11 to hub) is rotated 180° and placed flush with the board's
*bottom* edge (y=90) — moved here from the right edge. Any edge-mounted
connector belongs at the board edge as a matter of course, independent of
the case (this board had a real bug once from *not* following that rule —
J7 originally sat mid-board with no edge access at all; see git history).

Routing uses both copper layers, extensively. With J1-J4 unrotated, every
one of their 12 pins (pin1/2/3 × 4 parts) sits at the exact same y=10 —
unlike the rotated layout, where each pin *number* got a fixed y shared by
all 4 parts (turning "pin N, every part" into one trivial straight bus),
here every net needs its own dedicated lane below the row plus vertical
drops from each of its own pins down to that lane, and since the 4 nets'
pin x-positions are interleaved across the same 20-110 span, a drop for a
"deeper" net's lane inevitably passes through a "shallower" net's lane at
some point along that span. EXC_POS and EXC_NEG (each needing the full row
width) are kept on separate copper layers entirely so crossing each other
in plan view isn't a short; SIG_POS/SIG_NEG only span half the row each,
but still have to get past *both* of those, so their drops explicitly hop
layers (via) at each crossing rather than relying on a single layer
choice. J7's move to the bottom edge similarly turned its own approach
into a small routing puzzle: GND and SCK's target pads are only 1.02mm
apart, so straight verticals into either one grazed the *other's*
neighbor pad (VCC) for their whole length — fixed with an offset
approach-and-jog into each pad's own y, and DT/SCK/GND's lanes had to be
depth-ordered (matching the order of their target x's) so a deeper lane's
horizontal run doesn't cross a shallower one's drop. Each net's initial
jog off of J6 goes east (toward J7), not west first — per explicit
request — which flips *which* net needs the shallowest lane: since every
lane then extends the rest of the way east to J7 regardless of where its
own stub sits, the depth/stub-position pairing that avoids crossings
turned out to be the mirror image of the west-jog version (shallowest
lane ↔ stub furthest from J6, not closest).

GND and SCK are each a single unbroken line on one layer (B.Cu and F.Cu
respectively), no vias — J6's pads are through-hole, so a track can just
start on whichever layer it needs directly at the pad; both had a
vestigial F.Cu stub in an earlier version that wasn't actually needed.
VCC_3V3 and DT can't drop theirs, though, and this isn't a missed
simplification — checked exhaustively, not just patched around the first
conflict DRC caught: VCC's own source row at J6 sits inside DT's drop's
depth range, and DT's row sits inside VCC's, so whichever one is "in the
way" at that crossing needs to be on the other layer right there. Two
vias is the minimum for this connector, not four.

See the comments in `generate_pcb.py` for the exact reasoning behind each
routing decision — several were only found by DRC catching a real short
or clearance violation, not worked out by eye in advance.

**Note on KiCad footprint rotation**: got this wrong once already — KiCad's
`(at x y angle)` rotation is the opposite sign of the standard math
convention (confirmed empirically by checking DRC's reported pad
coordinates against a hand-rotated prediction, the same way the schematic's
Y-axis quirk was caught earlier). J7 uses `angle=180` to point its cable
face toward +Y (the bottom edge); don't assume a given angle achieves a
given direction without checking actual reported pad/courtyard positions
first — that's what caught this, not reasoning from the formula alone.

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
- **Front wall (y=0) has an open cutout** spanning the J1–J4 sensor
  terminal row, for the 4 sensor cables to exit (board-local y=0 is the
  board's own top edge, which sits against the case's front wall).
- **Back wall (y=outer_h) has a cutout matching J7's position** — moved
  here from a right-wall cutout when J7 moved from the board's right edge
  to its bottom edge (board-local y=90, which sits against the case's
  back wall — see Physical layout above). Earlier drafts had J7 positioned
  mid-board with a cutout nowhere near it — caught by directly computing
  J7's courtyard position against the case's wall coordinates rather than
  assuming the cutout was in the right place; fixed by moving J7 to the
  board edge (any case built around a mid-board position would need an
  internal tunnel to reach the connector, which isn't good practice
  regardless of the case).
- **Base is branded, engraved (not raised)**, both lines on the right
  wall (x=outer_w — the one wall without a connector cutout, now that
  J1-J4's cutout (front) and J7's (back) both claim one): "KegSensor"
  (bold, size 5) above "Sallaup Electronics" (italic, size 2.6, smaller as
  a subtitle). Recessed 0.6mm into the 2mm wall (1.4mm remains, plenty
  strong), centered horizontally and stacked vertically in the safe
  z-band shared with the connector cutouts. See
  `case_engrave_right_preview.png` — rendered as a true 2D orthographic
  projection from the wall's own outside-viewer perspective, not a 3D
  angle shot, because that's what actually caught a real bug the first
  time this branding was added (below). Text is generated with OpenSCAD's
  `text()` primitive directly from the strings in `case.scad`, not
  hand-drawn, so there's no typo risk — but getting an engraved letter
  *oriented* correctly on a vertical wall needs real verification, not
  assuming: the original front-wall attempt read upside-down at first; a
  fix reasoned from a 3D perspective render (a 180° rotation) corrected
  the vertical flip but introduced a horizontal mirror instead, only
  caught by switching to a true top-down 2D projection. `wall_text_right()`
  — a new module, following the same front/back pattern but re-derived
  from scratch for a wall on the other axis, not assumed by analogy —
  is what's in use now that branding moved to the right wall (freed up
  once J7's cutout claimed the back wall). Derived by tracking exactly
  what each OpenSCAD transform does to a known point rather than guessing,
  then verified the same way as before (a true 2D cross-section at the
  engrave depth, from the actual outside-viewer's perspective) — correct
  on the first attempt this time, though it was checked regardless rather
  than assumed correct from the derivation alone. `wall_text_front()` and
  `wall_text_back()` are both unused now but kept in case a wall needs
  text again later.

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
- `kicad-cli pcb drc` on the fully routed board → 0 errors, 0 unconnected
  pads (only one pre-existing accepted warning remains: the
  local-footprint-override notice for J7's custom RJ14 footprint — see
  its own comment). Iterated repeatedly: the first full layout pass found
  17 real clearance/short issues from too-tight spacing; switching J7 from
  the RJ9 to the RJ14 footprint reset the J6↔J7 routing and took several
  more DRC-guided rounds to clear, since RJ14's pads are much more tightly
  packed. Moving J1-J4 to a horizontal row (see Physical layout) went
  through the same cycle: a straight diagonal tap point cut through an
  unrelated pad's copper twice before landing on the current routing, each
  time caught by DRC, not by eye. That pass also surfaced a separate
  latent bug: `generate_pcb.py`'s footprint copies kept the *library's*
  pad/graphic UUIDs verbatim, so multiple instances of the same footprint
  (J1/J3/J2/J4, all `TerminalBlock_bornier-3`) shared identical pad UUIDs
  - DRC started mislabeling which physical pad a violation was actually
  against once there were 4 copies on the board. Fixed by re-rolling every
  nested UUID per instance, not just the footprint's own top-level one.
- Un-rotating J1-J4 back to angle=0 and moving J7 to the bottom edge (a
  later request) meant redesigning essentially all of this board's
  routing again, and went through several more DRC-caught rounds: a
  diagonal from J1-J4's row to J5 cut through the SIG_POS lane;
  SIG_NEG's approach crossed straight through the J6↔J7 corridor's own
  drops; and J7's GND/SCK approaches (straight verticals into their own
  target x) each grazed the *other's* neighboring pad, since GND/SCK and
  VCC/DT sit only ~1mm apart in the tight RJ14 pad cluster. Each was a
  real `tracks_crossing`/`shorting_items`/`clearance` error, not a style
  preference — fixed with offset approach paths, layer hops, and
  depth-ordered lanes; see `generate_pcb.py`'s comments for the specifics.
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
