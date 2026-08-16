import re, uuid, pathlib

SYM_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
OUT_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_NAME = "keg_display_bar_module"
SCH_PATH = OUT_DIR / f"{PROJECT_NAME}.kicad_sch"

# --- Design summary (rev 8) -------------------------------------------------
# Per-tap KegDisplay board: an off-the-shelf WS2812 LED strip, glued or
# screwed to the front of this custom PCB (no individually-placed LED
# footprints - see revision 7 in README, now superseded). NO MCU -
# KegStation drives the chain directly.
#
# J1 = IN (bottom-left of the enclosure, from the previous tap/KegStation),
# J2 = OUT (bottom-right, to the next tap downstream) - both connectors
# sit at the box's bottom edge so the daisy-chain cable runs sideways
# between taps (~10cm apart horizontally), not top-to-bottom-then-across.
# R1 = data-in series resistor. C1 = decoupling cap near the strip's
# bottom (IN) end.
#
# TP1/TP2/TP3 = solder points for the strip's own bottom-end leads
# (GND/VCC/DIN) - the strip's DIN gets its signal from R1, not directly
# from J1. TP4/TP5/TP6 = solder points for the strip's top-end leads
# (GND/VCC/DOUT) - GND/VCC are the same shared rails as the bottom, DOUT
# is a new net that needs to run all the way back down to J2 (the one hop
# that needs a back-copper-layer return trace on the real PCB, since J2
# sits at the bottom but the strip's DOUT lead is at the top - schematic
# doesn't care about that physical routing, only PCB layout does).

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

def load_symbol(libname, symname):
    text = open(f"{SYM_ROOT}/{libname}.kicad_sym").read()
    idx = text.index(f'(symbol "{symname}"')
    block = extract_balanced(text, idx)
    return block.replace(f'(symbol "{symname}"', f'(symbol "{libname}:{symname}"', 1)

def get_pins(block):
    pins = []
    for m in re.finditer(r'\(pin \w+ \w+\s*\n\s*\(at ([\-0-9.]+) ([\-0-9.]+) (\d+)\).*?\(number "(\w+)"', block, re.S):
        x, y, angle, num = m.groups()
        pins.append((num, float(x), float(y), int(angle)))
    pins.sort(key=lambda p: int(p[0]))
    return pins

LIB_DEFS = {
    "Conn_01x03": ("Connector_Generic", "Conn_01x03"),
    "R": ("Device", "R"),
    "C": ("Device", "C"),
    "TestPoint": ("Connector", "TestPoint"),
}
SYM_BLOCKS = {}
SYM_PINS = {}
for key, (lib, name) in LIB_DEFS.items():
    block = load_symbol(lib, name)
    SYM_BLOCKS[key] = block
    SYM_PINS[key] = get_pins(block)

def new_uuid():
    return str(uuid.uuid4())

ROOT_UUID = new_uuid()

GRID = 1.27
def snap(v):
    return round(round(v / GRID) * GRID, 2)

components = []

def add(ref, sym_key, x, y, value, footprint, pins):
    components.append(dict(ref=ref, sym_key=sym_key, at=(snap(x), snap(y)), value=value,
                            footprint=footprint, pins=pins))

TP_FP = "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm"

add("J1", "Conn_01x03", 20, 30, "IN_from_upstream", "Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal",
    {"1": "GND", "2": "VCC", "3": "DATA_0"})
add("R1", "R", 35, 20, "330", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical",
    {"1": "DATA_0", "2": "DATA_1"})
add("C1", "C", 45, 20, "100n", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm",
    {"1": "VCC", "2": "GND"})

# Strip's bottom (IN) end leads - soldered here, not part of the PCB's own
# copper chain.
add("TP1", "TestPoint", 60, 30, "STRIP_IN_GND", TP_FP, {"1": "GND"})
add("TP2", "TestPoint", 70, 30, "STRIP_IN_VCC", TP_FP, {"1": "VCC"})
add("TP3", "TestPoint", 80, 30, "STRIP_IN_DIN", TP_FP, {"1": "DATA_1"})

# Strip's top (OUT) end leads.
add("TP4", "TestPoint", 100, 30, "STRIP_OUT_GND", TP_FP, {"1": "GND"})
add("TP5", "TestPoint", 110, 30, "STRIP_OUT_VCC", TP_FP, {"1": "VCC"})
add("TP6", "TestPoint", 120, 30, "STRIP_OUT_DOUT", TP_FP, {"1": "DATA_OUT"})

add("J2", "Conn_01x03", 135, 30, "OUT_to_downstream", "Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal",
    {"1": "GND", "2": "VCC", "3": "DATA_OUT"})

def prop(name, val, x, y, angle, hide=False, size=1.27):
    hide_s = "\n\t\t\t\t(hide yes)" if hide else ""
    return f'''\t\t(property "{name}" "{val}"
\t\t\t(at {x} {y} {angle})
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size {size} {size})
\t\t\t\t){hide_s}
\t\t\t)
\t\t)'''

def sym_instance(ref, sym_key, x, y, value, footprint, npins):
    lib, name = LIB_DEFS[sym_key]
    u = new_uuid()
    pins_block = ""
    for i in range(1, npins + 1):
        pu = new_uuid()
        pins_block += f'\t\t(pin "{i}"\n\t\t\t(uuid "{pu}")\n\t\t)\n'
    ref_prop = prop("Reference", ref, x, y - 8, 0)
    val_prop = prop("Value", value, x, y + 8, 0)
    fp_prop = prop("Footprint", footprint, x, y, 0, hide=True)
    ds_prop = prop("Datasheet", "~", x, y, 0, hide=True)
    return f'''\t(symbol
\t\t(lib_id "{lib}:{name}")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{u}")
{ref_prop}
{val_prop}
{fp_prop}
{ds_prop}
{pins_block}\t\t(instances
\t\t\t(project "{PROJECT_NAME}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''

STUB = 2.54

def wire_and_label(px, py, local_x, local_y, net):
    dx = (1 if local_x > 0 else -1) if local_x != 0 else 0
    dy_local = (1 if local_y > 0 else -1) if local_y != 0 else 0
    ex = px + dx * STUB
    ey = py - dy_local * STUB
    wu = new_uuid()
    lu = new_uuid()
    justify = "left" if dx < 0 else ("right" if dx > 0 else ("left" if dy_local <= 0 else "right"))
    wire = f'''\t(wire
\t\t(pts
\t\t\t(xy {px} {py}) (xy {ex} {ey})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{wu}")
\t)'''
    label = f'''\t(label "{net}"
\t\t(at {ex} {ey} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify {justify})
\t\t)
\t\t(uuid "{lu}")
\t)'''
    return wire, label

symbol_blocks = []
wire_blocks = []
label_blocks = []
text_blocks = []

def add_text(msg, x, y, size=1.5):
    tu = new_uuid()
    text_blocks.append(f'''\t(text "{msg}"
\t\t(at {x} {y} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t)
\t\t)
\t\t(uuid "{tu}")
\t)''')

for c in components:
    cx, cy = c["at"]
    pins = SYM_PINS[c["sym_key"]]
    symbol_blocks.append(sym_instance(c["ref"], c["sym_key"], cx, cy, c["value"], c["footprint"], len(pins)))
    for num, lx, ly, angle in pins:
        px = snap(cx + lx)
        py = snap(cy - ly)
        net = c["pins"][num]
        w, l = wire_and_label(px, py, lx, ly, net)
        wire_blocks.append(w)
        label_blocks.append(l)

add_text("Keg Display Bar Module (rev 8) - off-the-shelf WS2812 strip glued/\\nscrewed to the PCB front, NO MCU. KegStation drives the chain directly.\\nSee ../README.md for the full revision history.", 20, 5, 2)
add_text("J1 = chain in (box bottom-left), J2 = chain out (box bottom-right).\\nTP1-3 = strip's bottom (IN) leads: GND/VCC/DIN, soldered by hand.\\nTP4-6 = strip's top (OUT) leads: GND/VCC/DOUT, soldered by hand.\\nOn the real PCB, TP6 (DOUT) is routed via the back copper layer down\\nto J2 (see README). R1 = data-in series resistor. C1 = decoupling.", 20, 50, 1.27)

sch = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A1")
\t(title_block
\t\t(title "KegDisplay Bar")
\t\t(company "Sallaup Electronics")
\t\t(comment 1 "Per-tap WS2812 strip on a custom backer PCB, no MCU")
\t\t(comment 2 "Part of the Sallaup KegSense keg-monitoring system")
\t)
\t(lib_symbols
{chr(10).join(SYM_BLOCKS[k] for k in ["Conn_01x03", "R", "C", "TestPoint"])}
\t)
{chr(10).join(symbol_blocks)}
{chr(10).join(wire_blocks)}
{chr(10).join(label_blocks)}
{chr(10).join(text_blocks)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''

SCH_PATH.write_text(sch)
print("wrote", SCH_PATH)
