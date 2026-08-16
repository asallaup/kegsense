import re, uuid, pathlib

FP_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
TEMPLATE_PCB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/EuroCard160mmX100mm/EuroCard160mmX100mm.kicad_pcb"
OUT = pathlib.Path(__file__).resolve().parent / "keg_display_bar_module.kicad_pcb"

# --- Design summary (rev 8) ---------------------------------------------
# An off-the-shelf WS2812 LED strip is glued or screwed to the front of
# this custom PCB (no individually-placed LED footprints - see revision 7
# in README, now superseded), housed in an enclosure on the collar's
# side. J1 (chain in) and J2 (chain out) both sit at the board's BOTTOM
# edge, left and right respectively, so cables exit sideways to reach the
# next tap's box (taps are ~10cm apart horizontally - see README).
#
# TP1/TP2/TP3 are solder points for the strip's own bottom-end leads
# (GND/VCC/DIN); TP4/TP5/TP6 are solder points for the strip's top-end
# leads (GND/VCC/DOUT). The strip itself carries data up its own length -
# not modeled as PCB copper, since it's a separate physical part glued on
# top, not part of this board. TP6 (DOUT) needs to return all the way
# back down to J2; the real board would route that as a via + back-
# copper-layer trace (see README's "PCB signal routing" decision) - NOT
# modeled as explicit copper here, same "placement + net assignment, not
# full routing" level of fidelity as every earlier revision's generator
# script (none of them emit track/via elements - DRC here validates
# physical fit/clearance, not routing completeness).
#
# Board outline and component positions below were hand-tuned in the
# KiCad GUI after the script's initial placement (courtyard-clearance
# fine adjustment: J1/J2 nudged, MH1/MH2 moved to the board's horizontal
# center, board outline resized/shifted) - this script is kept in sync
# with those GUI edits so it stays the reproducible source for this
# layout, not a stale starting point. Not sized to a specific strip yet
# - see README's "Which off-the-shelf strip to source" open item.

BOARD_X0, BOARD_Y0 = 9.5, -2.0
BOARD_X1, BOARD_Y1 = 43.5, 130.0
BOARD_WIDTH = BOARD_X1 - BOARD_X0
BOARD_HEIGHT = BOARD_Y1 - BOARD_Y0

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
FP_TESTPOINT = load_footprint("TestPoint.pretty", "TestPoint_THTPad_D1.5mm_Drill0.7mm")
FP_MOUNT = load_footprint("MountingHole.pretty", "MountingHole_2.2mm_M2")

def new_uuid():
    return str(uuid.uuid4())

NET_NAMES = ["GND", "VCC", "DATA_0", "DATA_1", "DATA_OUT"]
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
        ref_block_m = re.search(r'(\(property "Reference" "[^"]*"\s*\n\s*\(at [^)]+\)\s*\n\s*\(layer "[^"]*"\)\s*\n)', text)
        if ref_block_m:
            insert_at = ref_block_m.end()
            text = text[:insert_at] + '\t\t(hide yes)\n' + text[insert_at:]
    text = re.sub(r'\(uuid "[0-9a-fA-F-]+"\)', lambda m: f'(uuid "{new_uuid()}")', text)
    return text

components_out = []

def add_component(fp_text, lib_id, ref, x, y, angle, pad_nets, attr="through_hole", ref_at=None, hide_ref=False):
    components_out.append(instantiate(fp_text, lib_id, ref, x, y, angle, pad_nets, attr, ref_at, hide_ref))

# --- Placement ------------------------------------------------------------
# J1 (chain in) / J2 (chain out) - near the board's bottom, cables exit
# sideways to the neighboring tap's box. Positions below are the GUI
# fine-tuned values (nudged off a strict edge-flush/shared-Y placement to
# clear MH2 and each other's courtyards once the board was resized) - not
# derived from a formula, kept as literal coordinates so this script
# reproduces the validated layout exactly.
add_component(FP_JST_PH3, "Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal", "J1", 11.55, 124.5, 90,
              {"1": "GND", "2": "VCC", "3": "DATA_0"}, attr="through_hole", hide_ref=True)
add_component(FP_JST_PH3, "Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal", "J2", 41.45, 120.5, 270,
              {"1": "GND", "2": "VCC", "3": "DATA_OUT"}, attr="through_hole", hide_ref=True)

# R1 (data-in series resistor, between J1 and the strip's bottom DIN
# lead) and C1 (decoupling, near the strip's bottom end).
add_component(FP_R_VERT, "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical", "R1", 18, 111, 0,
              {"1": "DATA_0", "2": "DATA_1"}, attr="through_hole")
add_component(FP_C_DISC, "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", "C1", 30, 111, 0,
              {"1": "VCC", "2": "GND"}, attr="through_hole")

# Strip's bottom (IN) end leads - hand-soldered here once the strip is
# glued/screwed in place. Tight 4mm-pitch cluster, centered on the
# board's original 50mm width (kept as literal coordinates, same reason
# as J1/J2 above).
strip_bottom_y = 106
TP_PITCH = 4.0   # tight cluster - real strip end-leads land within a few mm of each other, not spread wide
tp_x0 = 21
add_component(FP_TESTPOINT, "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "TP1", tp_x0, strip_bottom_y, 0, {"1": "GND"})
add_component(FP_TESTPOINT, "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "TP2", tp_x0 + TP_PITCH, strip_bottom_y, 0, {"1": "VCC"})
add_component(FP_TESTPOINT, "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "TP3", tp_x0 + 2 * TP_PITCH, strip_bottom_y, 0, {"1": "DATA_1"})

# Strip's top (OUT) end leads. TP6 (DATA_OUT) is the one net that needs a
# via + back-layer return trace down to J2 on the real board (see design
# summary above) - not modeled as copper here.
strip_top_y = 10
add_component(FP_TESTPOINT, "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "TP4", tp_x0, strip_top_y, 0, {"1": "GND"})
add_component(FP_TESTPOINT, "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "TP5", tp_x0 + TP_PITCH, strip_top_y, 0, {"1": "VCC"})
add_component(FP_TESTPOINT, "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "TP6", tp_x0 + 2 * TP_PITCH, strip_top_y, 0, {"1": "DATA_OUT"})

# Mounting holes - both moved to the board's horizontal center (GUI edit).
add_component(FP_MOUNT, "MountingHole:MountingHole_2.2mm_M2", "MH1", 25, 3.5, 0, {}, ref_at=(3.5, 0, 0), hide_ref=True)
add_component(FP_MOUNT, "MountingHole:MountingHole_2.2mm_M2", "MH2", 25, 120.5, 0, {}, ref_at=(3.5, 0, 0), hide_ref=True)

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

silk_text("IN", 22.05, 124.5, 1.0)
silk_text("OUT", 37.95, 116, 1.0)
silk_text("STRIP IN (GND/VCC/DIN)", 10, 102, 0.8)
silk_text("STRIP OUT (GND/VCC/DOUT)", 10, 16, 0.8)
silk_text("KegDisplay Bar", 16, 129, 0.8)

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
\t\t(start {BOARD_X0} {BOARD_Y0})
\t\t(end {BOARD_X1} {BOARD_Y1})
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
print("wrote", OUT, len(pcb), "bytes, board", BOARD_WIDTH, "x", round(BOARD_HEIGHT, 2))
