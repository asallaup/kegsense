import re, uuid, pathlib

FP_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
TEMPLATE_PCB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/EuroCard160mmX100mm/EuroCard160mmX100mm.kicad_pcb"
OUT = pathlib.Path(__file__).resolve().parent / "keg_sensor_module.kicad_pcb"

def extract_balanced(text, start_idx):
    depth = 0
    for i in range(start_idx, len(text)):
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[start_idx:i + 1]
    raise ValueError("unbalanced")

def load_footprint(lib_pretty, name):
    path = f"{FP_ROOT}/{lib_pretty}/{name}.kicad_mod"
    text = open(path).read()
    block = extract_balanced(text, text.index(f'(footprint "{name}"'))
    return block

FP_TERMINAL3 = load_footprint("TerminalBlock.pretty", "TerminalBlock_bornier-3_P5.08mm")
FP_PINSOCKET4 = load_footprint("Connector_PinSocket_2.54mm.pretty", "PinSocket_1x04_P2.54mm_Vertical")
# RJ14 = genuine 6P4C connector (6-position body, 4 contacts) - this is
# mechanically what "RJ11" means in practice for a 4-wire line cord.
# RJ9 (4P4C) is a different, smaller body used for phone handset cords,
# not line cords - swapped out after review.
FP_RJ11 = load_footprint("Connector_RJ.pretty", "RJ14_Connfly_DS1133-S4_Horizontal")

def new_uuid():
    return str(uuid.uuid4())

NET_NAMES = ["EXC_POS", "EXC_NEG", "SIG_POS", "SIG_NEG", "GND", "DT", "SCK", "VCC_3V3"]
NET_ID = {name: i + 1 for i, name in enumerate(NET_NAMES)}

def net_block():
    lines = ['\t(net 0 "")']
    for name, nid in NET_ID.items():
        lines.append(f'\t(net {nid} "{name}")')
    return "\n".join(lines)

def inject_pad_net(fp_text, pad_num, net_name):
    nid = NET_ID[net_name]
    idx = fp_text.index(f'(pad "{pad_num}"')
    pad_block = extract_balanced(fp_text, idx)
    drill_idx = pad_block.index("(drill")
    drill_end = pad_block.index(")", drill_idx) + 1
    new_pad = (pad_block[:drill_end] +
               f'\n\t\t\t(net {nid} "{net_name}")' +
               pad_block[drill_end:])
    return fp_text[:idx] + new_pad + fp_text[idx + len(pad_block):]

def instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, ref_at=None):
    text = fp_text
    for pad_num, net_name in pad_nets.items():
        text = inject_pad_net(text, pad_num, net_name)
    text = text.replace(f'(footprint "{lib_id.split(":")[1]}"',
                         f'(footprint "{lib_id}"\n\t\t(layer "F.Cu")\n\t\t(uuid "{new_uuid()}")\n\t\t(at {x} {y} {angle})\n\t\t(attr through_hole)',
                         1)
    text = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', text, count=1)
    if ref_at is not None:
        # Override the reference field's own local (at) offset - needed
        # when the library's default offset (which assumes angle=0) ends
        # up landing back on top of the footprint's own silkscreen outline
        # once rotated (KiCad rotates this offset along with everything
        # else in the footprint).
        text = re.sub(r'(\(property "Reference" "[^"]*"\s*\n\s*\(at )[^)]+(\))',
                       lambda m: f'{m.group(1)}{ref_at[0]} {ref_at[1]} {ref_at[2]}{m.group(2)}',
                       text, count=1)
    # Every nested pad/graphic uuid comes straight from the library file,
    # so multiple instances of the same footprint (e.g. J1/J3/J2/J4, all
    # TerminalBlock_bornier-3) would otherwise share identical pad UUIDs -
    # confuses DRC's item identification (it started mislabeling which
    # physical pad a violation was against once there were 4 copies).
    # Re-roll every uuid in the copy so each instance's sub-items are
    # actually unique.
    text = re.sub(r'\(uuid "[0-9a-fA-F-]+"\)', lambda m: f'(uuid "{new_uuid()}")', text)
    return text

components_out = []

def add_component(fp_text, lib_id, ref, x, y, angle, pad_nets, ref_at=None):
    components_out.append(instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, ref_at))

# J1-J4 sensor terminals: horizontal row close to the board's top edge
# (y=0), 30mm pitch, reordered physically (FL,BR,FR,BL) so diagonal pairs
# (SIG_POS/SIG_NEG) are adjacent. Unrotated (angle=0, back to the library
# default orientation) per explicit request - previously rotated -90 to
# make the bus routing trivial (see git history), but that's a routing
# convenience, not a requirement: unrotated works too, it just needs
# lane+layer weaving instead of one straight bus per pin (see the J1-J4
# routing comments below).
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J1", 20, 10, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS"})   # FL
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J3", 50, 10, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS"})   # BR
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J2", 80, 10, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_NEG"})   # FR
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J4", 110, 10, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_NEG"})   # BL

# J5: HX711 load-cell side header
add_component(FP_PINSOCKET4, "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "J5", 60, 35, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS", "4": "SIG_NEG"})

# J6: HX711 digital/power side header (placeholder spacing from J5 - see README)
add_component(FP_PINSOCKET4, "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "J6", 95, 35, 0,
              {"1": "GND", "2": "DT", "3": "SCK", "4": "VCC_3V3"})

# J7: RJ11-to-hub jack (RJ14 6P4C). Moved to the board's bottom edge
# (y=90), per explicit request - previously flush with the right edge
# (x=155). Rotated 180deg: at angle=0 the footprint's cable/plug face
# points -Y (confirmed by the same empirical method as before - reading
# back actual DRC-reported pad/courtyard coordinates, not assuming), i.e.
# toward the *top* edge; 180deg flips that to +Y, toward the bottom edge.
# y=81 (not 90) so the footprint's own shell, which extends ~9mm past its
# reference point on the cable-face side, lands flush with y=90 rather
# than poking through it - confirmed via DRC: pads land at (146,81),
# (144.98,78.46), (143.96,81), (142.94,78.46), and its two NPTH mounting
# bosses at (150.47,83.3)/(138.47,83.3), both comfortably inside the
# board (which is why 81, not some other offset, was picked here).
add_component(FP_RJ11, "Connector_RJ:RJ14_Connfly_DS1133-S4_Horizontal", "J7", 146, 81, 180,
              {"1": "GND", "2": "VCC_3V3", "3": "SCK", "4": "DT"})

tracks_out = []
vias_out = []

def track(x1, y1, x2, y2, layer, net_name):
    tracks_out.append(f'''\t(segment
\t\t(start {x1} {y1})
\t\t(end {x2} {y2})
\t\t(width 0.3)
\t\t(layer "{layer}")
\t\t(net {NET_ID[net_name]})
\t\t(uuid "{new_uuid()}")
\t)''')

silk_out = []

def silk_text(text, x, y, size, layer="F.SilkS"):
    silk_out.append(f'''\t(gr_text "{text}"
\t\t(at {x} {y} 0)
\t\t(layer "{layer}")
\t\t(uuid "{new_uuid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t\t(thickness {round(size * 0.15, 3)})
\t\t\t)
\t\t)
\t)''')

def via(x, y, net_name):
    vias_out.append(f'''\t(via
\t\t(at {x} {y})
\t\t(size 0.6)
\t\t(drill 0.3)
\t\t(layers "F.Cu" "B.Cu")
\t\t(net {NET_ID[net_name]})
\t\t(uuid "{new_uuid()}")
\t)''')

# -- J1-J4 <-> J5 bus --
# J1-J4 are unrotated (angle=0, see placement comment above), so ALL 12
# sensor-side pins - pin1/2/3 of all 4 parts - sit on the exact same
# y=10 (only x differs, both by part and by pin-within-part). Unlike the
# rotated layout (where each pin number got its own fixed y, so "pin N,
# every part" was a trivial straight bus), nothing here is a straight
# line without touching another net - every net needs its own "lane"
# below the row (a dedicated y) plus vertical drops from each of its pins
# down to that lane, and since the 4 nets' pin x's are interleaved across
# the same 20-110 span, a drop for a deeper-lane net inevitably passes
# through a shallower net's lane y at some point along that span.
# Two nets (EXC_POS/EXC_NEG) get the full row width, so they're kept on
# separate copper layers entirely (F.Cu / B.Cu) - crossing a different
# layer isn't a short. SIG_POS/SIG_NEG only span half the row each, but
# still need to get past THIRD level down past both of the above, so
# their drops explicitly hop layers (via) at each crossing rather than
# relying on a single layer choice.
EXC_POS_LANE_Y = 14
EXC_NEG_LANE_Y = 18
SIG_LANE_Y = 22

# EXC_POS (pin1: J1,J3,J2,J4 @ x=20,50,80,110,y=10) - F.Cu throughout,
# lane y=14 (shallowest - nothing above it to dodge).
for x in (20, 50, 80, 110):
    track(x, 10, x, EXC_POS_LANE_Y, "F.Cu", "EXC_POS")
track(20, EXC_POS_LANE_Y, 110, EXC_POS_LANE_Y, "F.Cu", "EXC_POS")
# Tap at x=65 (not 60, J5's own x, and not a direct diagonal) - a
# diagonal toward (60,35) swept through x=30.16-60.16 at y=22 along the
# way, cutting straight across SIG_POS's lane (below) - DRC-flagged
# tracks_crossing. x=65 sits clear of both SIG_POS's (30.16-60.16) and
# SIG_NEG's (90.16-120.16) lane spans, so the vertical here can't cross
# either; a short final horizontal at J5's own pad row (y=35) closes the
# last 5mm into the pad.
track(65, EXC_POS_LANE_Y, 65, 35, "F.Cu", "EXC_POS")
track(65, 35, 60, 35, "F.Cu", "EXC_POS")          # -> J5 pad1 (60,35)

# EXC_NEG (pin2 @ x=25.08,55.08,85.08,115.08,y=10) - B.Cu throughout, own
# lane y=18. Different layer than EXC_POS, so their drops/lanes freely
# cross in plan view without shorting.
for x in (25.08, 55.08, 85.08, 115.08):
    track(x, 10, x, EXC_NEG_LANE_Y, "B.Cu", "EXC_NEG")
track(25.08, EXC_NEG_LANE_Y, 115.08, EXC_NEG_LANE_Y, "B.Cu", "EXC_NEG")
# Final approach offset to x=63 (not 60) then a short horizontal AT
# pad2's own y=37.54 - a straight line into x=60 would pass close by
# J5's pad1 (60,35, a different net), same lesson as the previous
# rotated-layout attempt that failed DRC for exactly this reason. Stays
# on B.Cu (not F.Cu) throughout - EXC_POS's approach also passes near
# x=63-65 on its own way into J5, and B.Cu is otherwise clear here.
track(63, EXC_NEG_LANE_Y, 63, 37.54, "B.Cu", "EXC_NEG")
track(63, 37.54, 60, 37.54, "B.Cu", "EXC_NEG")    # -> J5 pad2 (60,37.54)

# SIG_POS (pin3, J1+J3 only @ x=30.16,60.16,y=10) and SIG_NEG (J2+J4 only
# @ x=90.16,120.16,y=10) both need to get past EXC_POS's F.Cu lane (14)
# *and* EXC_NEG's B.Cu lane (18) to reach their own lane (22) - one via
# hop per crossing (F.Cu -> B.Cu -> F.Cu), landing back on F.Cu exactly
# at the SIG lane so both nets can share y=22 on the same layer (their
# x-ranges, 30.16-60.16 vs 90.16-120.16, stay disjoint, so sharing both
# the layer and the y is safe - same trick used repeatedly elsewhere in
# this board).
for x in (30.16, 60.16, 90.16, 120.16):
    net = "SIG_POS" if x < 90 else "SIG_NEG"
    track(x, 10, x, 13, "F.Cu", net)
    via(x, 13, net)
    track(x, 13, x, 17, "B.Cu", net)
    via(x, 17, net)
    track(x, 17, x, SIG_LANE_Y, "F.Cu", net)
track(30.16, SIG_LANE_Y, 60.16, SIG_LANE_Y, "F.Cu", "SIG_POS")
track(90.16, SIG_LANE_Y, 120.16, SIG_LANE_Y, "F.Cu", "SIG_NEG")
# L-shaped final approaches (vertical at a tap x, then horizontal AT the
# exact target y) rather than direct diagonals - a diagonal from this
# lane toward J5 passes within ~1.5mm of the *adjacent* J5 pad on the
# way to its own target, tight enough to risk the same kind of short as
# EXC_NEG's approach above; an L-shape only ever touches its own pad's y.
via(45, SIG_LANE_Y, "SIG_POS")
track(45, SIG_LANE_Y, 45, 40.08, "B.Cu", "SIG_POS")
track(45, 40.08, 60, 40.08, "B.Cu", "SIG_POS")    # -> J5 pad3 (60,40.08)
via(105, SIG_LANE_Y, "SIG_NEG")
# Detours up to y=30 (above every J6 pad/stub - all at y>=35) and over to
# x=65 before dropping to pad4's own y=42.62, rather than one straight
# horizontal at y=42.62 - that direct line crosses x=80-95 at that exact
# y, right where the J6<->J7 corridor's stub-to-lane drops live. Tried
# moving just that final leg to F.Cu instead (a different layer than
# those B.Cu drops) - fixed that conflict but created a new one: F.Cu at
# y=42.62 is exactly VCC_3V3's own stub-to-J6 row. Rather than keep
# hunting for a clear layer at a busy y, this avoids the busy y (35-42.62,
# where every J6 pad/stub sits) entirely, so the layer choice (stayed on
# B.Cu throughout) stops mattering.
track(105, SIG_LANE_Y, 105, 30, "B.Cu", "SIG_NEG")
track(105, 30, 65, 30, "B.Cu", "SIG_NEG")
track(65, 30, 65, 42.62, "B.Cu", "SIG_NEG")
track(65, 42.62, 60, 42.62, "B.Cu", "SIG_NEG")    # -> J5 pad4 (60,42.62)

# -- J6 <-> J7 (J7 now at the bottom edge, (146,81) rotated 180 - see J7
# comment above). Pads: pad1=GND(146,81) pad2=VCC(144.98,78.46)
# pad3=SCK(143.96,81) pad4=DT(142.94,78.46) - a tight cluster again, same
# character as the previous right-edge position, just transposed:
# GND/SCK now share a Y (81) instead of an X, and VCC/DT share the other
# Y (78.46).
#
# Same "keep each net's own lane, order lane depth to match target
# order" trick as J1-J4 above, applied to the depth (Y) axis this time.
# Targets sorted by X: DT(142.94) < SCK(143.96) < VCC(144.98) < GND(146).
# Give the FURTHEST-reaching target (GND) the SHALLOWEST lane and the
# NEAREST target (DT) the DEEPEST lane - each drop then only travels
# through lane-y's that are shallower than its own, and a drop only
# avoids a shallower lane if the drop's own x sits *outside* that lane's
# span. Stubs go east (toward J7, not doubling back west of J6 first) at
# x=97/99/101/103, all clustered just past J6's own x=95 - since every
# lane then extends the rest of the way east to ~140-150 anyway, the
# stub ordering that keeps each drop outside the shallower lanes' spans
# is the *reverse* of the west-side version: shallowest lane (GND) gets
# the stub furthest from J6 (103, so its lane's span starts past every
# other net's drop), deepest (DT) gets the one closest to J6 (97).
#
# J6's pads are through-hole (copper on both F.Cu and B.Cu already), so a
# track can just start on whichever layer it needs directly at the pad -
# an earlier version routed a short F.Cu stub off J6 before via-ing to
# B.Cu, on every net, which turned out to be vestigial for two of them
# (nothing else occupies F.Cu right at J6, or did once SCK moved off
# B.Cu entirely - see below). GND is a single unbroken B.Cu line, no via.
# SCK is a single unbroken F.Cu line, no via - it needs to cross DT's
# B.Cu horizontal (at y=74, out to x=142.94) somewhere along the way, and
# F.Cu is otherwise clear along SCK's whole path (J1-J4/J5's F.Cu stuff
# stays within x<=110, y<=35, well clear of SCK's x=95-143.96, y=40.08-81).
track(95, 35, 103, 35, "B.Cu", "GND")
track(103, 35, 103, 45, "B.Cu", "GND")
track(103, 45, 149, 45, "B.Cu", "GND")
# Offset to x=149, not straight into pad1's own x=146 - that vertical
# would run within 1.02mm of J7 pad2 (VCC, 144.98,78.46) for its whole
# length, since pad1/pad2 are that close together - DRC-flagged
# clearance (0.12mm actual vs 0.2mm required). x=149 stays clear of
# every J7 pad and (since it stops at y=81, short of y=82.15) clear of
# the NPTH mounting hole at (150.47,83.3) too.
track(149, 45, 149, 81, "B.Cu", "GND")
track(149, 81, 146, 81, "B.Cu", "GND")             # -> J7 pad1 (146,81)

# Stub at x=102, not 99 - VCC_3V3's own stub (below) is F.Cu too now and
# reaches to x=101, so 99 landed inside it (DRC: tracks_crossing).
track(95, 40.08, 102, 40.08, "F.Cu", "SCK")
track(102, 40.08, 102, 65, "F.Cu", "SCK")
# Same fix as GND above, offset the other way: straight into pad3's own
# x=143.96 ran within 1.02mm of J7 pad2 (VCC) the whole way down. x=140
# stays clear of VCC (144.98) and DT (142.94) alike.
track(102, 65, 140, 65, "F.Cu", "SCK")
track(140, 65, 140, 81, "F.Cu", "SCK")
track(140, 81, 143.96, 81, "F.Cu", "SCK")          # -> J7 pad3 (143.96,81)

# VCC_3V3 and DT are the two nets that genuinely can't also drop their
# via, not from a missed simplification but real geometry: each needs a
# lane deep enough that its drop, on the way down, passes through the
# *other's* row at J6 (VCC's source y=42.62 sits inside DT's drop range
# 37.54-74; DT's source y=37.54 likewise sits inside VCC's own drop
# range once VCC is deep enough to matter) - so whichever one is "in the
# way" at that crossing point needs to be on the opposite layer right
# there, which means starting that specific stub on F.Cu rather than
# B.Cu. Checked exhaustively (every pairing among GND/VCC/DT/SCK, not
# just the one conflict DRC first caught after a first attempt put both
# on B.Cu) - this is the minimum: 2 vias total (one each), not 4.
track(95, 42.62, 101, 42.62, "F.Cu", "VCC_3V3")
via(101, 42.62, "VCC_3V3")
track(101, 42.62, 101, 55, "B.Cu", "VCC_3V3")
track(101, 55, 144.98, 55, "B.Cu", "VCC_3V3")
track(144.98, 55, 144.98, 78.46, "B.Cu", "VCC_3V3")  # -> J7 pad2 (144.98,78.46)

track(95, 37.54, 97, 37.54, "F.Cu", "DT")
via(97, 37.54, "DT")
track(97, 37.54, 97, 74, "B.Cu", "DT")
track(97, 74, 142.94, 74, "B.Cu", "DT")
track(142.94, 74, 142.94, 78.46, "B.Cu", "DT")     # -> J7 pad4 (142.94,78.46)

# -- J1-J4 wire-color labels --
# R/B/W above each of J1-J4's 3 pins, matching the documented sensor
# lead convention (wiring.md: Red=E+, Black=E-, White=Signal) - pin1=R,
# pin2=B, pin3=W, in that fixed order for every connector regardless of
# which physical corner (FL/BR/FR/BL) it's wired to. Placed at y=3, above
# the connector body (courtyard top at y=6) and clear of the board edge
# (y=0) and of each connector's own reference designator (default
# position ~y=5.35, i.e. between these labels and the connector) -
# checked via DRC's silk_overlap rule, not just eyeballed.
for px in (20, 50, 80, 110):
    silk_text("R", px, 3, 1.0)
    silk_text("B", px + 5.08, 3, 1.0)
    silk_text("W", px + 10.16, 3, 1.0)

# -- silkscreen branding --
# Silkscreen is a print layer, not copper - it doesn't need clearance
# from tracks/lanes underneath, only from other silkscreen (reference
# designators, board edge). This spot stays clear of J1-J4/J5/J6/J7's own
# reference designators.
silk_text("KegSensor", 100, 58, 2.2)
silk_text("Sallaup Electronics", 100, 62, 1.2)
silk_text("Rev A", 100, 68, 2.2)
silk_text("2026", 100, 72, 1.5)

tmpl = open(TEMPLATE_PCB).read()
layers_block = extract_balanced(tmpl, tmpl.index("\t(layers"))
setup_block = extract_balanced(tmpl, tmpl.index("\t(setup"))

pcb = f'''(kicad_pcb
\t(version 20241229)
\t(generator "pcbnew")
\t(generator_version "9.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A3")
{layers_block}
{setup_block}
{net_block()}
\t(gr_rect
\t\t(start 0 0)
\t\t(end 155 90)
\t\t(stroke
\t\t\t(width 0.15)
\t\t\t(type solid)
\t\t)
\t\t(fill no)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{new_uuid()}")
\t)
{chr(10).join(components_out)}
{chr(10).join(tracks_out)}
{chr(10).join(vias_out)}
{chr(10).join(silk_out)}
\t(embedded_fonts no)
)
'''

OUT.write_text(pcb)
print("wrote", OUT, len(pcb), "bytes")
