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

# J7: RJ11-to-hub jack (RJ14 6P4C - genuine RJ11-style body/contact count)
add_component(FP_RJ11, "Connector_RJ:RJ14_Connfly_DS1133-S4_Horizontal", "J7", 135, 33, 0,
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

# -- J6 <-> J7 (J7 = RJ14, pad1=GND(135,33) pad2=VCC(136.02,35.54)
# pad3=SCK(137.04,33) pad4=DT(138.06,35.54)) --
# GND, SCK: simple L-shapes (own source-y horizontal, then vertical into
# pad) - source-y order matches target-x order for this pair, so they
# don't cross; also clear of J7's NPTH mounting holes at (130.53,30.7)
# and (142.53,30.7).
track(95, 35, 135, 35, "F.Cu", "GND")
track(135, 35, 135, 33, "F.Cu", "GND")             # -> J7 pad1 (135,33)

# SCK's straight final approach clips VCC's pad (only 1.02mm clearance at
# RJ14's tight pitch) - given J7's 4 pads are packed within ~3x2.5mm, the
# reliable fix is a via for just the final approach, landing on the
# otherwise-empty B.Cu layer where it can go direct with no neighbors to
# graze.
# A direct B.Cu diagonal into the pad still grazes GND's or VCC's pad
# (they're only ~1-2mm away at this pitch) no matter the angle - approach
# straight down from above instead (x locked to the target's own x, well
# above the y=33-40.08 pad band and above the mounting holes at y=30.7),
# so the final segment isn't diagonal-close to any neighboring pad.
track(95, 40.08, 110, 40.08, "F.Cu", "SCK")
via(110, 40.08, "SCK")
track(110, 40.08, 110, 25, "B.Cu", "SCK")
track(110, 25, 137.04, 25, "B.Cu", "SCK")
track(137.04, 25, 137.04, 33, "B.Cu", "SCK")       # -> J7 pad3 (137.04,33)

# DT and VCC both target y=35.54, right where GND/SCK's F.Cu horizontals
# and verticals live - rather than a via, route both around that band
# entirely, staying on F.Cu throughout.
#
# DT's vertical jog is kept tiny (37.54->37, just 0.54mm) so it doesn't
# block VCC's escape at y=42.62 further down; the long horizontal run is
# at y=37, comfortably clear of GND (y=35) and SCK (y=40.08) pads/traces.
track(95, 37.54, 91, 37.54, "F.Cu", "DT")
track(91, 37.54, 91, 37, "F.Cu", "DT")
track(91, 37, 138.06, 37, "F.Cu", "DT")
track(138.06, 37, 138.06, 35.54, "F.Cu", "DT")     # -> J7 pad4 (138.06,35.54)

# VCC escapes to x=89 entirely at its own y=42.62 (clear of DT's now-tiny
# vertical and of DT's y=37 horizontal, both far from 42.62), then drops
# to the y=36.3 crossing height at x=89 - safely left of DT's horizontal,
# which only starts at x=91.
track(95, 42.62, 89, 42.62, "F.Cu", "VCC_3V3")
track(89, 42.62, 89, 36.3, "F.Cu", "VCC_3V3")
track(89, 36.3, 136.02, 36.3, "F.Cu", "VCC_3V3")
track(136.02, 36.3, 136.02, 35.54, "F.Cu", "VCC_3V3")  # -> J7 pad2 (136.02,35.54)

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
\t\t(end 145 90)
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
