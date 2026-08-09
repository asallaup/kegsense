import re, uuid, pathlib

FP_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
TEMPLATE_PCB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/EuroCard160mmX100mm/EuroCard160mmX100mm.kicad_pcb"
OUT = pathlib.Path("/Users/arvid/projects/beeer-weight-proto/hardware/keg-module-pcb/keg_sensor_module.kicad_pcb")

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

def instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets):
    text = fp_text
    for pad_num, net_name in pad_nets.items():
        text = inject_pad_net(text, pad_num, net_name)
    text = text.replace(f'(footprint "{lib_id.split(":")[1]}"',
                         f'(footprint "{lib_id}"\n\t\t(layer "F.Cu")\n\t\t(uuid "{new_uuid()}")\n\t\t(at {x} {y} {angle})\n\t\t(attr through_hole)',
                         1)
    text = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', text, count=1)
    return text

components_out = []

def add_component(fp_text, lib_id, ref, x, y, angle, pad_nets):
    components_out.append(instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets))

# J1-J4 sensor terminals, reordered physically (FL,BR,FR,BL) so diagonal
# pairs (SIG_POS/SIG_NEG) are adjacent - widened to 20mm row pitch
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J1", 10, 15, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS"})   # FL
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J3", 10, 35, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_POS"})   # BR
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J2", 10, 55, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_NEG"})   # FR
add_component(FP_TERMINAL3, "TerminalBlock:TerminalBlock_bornier-3_P5.08mm", "J4", 10, 75, 0,
              {"1": "EXC_POS", "2": "EXC_NEG", "3": "SIG_NEG"})   # BL

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

def via(x, y, net_name):
    vias_out.append(f'''\t(via
\t\t(at {x} {y})
\t\t(size 0.6)
\t\t(drill 0.3)
\t\t(layers "F.Cu" "B.Cu")
\t\t(net {NET_ID[net_name]})
\t\t(uuid "{new_uuid()}")
\t)''')

# -- J1-J4 <-> J5 bus (F.Cu vertical buses, B.Cu diagonal jogs via vias) --
# Tap points chosen in the SAME relative order as their J5 target pads
# (20 < 30 < 32 < 60, matching EXC_POS<EXC_NEG<SIG_POS<SIG_NEG targets)
# so the 4 B.Cu diagonals fan in without crossing each other.
track(10, 15, 10, 75, "F.Cu", "EXC_POS")
via(10, 20, "EXC_POS")
track(10, 20, 60, 35, "B.Cu", "EXC_POS")          # -> J5 pad1 (60,35)

track(15.08, 15, 15.08, 75, "F.Cu", "EXC_NEG")
via(15.08, 30, "EXC_NEG")
track(15.08, 30, 60, 37.54, "B.Cu", "EXC_NEG")    # -> J5 pad2 (60,37.54)

track(20.16, 15, 20.16, 35, "F.Cu", "SIG_POS")    # J1+J3 only
via(20.16, 32, "SIG_POS")
track(20.16, 32, 60, 40.08, "B.Cu", "SIG_POS")    # -> J5 pad3 (60,40.08)

track(20.16, 55, 20.16, 75, "F.Cu", "SIG_NEG")    # J2+J4 only
via(20.16, 60, "SIG_NEG")
track(20.16, 60, 60, 42.62, "B.Cu", "SIG_NEG")    # -> J5 pad4 (60,42.62)

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
track(95, 35, 97, 35, "F.Cu", "GND")
via(97, 35, "GND")
track(97, 35, 97, 20, "B.Cu", "GND")
track(97, 20, 146, 20, "B.Cu", "GND")
track(146, 20, 146, 35, "B.Cu", "GND")             # -> J7 pad1 (146,35), from above

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
\t(embedded_fonts no)
)
'''

OUT.write_text(pcb)
print("wrote", OUT, len(pcb), "bytes")
