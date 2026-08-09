# Load cell holder — derived design

`load_cell_holder.scad` is a same-dimension recreation of a third-party
snap-fit load cell holder from Printables:
https://www.printables.com/model/157473-load-cell-holder

It holds one of the KegSensor half-bridge load cells at one end (snap-fit
into the central pocket) while the other two holes bolt the holder down
to a base plate. Four of these, one per corner, is the mounting scheme
for a keg platform — see `../hub-wiring.md` for the sensor wiring side of
that (not built yet; this holder is the first piece of the mechanical
platform, done in isolation per current scope).

## Why OpenSCAD instead of just using the original STL

Consistent with how the rest of this project's parts are built
(`case.scad`, `generate_pcb.py`) — editable source, not an opaque
downloaded file, so dimensions can be adjusted later (e.g. once the
actual platform plates get designed and need to match up with these
holders) without needing to reverse-engineer it again.

## How it was derived

The original's dimensions were **measured directly from the downloaded
STL**, not eyeballed or guessed:
- 2D cross-section slices through the mesh at specific heights (exact
  polygon boundaries, not approximated from a rendered image)
- Point-cloud analysis for hole positions/diameters and material
  thickness at various heights

Key measured values (see comments in `load_cell_holder.scad` for the
full set): overall envelope 76.08 × 46.05 × 8.01mm, two M4-clearance
bolt holes (r=2.05mm) 59.05mm apart, a 26.03×26.03mm central pocket
opening, ~6mm base thickness with a ~2mm raised lip around the pocket,
and a ~5.8mm-wide split-seam slit at the pocket's top edge (the flex
feature that lets the load cell snap in).

This is a **faithful functional recreation** (same envelope, hole
positions/sizes, pocket opening, general thickness) — not a
byte-identical mesh clone. Fine fillet/rounding details are approximated
with simpler geometry.

## Validation performed

- `openscad` reports the generated STL as `Simple: yes` (valid, manifold,
  watertight — same check used throughout this project).
- Bounding box compared directly against the original: 76.08×46.04×8.00mm
  derived vs. 76.076×46.046×8.008mm original — matches to within
  measurement/rounding error.
- Volume compared: 12646mm³ derived vs. 12974mm³ original (~2.5% smaller,
  expected from the approximated fillets, not a structural difference).
- **A first attempt had a real bug**: the ear tabs appeared visually
  disconnected from the central collar in a 3D perspective render. Rather
  than trusting that render, it was checked against the actual 2D
  polygon outline (`openscad ... -o outline.svg`, confirmed a single
  closed contour — i.e. actually one connected shape) and a true
  top-down orthographic projection colored by height (see
  `load_cell_holder_validation.png`) — both confirmed the geometry was
  fine and the "gap" was a rendering artifact in the perspective-view
  script (matplotlib doesn't depth-sort concave 3D shapes well), not a
  real defect. The ear/collar overlap was still widened afterward as a
  robustness margin regardless. `load_cell_holder_validation.png` is the
  final side-by-side (original vs. derived) top-down comparison used to
  confirm the match — same figure, both parts now line up on bolt hole
  positions, pocket opening, raised lip, and seam slit.

## Known limitation

The original file (`load_cell_holder_reference.stl`, used locally for
comparison during derivation) is **not included in this repo** — it's a
third-party download with unspecified license terms, not ours to
redistribute. Get it from the Printables link above if you want to
re-run the comparison yourself; `.gitignore` excludes it by that
filename.
