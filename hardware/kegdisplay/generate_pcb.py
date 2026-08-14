import re, uuid, pathlib

FP_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
TEMPLATE_PCB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/EuroCard160mmX100mm/EuroCard160mmX100mm.kicad_pcb"
OUT = pathlib.Path(__file__).resolve().parent / "keg_display_module.kicad_pcb"

N_LEDS = 5

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

FP_JST_PH3 = load_footprint("Connector_JST.pretty", "JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal")
FP_R_VERT = load_footprint("Resistor_THT.pretty", "R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical")
FP_C_DISC = load_footprint("Capacitor_THT.pretty", "C_Disc_D3.0mm_W2.0mm_P2.50mm")
FP_WS2812_MINI = load_footprint("LED_SMD.pretty", "LED_WS2812B-Mini_PLCC4_3.5x3.5mm")
FP_MOUNT = load_footprint("MountingHole.pretty", "MountingHole_2.2mm_M2")

def new_uuid():
    return str(uuid.uuid4())

NET_NAMES = ["GND", "VCC"] + [f"DATA_{i}" for i in range(N_LEDS + 2)]
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

def instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, attr="through_hole", ref_at=None, hide_ref=False):
    text = fp_text
    for pad_num, net_name in pad_nets.items():
        text = inject_pad_net(text, pad_num, net_name)
    fp_name = lib_id.split(":")[1]
    text = text.replace(f'(footprint "{fp_name}"',
                         f'(footprint "{lib_id}"\n\t\t(layer "F.Cu")\n\t\t(uuid "{new_uuid()}")\n\t\t(at {x} {y} {angle})\n\t\t(attr {attr})',
                         1)
    text = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', text, count=1)
    if ref_at is not None:
        text = re.sub(r'(\(property "Reference" "[^"]*"\s*\n\s*\(at )[^)]+(\))',
                       lambda m: f'{m.group(1)}{ref_at[0]} {ref_at[1]} {ref_at[2]}{m.group(2)}',
                       text, count=1)
    if hide_ref:
        # Densely packed parts (10 LEDs at 5.8mm pitch) don't have room
        # for individual silkscreen reference labels without overlapping
        # their neighbors - hidden here rather than fought over pixel by
        # pixel; still fully present in the BOM/pick-place data. Footprint
        # properties put (hide yes) as a sibling of (at)/(layer)/(uuid),
        # NOT nested inside (effects ...) - confirmed against this same
        # footprint's own (already-hidden) Datasheet property, since an
        # earlier attempt placed it inside effects and silently had no
        # effect (still showed up as a real DRC silk_overlap).
        ref_block_m = re.search(r'(\(property "Reference" "[^"]*"\s*\n\s*\(at [^)]+\)\s*\n\s*\(layer "[^"]*"\)\s*\n)', text)
        if ref_block_m:
            insert_at = ref_block_m.end()
            text = text[:insert_at] + '\t\t(hide yes)\n' + text[insert_at:]
        # This footprint also has a separate "1" pin-1-orientation marker
        # (fp_text user "1" ...) on F.SilkS - collides with the next LED
        # over at this pitch too, same fix (pad 1's own square shape
        # already marks pin 1 without it).
        pin1_m = re.search(r'\t\(fp_text user "1"[\s\S]*?\n\t\)\n', text)
        if pin1_m:
            text = text[:pin1_m.start()] + text[pin1_m.end():]
    text = re.sub(r'\(uuid "[0-9a-fA-F-]+"\)', lambda m: f'(uuid "{new_uuid()}")', text)
    return text

components_out = []

def add_component(fp_text, lib_id, ref, x, y, angle, pad_nets, attr="through_hole", ref_at=None, hide_ref=False):
    components_out.append(instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, attr, ref_at, hide_ref))

# --- Placement (rev 5: 10-LED WS2812 progress bar, no MCU) -------------
# Real constraint: ~100mm between taps, ~30mm max height. A tight 5mm
# LED pitch keeps the 10-LED span to 45mm, leaving real room for
# connectors + passives within the 100mm budget - unlike the ATtiny1614+
# OLED board, which never fit no matter how it was rearranged (see
# README's revision note).
#
# J1/J2 connector choice is NOT committed (see README Still Open) - using
# small JST-PH 3-pin here as a placeholder to get real PCB geometry to
# validate against, not a final decision.

add_component(FP_JST_PH3, "Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal", "J1", 7.05, 11, 90,
              {"1": "GND", "2": "VCC", "3": "DATA_0"}, attr="through_hole", ref_at=(9, 1.5, 0))

add_component(FP_R_VERT, "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical", "R1", 26, 4.5, 0,
              {"1": "DATA_0", "2": "DATA_1"}, attr="through_hole")

add_component(FP_C_DISC, "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", "C1", 33, 4.5, 0,
              {"1": "VCC", "2": "GND"}, attr="through_hole")

led_x0 = 19
led_pitch = 5.8
for i in range(1, N_LEDS + 1):
    x = led_x0 + (i - 1) * led_pitch
    din_net = f"DATA_{i}"
    dout_net = f"DATA_{i+1}"
    add_component(FP_WS2812_MINI, "LED_SMD:LED_WS2812B-Mini_PLCC4_3.5x3.5mm", f"LED{i}", x, 9, 0,
                  {"4": din_net, "2": dout_net, "1": "VCC", "3": "GND"}, attr="smd", hide_ref=True)

j2_x = led_x0 + (N_LEDS - 1) * led_pitch + 2.64 + 2 + 5
add_component(FP_JST_PH3, "Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal", "J2", j2_x, 7, 270,
              {"1": "GND", "2": "VCC", "3": f"DATA_{N_LEDS+1}"}, attr="through_hole", ref_at=(-6, 0, 0))

board_width = j2_x + 2
board_height = 16

# Mounting holes - two, diagonal, clear of every component's courtyard
# (all components sit in one row around y=9; holes go above/below that).
add_component(FP_MOUNT, "MountingHole:MountingHole_2.2mm_M2", "MH1", 17.5, 13.5, 0, {}, ref_at=(3.5, 0, 0))
add_component(FP_MOUNT, "MountingHole:MountingHole_2.2mm_M2", "MH2", 41, 3, 0, {}, ref_at=(-3.5, 0, 0))

silk_out = []

def silk_text(text, x, y, size, layer="F.SilkS"):
    mirror = "\n\t\t\t(justify mirror)" if layer.startswith("B.") else ""
    silk_out.append(f'''\t(gr_text "{text}"
\t\t(at {x} {y} 0)
\t\t(layer "{layer}")
\t\t(uuid "{new_uuid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t\t(thickness {round(size * 0.15, 3)})
\t\t\t){mirror}
\t\t)
\t)''')

silk_text("IN", 8.55, 14.5, 1.0)
silk_text("OUT", j2_x, 14.5, 1.0)
silk_text("KegDisplay - Sallaup Elec.", 32, 14, 0.8)

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
\t\t(start 5 0)
\t\t(end {round(board_width,2)} {board_height})
\t\t(stroke
\t\t\t(width 0.15)
\t\t\t(type solid)
\t\t)
\t\t(fill no)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{new_uuid()}")
\t)
{chr(10).join(components_out)}
{chr(10).join(silk_out)}
\t(embedded_fonts no)
)
'''

OUT.write_text(pcb)
print("wrote", OUT, len(pcb), "bytes, board", round(board_width,2), "x", board_height)
