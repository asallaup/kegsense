import re, uuid, pathlib

SYM_ROOT = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
OUT_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_NAME = "keg_display_lid_module"
SCH_PATH = OUT_DIR / f"{PROJECT_NAME}.kicad_sch"

# --- Design summary ---------------------------------------------------
# Per-tap KegDisplay LID board - hosts the OLED and the bi-color status
# LED, both physically mounted on the case lid (see README's mechanical-
# split decision). Connects back to the main board (keg_display_module,
# same directory) via a single 6-wire cable, JST-PH on both ends.
# J1 = cable-in from the main board (same JST-PH 6-pin part as the main
# board's own J3, so the cable is a standard JST-to-JST harness).
# J2 = OLED module socket (4-pin: VCC/GND/SCL/SDA) - most 0.91in SSD1306
# modules ship with their own male pin header, so this is a female
# socket the module plugs into.
# LED1 = the bi-color (yellow/green) status LED itself - a real
# component on this board now (not a connector standing in for an
# off-board part, unlike the main board's earlier placeholder). Common
# cathode, 3 leads. No series resistors here - those stay on the main
# board, ahead of the cable (see main board's README/schematic notes).
#
# Net plan (all straight pass-through from J1 to J2/LED1):
#   J1.1 VCC       -> J2.1
#   J1.2 GND       -> J2.2, LED1.3 (common cathode)
#   J1.3 SCL       -> J2.3
#   J1.4 SDA       -> J2.4
#   J1.5 YELLOW_LED -> LED1.1
#   J1.6 GREEN_LED  -> LED1.2

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
    "Conn_01x04": ("Connector_Generic", "Conn_01x04"),
    "Conn_01x06": ("Connector_Generic", "Conn_01x06"),
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

add("J1", "Conn_01x06", 30, 40, "Cable_from_main_board", "Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical",
    {"1": "VCC", "2": "GND", "3": "SCL", "4": "SDA", "5": "YELLOW_LED", "6": "GREEN_LED"})
add("J2", "Conn_01x04", 70, 40, "SSD1306_0.91in_OLED_socket", "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical",
    {"1": "VCC", "2": "GND", "3": "SCL", "4": "SDA"})
add("LED1", "Conn_01x03", 70, 65, "Bicolor_LED_Yellow-Green_CommonCathode", "LED_THT:LED_D5.0mm-3",
    {"1": "YELLOW_LED", "2": "GREEN_LED", "3": "GND"})

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
    ref_prop = prop("Reference", ref, x, y - 10, 0)
    val_prop = prop("Value", value, x, y + 10, 0)
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
    x, y = c["at"]
    pins = SYM_PINS[c["sym_key"]]
    symbol_blocks.append(sym_instance(c["ref"], c["sym_key"], x, y, c["value"], c["footprint"], len(pins)))
    for num, lx, ly, angle in pins:
        px = snap(x + lx)
        py = snap(y - ly)
        net = c["pins"][num]
        w, l = wire_and_label(px, py, lx, ly, net)
        wire_blocks.append(w)
        label_blocks.append(l)

add_text("Keg Display LID Module - hosts the OLED + bi-color status LED.\\nConnects to the main board (keg_display_module) via one 6-wire JST-PH cable - see ../README.md.", 20, 10, 2)
add_text("J2 = OLED module socket, pin order VCC/GND/SCL/SDA - CONFIRM against\\nthe actual 0.91in SSD1306 module's own pin order before wiring.\\nLED1 = bi-color LED, common cathode, no series resistors here (they\\nstay on the main board, ahead of the cable).", 20, 90, 1.27)

sch = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A4")
\t(title_block
\t\t(title "KegDisplay Lid Module")
\t\t(company "Sallaup Electronics")
\t\t(comment 1 "Per-tap lid board: OLED socket + bi-color status LED")
\t\t(comment 2 "Part of the Sallaup KegSense keg-monitoring system")
\t)
\t(lib_symbols
{chr(10).join(SYM_BLOCKS[k] for k in ["Conn_01x03", "Conn_01x04", "Conn_01x06"])}
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
