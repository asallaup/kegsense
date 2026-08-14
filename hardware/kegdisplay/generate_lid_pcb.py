import re, uuid, pathlib

FP_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
TEMPLATE_PCB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/EuroCard160mmX100mm/EuroCard160mmX100mm.kicad_pcb"
OUT = pathlib.Path(__file__).resolve().parent / "keg_display_lid_module.kicad_pcb"

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
    return extract_balanced(text, text.index(f'(footprint "{name}"'))

FP_JST_PH6 = load_footprint("Connector_JST.pretty", "JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical")
FP_PINSOCKET4 = load_footprint("Connector_PinSocket_2.54mm.pretty", "PinSocket_1x04_P2.54mm_Vertical")
FP_LED3 = load_footprint("LED_THT.pretty", "LED_D5.0mm-3")

def new_uuid():
    return str(uuid.uuid4())

NET_NAMES = ["VCC", "GND", "SCL", "SDA", "YELLOW_LED", "GREEN_LED"]
NET_ID = {name: i + 1 for i, name in enumerate(NET_NAMES)}

def net_block():
    lines = ['\t(net 0 "")']
    for name, nid in NET_ID.items():
        lines.append(f'\t(net {nid} "{name}")')
    return "\n".join(lines)

def inject_pad_net(fp_text, pad_num, net_name):
    nid = NET_ID[net_name]
    search = f'(pad "{pad_num}"'
    starts = []
    idx = 0
    while True:
        i = fp_text.find(search, idx)
        if i == -1:
            break
        starts.append(i)
        idx = i + len(search)
    for start in reversed(starts):
        pad_block = extract_balanced(fp_text, start)
        drill_idx = pad_block.find("(drill")
        if drill_idx != -1:
            insert_end = pad_block.index(")", drill_idx) + 1
        else:
            size_idx = pad_block.index("(size")
            insert_end = pad_block.index(")", size_idx) + 1
        new_pad = pad_block[:insert_end] + f'\n\t\t\t(net {nid} "{net_name}")' + pad_block[insert_end:]
        fp_text = fp_text[:start] + new_pad + fp_text[start + len(pad_block):]
    return fp_text

def instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, attr="through_hole"):
    text = fp_text
    for pad_num, net_name in pad_nets.items():
        text = inject_pad_net(text, pad_num, net_name)
    fp_name = lib_id.split(":")[1]
    text = text.replace(f'(footprint "{fp_name}"',
                         f'(footprint "{lib_id}"\n\t\t(layer "F.Cu")\n\t\t(uuid "{new_uuid()}")\n\t\t(at {x} {y} {angle})\n\t\t(attr {attr})',
                         1)
    text = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', text, count=1)
    text = re.sub(r'\(uuid "[0-9a-fA-F-]+"\)', lambda m: f'(uuid "{new_uuid()}")', text)
    return text

components_out = []

def add_component(fp_text, lib_id, ref, x, y, angle, pad_nets, attr="through_hole"):
    components_out.append(instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, attr))

# --- Placement (courtyard-based, same method as the main board) -------
# J2 (OLED, left) and LED1 (right) deliberately kept far apart in X so
# the two branch families - J1 pins 1-4 heading to J2, pins 5-6 heading
# to LED1 - never need to route anywhere near each other's pads. An
# earlier attempt with J2/LED1 close together caused real shorts
# (LED_D5.0mm-3's pads are 1.8mm square - a track passing within ~1mm of
# an off-target pad's center already overlaps its copper).
add_component(FP_JST_PH6, "Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical", "J1", 8, 6, 0,
              {"1": "VCC", "2": "GND", "3": "SCL", "4": "SDA", "5": "YELLOW_LED", "6": "GREEN_LED"})
add_component(FP_PINSOCKET4, "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "J2", 6, 16, 0,
              {"1": "VCC", "2": "GND", "3": "SCL", "4": "SDA"})
add_component(FP_LED3, "LED_THT:LED_D5.0mm-3", "LED1", 20, 16, 0,
              {"1": "YELLOW_LED", "2": "GREEN_LED", "3": "GND"})

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

# J1 pads (angle 0, world = origin + local): 1=(8,6) 2=(10,6) 3=(12,6)
# 4=(14,6) 5=(16,6) 6=(18,6). J2 pads: 1=(6,16) 2=(6,18.54) 3=(6,21.08)
# 4=(6,23.62). LED1 pads: 1=(20,16) 2=(22.54,16) 3=(25.08,16).
#
# Two branch families, kept spatially separate (see placement comment
# above): J1 pins 1-4 -> J2 (all routing stays x<=14, well left of
# LED1's pads at x>=20); J1 pins 5-6 -> LED1 (x>=16, well right of J2's
# pads at x=6). GND reaches both, via a B.Cu lane at y=9 that both
# branches' F.Cu tracks can cross freely (different layer).

# VCC: straight vertical + one horizontal into J2.1.
track(8, 6, 8, 16, "F.Cu", "VCC")
track(8, 16, 6, 16, "F.Cu", "VCC")

# SCL: x=12 column, clear of J2's own x=6 pads and of LED1 (x>=20).
track(12, 6, 12, 21.08, "F.Cu", "SCL")
track(12, 21.08, 6, 21.08, "F.Cu", "SCL")

# SDA: x=14 column.
track(14, 6, 14, 23.62, "F.Cu", "SDA")
track(14, 23.62, 6, 23.62, "F.Cu", "SDA")

# YELLOW_LED: x=16 column down to LED1's own y, then straight into pad1.
track(16, 6, 16, 16, "F.Cu", "YELLOW_LED")
track(16, 16, 20, 16, "F.Cu", "YELLOW_LED")

# GREEN_LED: x=18 column down toward LED1's row, but that column crosses
# YELLOW_LED's own horizontal (16,16)-(20,16) at (18,16) - same layer,
# real conflict (DRC-caught, twice - the pad/track clearance needed
# turned out bigger than first two attempts gave it: LED1's pads are
# 1.8mm square, PinSocket's are 1.7mm square, so anything passing within
# ~1.2mm of an off-target pad center still overlaps its copper). Via-hop
# to B.Cu with generous 2mm+ clearance on both sides of y=16 this time.
track(18, 6, 18, 14, "F.Cu", "GREEN_LED")
via(18, 14, "GREEN_LED")
track(18, 14, 18, 18.5, "B.Cu", "GREEN_LED")
via(18, 18.5, "GREEN_LED")
track(18, 18.5, 22.54, 18.5, "F.Cu", "GREEN_LED")
track(22.54, 18.5, 22.54, 16, "F.Cu", "GREEN_LED")

# GND: J1.2 -> B.Cu lane at y=9 -> branches left to J2.2, right to
# LED1.3. Left branch offset to x=9, not x=7 - 1mm clearance from J2.1's
# (VCC) pad at (6,16) still overlapped its copper (DRC-caught again);
# 3mm clears it comfortably.
track(10, 6, 10, 9, "B.Cu", "GND")
track(9, 9, 10, 9, "B.Cu", "GND")
track(9, 9, 9, 18.54, "B.Cu", "GND")
track(9, 18.54, 6, 18.54, "B.Cu", "GND")
track(10, 9, 25.08, 9, "B.Cu", "GND")
track(25.08, 9, 25.08, 16, "B.Cu", "GND")

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

silk_text("KegDisplay Lid", 22, 3, 0.8)

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
\t(paper "A4")
{layers_block}
{setup_block}
{net_block()}
\t(gr_rect
\t\t(start 0 0)
\t\t(end 30 28)
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
