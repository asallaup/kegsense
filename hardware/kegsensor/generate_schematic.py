import re, uuid, pathlib

LIB_PATH = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Connector_Generic.kicad_sym"
OUT_DIR = pathlib.Path("/Users/arvid/projects/beeer-weight-proto/hardware/kegsensor")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_NAME = "keg_sensor_module"
SCH_PATH = OUT_DIR / f"{PROJECT_NAME}.kicad_sch"

def extract_balanced(text, start_idx):
    depth = 0
    for i in range(start_idx, len(text)):
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[start_idx:i+1]
    raise ValueError("unbalanced")

lib_text = open(LIB_PATH).read()

def get_symbol_block(name):
    idx = lib_text.index(f'(symbol "{name}"')
    block = extract_balanced(lib_text, idx)
    # qualify only the top-level symbol name (first occurrence at start of block)
    qualified = block.replace(f'(symbol "{name}"', f'(symbol "Connector_Generic:{name}"', 1)
    return qualified

conn3 = get_symbol_block("Conn_01x03")
conn4 = get_symbol_block("Conn_01x04")

def new_uuid():
    return str(uuid.uuid4())

ROOT_UUID = new_uuid()

# --- Component/net plan --------------------------------------------------
# J1-J4: half-bridge sensor terminals (3 pins: E+, E-, SIG)
# Diagonal corner pairing: J1(FL)+J3(BR) -> SIG_POS ; J2(FR)+J4(BL) -> SIG_NEG
# J5: HX711 header, load-cell side  -> pin1=E+ pin2=E- pin3=A+ pin4=A-
# J6: HX711 header, digital/power side -> pin1=GND pin2=DT pin3=SCK pin4=VCC
#     (verify against the specific module's silkscreen; order varies by vendor)
# J7: RJ11 jack -> pin1=GND(Black) pin2=VCC(Red) pin3=SCK(Green) pin4=DT(Yellow)
#     (must match the in-keezer hub's RJ11 pin convention for a straight cable)

PIN_DX = -5.08  # pin connection point x-offset from symbol origin (angle 0)
STUB = 2.54     # extra wire length from pin to label anchor
GRID = 1.27     # KiCad's default schematic connection grid (50 mil)

def snap(v):
    return round(round(v / GRID) * GRID, 2)

components = []  # each: dict(ref, lib, at, pins: [(num, net, label_side)])

def sensor(ref, x, y, corner):
    return dict(ref=ref, lib="Conn_01x03", at=(x, y), value=f"Sensor_{corner}",
                pins=[("1", "EXC_POS"), ("2", "EXC_NEG"), ("3", "SIG_POS" if corner in ("FL", "BR") else "SIG_NEG")],
                footprint="TerminalBlock:TerminalBlock_bornier-3_P5.08mm")

components.append(sensor("J1", 60, 30, "FL"))
components.append(sensor("J2", 60, 60, "FR"))
components.append(sensor("J3", 60, 90, "BR"))
components.append(sensor("J4", 60, 120, "BL"))

components.append(dict(ref="J5", lib="Conn_01x04", at=(150, 45), value="HX711_LoadCell_Side",
                        pins=[("1", "EXC_POS"), ("2", "EXC_NEG"), ("3", "SIG_POS"), ("4", "SIG_NEG")],
                        footprint="Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical"))

components.append(dict(ref="J6", lib="Conn_01x04", at=(150, 105), value="HX711_Digital_Side",
                        pins=[("1", "GND"), ("2", "DT"), ("3", "SCK"), ("4", "VCC_3V3")],
                        footprint="Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical"))

components.append(dict(ref="J7", lib="Conn_01x04", at=(240, 75), value="RJ11_to_Hub",
                        pins=[("1", "GND"), ("2", "VCC_3V3"), ("3", "SCK"), ("4", "DT")],
                        footprint=""))

# --- Build symbol instances + wires + labels ------------------------------

def indent(s, n):
    pad = "\t" * n
    return "\n".join(pad + line if line.strip() else line for line in s.split("\n"))

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

def sym_instance(ref, lib, x, y, value, footprint):
    u = new_uuid()
    pins_block = ""
    npins = 3 if lib == "Conn_01x03" else 4
    pin_uuids = []
    for i in range(1, npins + 1):
        pu = new_uuid()
        pin_uuids.append(pu)
        pins_block += f'\t\t(pin "{i}"\n\t\t\t(uuid "{pu}")\n\t\t)\n'
    ref_prop = prop("Reference", ref, x, y - 10, 0)
    val_prop = prop("Value", value, x, y + (10 if lib == "Conn_01x03" else 13), 0)
    fp_prop = prop("Footprint", footprint, x, y, 0, hide=True)
    ds_prop = prop("Datasheet", "~", x, y, 0, hide=True)
    block = f'''\t(symbol
\t\t(lib_id "Connector_Generic:{lib}")
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
    return block

def wire_and_label(px, py, net, pin_dx_sign=-1):
    # stub extends further in -X from the pin connection point
    ex = px + pin_dx_sign * STUB
    ey = py
    wu = new_uuid()
    lu = new_uuid()
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
\t\t\t(justify right)
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
    x, y = snap(c["at"][0]), snap(c["at"][1])
    symbol_blocks.append(sym_instance(c["ref"], c["lib"], x, y, c["value"], c["footprint"]))
    pin_dy_start = 2.54  # pin 1 offset from symbol origin, per library def
    for num, net in c["pins"]:
        dy = pin_dy_start - (int(num) - 1) * 2.54
        px = x + PIN_DX
        # KiCad negates the symbol-local Y axis when placing at rotation 0
        # (lib editor is Y-up, schematic sheet is Y-down) - confirmed via ERC.
        py = y - dy
        w, l = wire_and_label(px, py, net)
        wire_blocks.append(w)
        label_blocks.append(l)

# Documentation text annotations (non-electrical)
add_text("Keg Sensor Module - carrier for HX711 breakout + 4x half-bridge sensors + RJ11 to hub", 20, 10, 2)
add_text("J1=FL J2=FR J3=BR J4=BL corner sensors.\\nDiagonal pairing: J1+J3 -> SIG_POS, J2+J4 -> SIG_NEG.\\nVerify against kit's wiring diagram - swap if reading is inverted/flat.", 20, 145, 1.27)
add_text("J6 pin order (GND,DT,SCK,VCC) is a common HX711 module layout -\\nCONFIRM against your specific module's silkscreen before wiring/routing.", 130, 130, 1.27)
add_text("J7 = RJ11 jack to in-keezer hub.\\nPin1=GND(Black) Pin2=VCC(Red) Pin3=SCK(Green) Pin4=DT(Yellow).\\nMust match hub-side RJ11 pin convention (wiring.md) for a straight-through cable.\\nFootprint intentionally left blank - assign to match your exact RJ11 jack part.", 220, 40, 1.27)

sch = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A3")
\t(title_block
\t\t(title "KegSensor")
\t\t(company "Sallaup Electronics")
\t\t(comment 1 "HX711 carrier + 4x half-bridge sensor terminals + RJ11 to hub")
\t\t(comment 2 "Part of the Sallaup KegSense keg-monitoring system")
\t)
\t(lib_symbols
{indent(conn3, 2)}
{indent(conn4, 2)}
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
