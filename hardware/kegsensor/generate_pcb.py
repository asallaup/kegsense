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
# (SIG_POS/SIG_NEG) are adjacent. Rotated -90deg (see J7's rotation-sign
# comment below for why -90, not +90) so each part's 3 pins stack in Y
# instead of spreading in X - without that, all 4 parts' pin1/pin2/pin3
# would land on the exact same 3 y-values, and EXC_POS/EXC_NEG/SIG_POS/
# SIG_NEG buses (below) would have no way to cross the row without
# shorting each other. Rotated, each part's own pins share one x (so a
# horizontal bus at a fixed y cleanly picks up "this pin, every part"),
# mirroring how the pre-rotation vertical layout used a fixed x per pin.
# ref_at=(5.05,-9,0): library default is (5.05,-4.65,0), which after the
# -90 rotation above lands at local (4.65,5.05) - just outside the
# unrotated courtyard but overlapping it post-rotation (DRC: silk_overlap
# against the part's own silkscreen outline). Pushing further out along
# the same local axis moves it to (9,5.05) post-rotation, clear of the
# rotated courtyard (+-4mm) - confirmed via DRC, not just computed by hand.
REF_AT = (5.05, -9, 0)
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J1", 20, 10, -90,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS"}, REF_AT)   # FL
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J3", 50, 10, -90,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS"}, REF_AT)   # BR
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J2", 80, 10, -90,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_NEG"}, REF_AT)   # FR
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J4", 110, 10, -90,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_NEG"}, REF_AT)   # BL

# J5: HX711 load-cell side header
add_component(FP_PINSOCKET4, "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "J5", 60, 35, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS", "4": "SIG_NEG"})

# J6: HX711 digital/power side header (placeholder spacing from J5 - see README)
add_component(FP_PINSOCKET4, "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "J6", 95, 35, 0,
              {"1": "GND", "2": "DT", "3": "SCK", "4": "VCC_3V3"})

# J7: RJ11-to-hub jack (RJ14 6P4C). Rotated -90deg and moved flush with the
# board's right edge (x=155) so the cable is actually reachable from
# outside the case - it was previously stranded ~14-27mm from the nearest
# wall (see git history / README). Courtyard's -Y side is the cable/plug
# face (mounting bosses + pads sit near the PCB-facing back at local
# y=-2.3..2.54, the shell extends out to y=-9).
#
# KiCad's footprint rotation is the *opposite* sign of the standard math
# convention (confirmed empirically: angle=+90 put pad2 at (148.54,33.98)
# and pointed the cable face -X/left, i.e. into the board - the reverse of
# both what the formula below predicts and what's wanted). angle=-90 is
# the one that both matches these pad targets and points the cable face
# +X/right, out through the board edge - verified via kicad-cli DRC
# reporting actual pad coordinates, not assumed.
add_component(FP_RJ11, "Connector_RJ:RJ14_Connfly_DS1133-S4_Horizontal", "J7", 146, 35, -90,
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

# -- J1-J4 <-> J5 bus (F.Cu horizontal buses, B.Cu diagonal jogs via vias) --
# Rotated J1-J4 (see placement comment above) put each part's own pins on
# one shared x, at fixed y offsets 0/5.08/10.16 from its placement y=10 -
# i.e. pin1 of every part sits at y=10, pin2 at y=15.08, pin3 at y=20.16,
# regardless of which part. So "pin N, every part" is a straight
# horizontal F.Cu run at that fixed y, exactly mirroring how the
# pre-rotation layout used a fixed x per pin. SIG_POS/SIG_NEG share pin3's
# y=20.16 but stay on disjoint x-ranges (J1+J3 vs J2+J4), same trick the
# old layout used with disjoint y-ranges at a shared x.
# Tap points all kept at x<=85, i.e. clear of the J6<->J7 corridor (which
# starts at x=93 - see VCC_3V3's B.Cu vertical below) - an earlier version
# of this used tap x=95/100, and those diagonals cut straight through that
# corridor's B.Cu traces, DRC-flagged as both track-crossing and solder
# mask bridge shorts. Also chosen (30 < 85, 35 < 82) so, combined with the
# target y ordering at J5 (35 < 37.54 < 40.08 < 42.62), the 4 diagonals
# fan in without crossing each other (verified via DRC, not just by eye).
track(20, 10, 110, 10, "F.Cu", "EXC_POS")           # pin1: J1,J3,J2,J4
via(30, 10, "EXC_POS")
track(30, 10, 60, 35, "B.Cu", "EXC_POS")          # -> J5 pad1 (60,35)

track(20, 15.08, 110, 15.08, "F.Cu", "EXC_NEG")     # pin2: J1,J3,J2,J4
# Tap at x=62 (not a direct diagonal) - two earlier attempts both failed
# DRC: x=85's diagonal cut through J2's own pad3 (80,20.16), and a
# straight diagonal from x=65 swung within ~0.55mm of J5's own pad1
# (60,35) on its way in to pad2, since pad1/pad2 are only 2.54mm apart.
# This L-shape - a near-vertical run at x=62 (2mm clear of pad1, still
# clear of SIG_NEG's diagonal further right - see below) then a short
# final horizontal AT pad2's own y=37.54 - never gets closer than 2mm to
# pad1 at any point, unlike a diagonal that necessarily passes close to
# it en route to the adjacent pad.
via(62, 15.08, "EXC_NEG")
track(62, 15.08, 62, 37.54, "B.Cu", "EXC_NEG")
track(62, 37.54, 60, 37.54, "B.Cu", "EXC_NEG")    # -> J5 pad2 (60,37.54)

track(20, 20.16, 50, 20.16, "F.Cu", "SIG_POS")      # pin3: J1+J3 only
via(35, 20.16, "SIG_POS")
track(35, 20.16, 60, 40.08, "B.Cu", "SIG_POS")    # -> J5 pad3 (60,40.08)

track(80, 20.16, 110, 20.16, "F.Cu", "SIG_NEG")     # pin3: J2+J4 only
via(82, 20.16, "SIG_NEG")
track(82, 20.16, 60, 42.62, "B.Cu", "SIG_NEG")    # -> J5 pad4 (60,42.62)

# -- J6 <-> J7 (J7 now at (146,35) rotated 90deg - see J7 comment above)
# Pads: pad1=GND(146,35) pad2=VCC(143.46,36.02) pad3=SCK(146,37.04)
# pad4=DT(143.46,38.06). NPTH mounting holes at (148.3,30.53) and
# (148.3,42.53).
#
# All 4 nets get a short F.Cu stub near J6 (own source y, distinct x so
# the stubs don't cross each other) then a via onto B.Cu, which is
# otherwise completely empty over here - so the only remaining constraint
# is staying clear of J7's own tightly-packed pads/holes, not other
# traces. GND/SCK (sharing target x=146) approach from the upper-right,
# outside the board edge, then a short final horizontal into the pad from
# the right - clean because that direction has no other pads in the way.
# DT/VCC (sharing target x=143.46) approach as a vertical from below/above
# respectively, since their target-y order (VCC=36.02 < DT=38.06) keeps
# those two vertical spans non-overlapping.
# GND and SCK share target x=146 (2.04mm apart in y) - approach one from
# above, the other from below, so their final verticals (both at x=146)
# occupy non-overlapping y-ranges and can share that x safely. Both stay
# >=2.3mm from J7's NPTH holes at (148.3,30.53)/(148.3,42.53) - tight but
# clear (need 1.875mm).
# Lane y=25, not the original 20 - y=20 ran only 0.16mm from J4's new
# pad3 (110,20.16) once J1-J4 moved up near the top edge (real
# copper-to-copper overlap, not just a warning: DRC flagged both
# shorting_items and solder_mask_bridge). y=25 clears J1-J4's courtyard
# (bottom edge at y=22.88) and the row's own bus/diagonal routing (all
# at y<=20.16), with nothing else routed through this gap before J5/J6.
track(95, 35, 97, 35, "F.Cu", "GND")
via(97, 35, "GND")
track(97, 35, 97, 25, "B.Cu", "GND")
track(97, 25, 146, 25, "B.Cu", "GND")
track(146, 25, 146, 35, "B.Cu", "GND")             # -> J7 pad1 (146,35), from above

# lane y=52, not 45 - DT's escape/approach verticals occupy y=37.54-50 at
# x=101/143.46, both within this horizontal's x-span, so 45 crossed them.
track(95, 40.08, 99, 40.08, "F.Cu", "SCK")
via(99, 40.08, "SCK")
track(99, 40.08, 99, 52, "B.Cu", "SCK")
track(99, 52, 146, 52, "B.Cu", "SCK")
track(146, 52, 146, 37.04, "B.Cu", "SCK")          # -> J7 pad3 (146,37.04), from below

track(95, 37.54, 101, 37.54, "F.Cu", "DT")
via(101, 37.54, "DT")
track(101, 37.54, 101, 50, "B.Cu", "DT")
track(101, 50, 143.46, 50, "B.Cu", "DT")
track(143.46, 50, 143.46, 38.06, "B.Cu", "DT")     # -> J7 pad4 (143.46,38.06)

# VCC stubs LEFT (x=93, not right) so its long vertical doesn't sit inside
# GND's/SCK's lead-in horizontals' x-range (97-146) - avoids crossing them.
track(95, 42.62, 93, 42.62, "F.Cu", "VCC_3V3")
via(93, 42.62, "VCC_3V3")
track(93, 42.62, 93, 12, "B.Cu", "VCC_3V3")
track(93, 12, 143.46, 12, "B.Cu", "VCC_3V3")
# GND's lead-in horizontal is at y=20, clear of this y=12 run; the final
# vertical below still needs F.Cu though, since it crosses GND's y=20 and
# SCK's y=45 horizontals otherwise (both span across x=143.46).
via(143.46, 12, "VCC_3V3")
track(143.46, 12, 143.46, 36.02, "F.Cu", "VCC_3V3")  # -> J7 pad2 (143.46,36.02)

# -- silkscreen branding --
# Right side only (an earlier left-side copy, between J2 and J4, was
# removed) - large open area right of J5/below the J6<->J7 routing (that
# routing stays y<=52; nothing else occupies x=60-155, y=52-90).
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
