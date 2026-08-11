import re, uuid, math, pathlib

KICAD_SHARE = pathlib.Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport")
SYM_DIR = KICAD_SHARE / "symbols"
OUT_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_NAME = "keg_display_module"
SCH_PATH = OUT_DIR / f"{PROJECT_NAME}.kicad_sch"

# --- library extraction helpers -------------------------------------------

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


def get_block(lib_file, symbol_name):
    text = (SYM_DIR / lib_file).read_text()
    idx = text.index(f'(symbol "{symbol_name}"')
    return extract_balanced(text, idx)


def qualify(block, bare_name, qualified_name):
    # The lib_id used by a symbol instance must exactly match the top-level
    # name of its lib_symbols block, or KiCad fails to resolve it (this was
    # the cause of an ERC crash - only the top-level name needs qualifying,
    # nested "<name>_0_1"/"<name>_1_1" unit-body names stay as-is).
    new_block = block.replace(f'(symbol "{bare_name}"', f'(symbol "{qualified_name}"', 1)
    assert new_block != block, f"qualify: {bare_name!r} not found"
    return new_block


def pin_blocks(block):
    out, i = [], 0
    while True:
        j = block.find('(pin ', i)
        if j == -1:
            break
        pb = extract_balanced(block, j)
        out.append(pb)
        i = j + len(pb)
    return out


def parse_pins(block):
    """Return list of dict(number, name, x, y, angle, etype) for a *_1_1 (or _0_0) unit body."""
    pins = []
    for pb in pin_blocks(block):
        etype = pb.split()[1]
        at = re.search(r'\(at ([\-0-9.]+) ([\-0-9.]+) (\d+)\)', pb)
        name = re.search(r'\(name "([^"]*)"', pb)
        number = re.search(r'\(number "([^"]*)"', pb)
        pins.append(dict(
            number=number.group(1), name=name.group(1) if name else "~",
            x=float(at.group(1)), y=float(at.group(2)), angle=int(at.group(3)),
            etype=etype,
        ))
    return pins

# --- flatten the specific library symbols we need into self-contained blocks ---
# (some stock KiCad symbols use `extends`, which our raw-text embedding approach
#  can't resolve at load time - so we flatten each one to its base geometry here,
#  same trick used in kegsensor/generate_schematic.py for Connector_Generic parts.)

conn4 = qualify(get_block("Connector_Generic.kicad_sym", "Conn_01x04"), "Conn_01x04", "Connector_Generic:Conn_01x04")
conn6 = qualify(get_block("Connector_Generic.kicad_sym", "Conn_01x06"), "Conn_01x06", "Connector_Generic:Conn_01x06")
dev_r = qualify(get_block("Device.kicad_sym", "R"), "R", "Device:R")
dev_led = qualify(get_block("Device.kicad_sym", "LED"), "LED", "Device:LED")
dev_zener = qualify(get_block("Device.kicad_sym", "D_Zener"), "D_Zener", "Device:D_Zener")
pwr_flag = qualify(get_block("power.kicad_sym", "PWR_FLAG"), "PWR_FLAG", "power:PWR_FLAG")

# Nano: Arduino_Nano_v2.x is self-contained (no `extends`), footprint = Module:Arduino_Nano
nano_block = qualify(get_block("MCU_Module.kicad_sym", "Arduino_Nano_v2.x"),
                      "Arduino_Nano_v2.x", "MCU_Module:Arduino_Nano_v2.x")

# MAX485: MAX485E -> extends MAX481E -> extends LTC2850xS8 (the actual base, self-contained).
# Pinout (DIP-8/SOIC-8): 1=RO 2=~RE 3=DE 4=DI 5=GND 6=A 7=B 8=VCC - same for MAX485/481/491 family.
max485_base = get_block("Interface_UART.kicad_sym", "LTC2850xS8")
max485_base = qualify(max485_base, "LTC2850xS8", "Interface_UART:MAX485")
max485_base = max485_base.replace('"LTC2850xS8_0_1"', '"MAX485_0_1"', 1)
max485_base = max485_base.replace('"LTC2850xS8_1_1"', '"MAX485_1_1"', 1)
max485_base = re.sub(r'\(property "Value" "LTC2850xS8"', '(property "Value" "MAX485"', max485_base)
max485_base = re.sub(
    r'\(property "Footprint" "[^"]*"',
    '(property "Footprint" "Package_DIP:DIP-8_W7.62mm"',
    max485_base, count=1,
)

# Q1: AO3401A -> extends TP0610T (the actual base, self-contained). Same SOT-23 P-MOSFET
# pinout (1=G 2=S 3=D), AO3401A just has a beefier current/voltage rating - swap in its
# real part name/datasheet/footprint since that's the part actually going on the BOM.
q_base = get_block("Transistor_FET.kicad_sym", "TP0610T")
q_base = qualify(q_base, "TP0610T", "Transistor_FET:AO3401A")
q_base = q_base.replace('"TP0610T_0_1"', '"AO3401A_0_1"', 1)
q_base = q_base.replace('"TP0610T_1_1"', '"AO3401A_1_1"', 1)
q_base = re.sub(r'\(property "Value" "TP0610T"', '(property "Value" "AO3401A"', q_base)
q_base = re.sub(
    r'\(property "Datasheet" "[^"]*"',
    '(property "Datasheet" "http://www.aosmd.com/pdfs/datasheet/AO3401A.pdf"',
    q_base, count=1,
)

LIB_SYMBOLS = [conn4, conn6, dev_r, dev_led, dev_zener, pwr_flag, nano_block, max485_base, q_base]

NANO_PINS = {p["number"]: p for p in parse_pins(nano_block)}
MAX485_PINS = {p["number"]: p for p in parse_pins(max485_base)}
Q_PINS = {p["number"]: p for p in parse_pins(q_base)}
R_PINS = {p["number"]: p for p in parse_pins(dev_r)}
LED_PINS = {p["number"]: p for p in parse_pins(dev_led)}
ZENER_PINS = {p["number"]: p for p in parse_pins(dev_zener)}
FLAG_PINS = {p["number"]: p for p in parse_pins(pwr_flag)}


CONN4_PINS = {p["number"]: p for p in parse_pins(conn4)}
CONN6_PINS = {p["number"]: p for p in parse_pins(conn6)}

# --- net / component plan --------------------------------------------------
#
# J1, J2: RJ12 (6P6C) daisy-chain jacks, wired in parallel per the KegDisplay
# README pin convention: 1=A 2=B 3=GND 4=+V(raw) 5=ENABLE(per-jack, NOT bussed
# between J1/J2 - that's the whole point of chain-position auto-addressing)
# 6=spare (bussed through, unused on this board).
#
# Q1/R1/D1: P-MOSFET high-side reverse-polarity protection (see
# power_protection.png) sitting between the raw +V bus and the Nano's VIN.
#
# U2 (Nano): VIN<-V_PROT, GND, +5V->PWR5V (feeds OLED + MAX485), A4/A5->I2C,
# D0/D1<->MAX485 RO/DI, D2->MAX485 DE+RE tied together, D3/D4->ENABLE_A/B
# (per-jack GPIO, auto-detect scheme - see README "Addressing"), D5/D6->
# status LED (yellow/green) through current-limit resistors.
#
# U1 (MAX485): RS-485 transceiver, A/B bussed straight to both RJ12 jacks.
# R_TERM: 120 ohm termination, DNP by default - only the physical first/last
# board in the chain gets it populated (see README "Termination").
#
# J3: OLED module header (SSD1306, I2C) - GND/VCC/SCL/SDA, generic 4-pin
# header like kegsensor's HX711 headers; confirm against the exact module's
# silkscreen order before wiring, same caveat as kegsensor's J6.
# R_SDA/R_SCL: I2C pull-ups - many SSD1306 modules already carry their own,
# so these may end up redundant (harmless) rather than load-bearing; verify
# against the specific module once it's in hand.

components = []


def add(ref, kind, x, y, value, footprint, pinmap, netmap, angle=0, dnp=False):
    components.append(dict(ref=ref, kind=kind, at=(x, y), value=value, footprint=footprint,
                            pinmap=pinmap, netmap=netmap, angle=angle, dnp=dnp))


# RJ12 jacks
add("J1", "Conn_01x06", 25, 60, "RJ12_to_chain (either direction)",
    "Connector_RJ:RJ12_Amphenol_54601-x06_Horizontal", CONN6_PINS,
    {"1": "RS485_A", "2": "RS485_B", "3": "GND", "4": "VBUS_RAW", "5": "ENABLE_A", "6": "SPARE_BUS"})

add("J2", "Conn_01x06", 25, 190, "RJ12_to_chain (either direction)",
    "Connector_RJ:RJ12_Amphenol_54601-x06_Horizontal", CONN6_PINS,
    {"1": "RS485_A", "2": "RS485_B", "3": "GND", "4": "VBUS_RAW", "5": "ENABLE_B", "6": "SPARE_BUS"})

# Reverse-polarity protection (see power_protection.png)
add("Q1", "AO3401A", 70, 125, "AO3401A", "Package_TO_SOT_SMD:SOT-23", Q_PINS,
    {"1": "GATE", "2": "VBUS_RAW", "3": "V_PROT"})
add("R1", "R", 55, 145, "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", R_PINS,
    {"1": "GATE", "2": "GND"}, angle=90)
add("D1", "D_Zener", 90, 145, "5.1V (optional Vgs clamp, DNP by default)",
    "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", ZENER_PINS,
    {"1": "VBUS_RAW", "2": "GATE"}, dnp=True)

# Arduino Nano (socketed - see README)
add("U2", "Arduino_Nano_v2.x", 180, 110, "Arduino Nano (socketed, not soldered)",
    "Module:Arduino_Nano", NANO_PINS,
    {"1": "MAX485_DI", "2": "MAX485_RO", "3": "NC", "4": "GND", "5": "MAX485_DERE",
     "6": "ENABLE_A", "7": "ENABLE_B", "8": "LEDY_CTRL", "9": "LEDG_CTRL",
     "10": "NC", "11": "NC", "12": "NC", "13": "NC", "14": "NC", "15": "NC", "16": "NC",
     "17": "NC", "18": "NC", "19": "NC", "20": "NC", "21": "NC", "22": "NC",
     "23": "I2C_SDA", "24": "I2C_SCL", "25": "NC", "26": "NC",
     "27": "PWR5V", "28": "NC", "29": "GND", "30": "V_PROT"})

# RS-485 transceiver
add("U1", "MAX485", 280, 100, "MAX485", "Package_DIP:DIP-8_W7.62mm", MAX485_PINS,
    {"1": "MAX485_RO", "2": "MAX485_DERE", "3": "MAX485_DERE", "4": "MAX485_DI",
     "5": "GND", "6": "RS485_A", "7": "RS485_B", "8": "PWR5V"})

add("R_TERM", "R", 300, 130, "120R (populate only on the chain's first/last board)",
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", R_PINS,
    {"1": "RS485_A", "2": "RS485_B"}, angle=90, dnp=True)

# Status LED (bi-color yellow/green = 2x LED sharing a GND cathode - see README)
add("R_LEDY", "R", 220, 45, "330R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    R_PINS, {"1": "LEDY_CTRL", "2": "LEDY_A"})
add("LED_Y", "LED", 245, 45, "Yellow (status)", "LED_THT:LED_D5.0mm", LED_PINS,
    {"1": "GND", "2": "LEDY_A"})
add("R_LEDG", "R", 220, 60, "330R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    R_PINS, {"1": "LEDG_CTRL", "2": "LEDG_A"})
add("LED_G", "LED", 245, 60, "Green (status)", "LED_THT:LED_D5.0mm", LED_PINS,
    {"1": "GND", "2": "LEDG_A"})

# OLED module header (0.96" SSD1306, I2C - confirm pin order against the real module)
add("J3", "Conn_01x04", 180, 190, "OLED_SSD1306_I2C (confirm pin order against module silkscreen)",
    "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", CONN4_PINS,
    {"1": "GND", "2": "PWR5V", "3": "I2C_SCL", "4": "I2C_SDA"})
add("R_SDA", "R", 210, 175, "4.7k (I2C pull-up - many SSD1306 modules already have one, verify)",
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", R_PINS,
    {"1": "I2C_SDA", "2": "PWR5V"}, angle=90)
add("R_SCL", "R", 225, 175, "4.7k (I2C pull-up - many SSD1306 modules already have one, verify)",
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", R_PINS,
    {"1": "I2C_SCL", "2": "PWR5V"}, angle=90)

# Power flags: GND and V_PROT are only ever driven by passive-typed pins on
# this sheet (connector pins, MOSFET drain) - ERC needs an explicit marker
# that they're legitimately externally-powered nets, not undriven ones.
add("#FLG_GND", "PWR_FLAG", 40, 230, "PWR_FLAG", "", FLAG_PINS, {"1": "GND"})
add("#FLG_VPROT", "PWR_FLAG", 100, 90, "PWR_FLAG", "", FLAG_PINS, {"1": "V_PROT"})

# --- schematic text generation ---------------------------------------------

GRID = 1.27
STUB = 2.54


def snap(v):
    return round(round(v / GRID) * GRID, 2)


def new_uuid():
    return str(uuid.uuid4())


ROOT_UUID = new_uuid()


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


def lib_id_for(kind):
    return {
        "Conn_01x04": "Connector_Generic:Conn_01x04",
        "Conn_01x06": "Connector_Generic:Conn_01x06",
        "R": "Device:R",
        "LED": "Device:LED",
        "D_Zener": "Device:D_Zener",
        "PWR_FLAG": "power:PWR_FLAG",
        "Arduino_Nano_v2.x": "MCU_Module:Arduino_Nano_v2.x",
        "MAX485": "Interface_UART:MAX485",
        "AO3401A": "Transistor_FET:AO3401A",
    }[kind]


symbol_blocks, wire_blocks, label_blocks, text_blocks, noconn_blocks = [], [], [], [], []


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


def sym_instance(c, x, y):
    ref, kind, value, footprint = c["ref"], c["kind"], c["value"], c["footprint"]
    lib_id = lib_id_for(kind)
    u = new_uuid()
    pins_block = ""
    for num in c["pinmap"]:
        pu = new_uuid()
        pins_block += f'\t\t(pin "{num}"\n\t\t\t(uuid "{pu}")\n\t\t)\n'
    ref_prop = prop("Reference", ref, x, y - 12, 0)
    val_prop = prop("Value", value, x, y + 12, 0)
    fp_prop = prop("Footprint", footprint, x, y, 0, hide=True)
    ds_prop = prop("Datasheet", "~", x, y, 0, hide=True)
    dnp_s = "\n\t\t(dnp yes)" if c.get("dnp") else "\n\t\t(dnp no)"
    block = f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {c.get("angle", 0)})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes){dnp_s}
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


def wire_and_label(px, py, net):
    lu = new_uuid()
    label = f'''\t(label "{net}"
\t\t(at {px} {py} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t)
\t\t(uuid "{lu}")
\t)'''
    return label


for c in components:
    x, y = snap(c["at"][0]), snap(c["at"][1])
    symbol_blocks.append(sym_instance(c, x, y))

PINGEO = {
    "Conn_01x04": CONN4_PINS, "Conn_01x06": CONN6_PINS, "R": R_PINS, "LED": LED_PINS,
    "D_Zener": ZENER_PINS, "PWR_FLAG": FLAG_PINS, "Arduino_Nano_v2.x": NANO_PINS,
    "MAX485": MAX485_PINS, "AO3401A": Q_PINS,
}

for c in components:
    x, y = snap(c["at"][0]), snap(c["at"][1])
    geo = PINGEO[c["kind"]]
    inst_angle = math.radians(c.get("angle", 0))
    ca, sa = round(math.cos(inst_angle)), round(math.sin(inst_angle))
    for num, net in c["netmap"].items():
        if net == "NC":
            continue
        p = geo[num]
        # rotate the pin's local offset by the instance's own placement angle
        lx, ly = p["x"], p["y"]
        rx = lx * ca - ly * sa
        ry = lx * sa + ly * ca
        px = x + rx
        py = y - ry  # lib editor is Y-up, schematic sheet is Y-down
        pin_angle = math.radians((p["angle"] + c.get("angle", 0)) % 360)
        ex = px - STUB * round(math.cos(pin_angle))
        ey = py + STUB * round(math.sin(pin_angle))
        wu = new_uuid()
        wire_blocks.append(f'''\t(wire
\t\t(pts
\t\t\t(xy {px} {py}) (xy {ex} {ey})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{wu}")
\t)''')
        label_blocks.append(wire_and_label(ex, ey, net))

    for num in c["pinmap"]:
        if c["netmap"].get(num) == "NC":
            p = geo[num]
            lx, ly = p["x"], p["y"]
            rx = lx * ca - ly * sa
            ry = lx * sa + ly * ca
            px, py = x + rx, y - ry
            nu = new_uuid()
            noconn_blocks.append(f'''\t(no_connect
\t\t(at {px} {py})
\t\t(uuid "{nu}")
\t)''')

add_text("KegDisplay - Arduino Nano + SSD1306 OLED, RS-485 (MAX485) daisy-chained\\n"
         "back to KegStation over RJ12. One board per keg, mounted at/over its tap.",
         20, 15, 2)
add_text("J1/J2 = RJ12 (6P6C) daisy-chain jacks, wired in parallel except ENABLE\\n"
         "(not bussed - each jack's ENABLE goes to its own Nano GPIO, see README\\n"
         "'Addressing': auto-detecting enable, either jack can be upstream).\\n"
         "Pin order (this project's own convention, not a telecom standard):\\n"
         "1=A 2=B 3=GND 4=+V(raw) 5=ENABLE 6=spare.", 20, 220, 1.27)
add_text("Q1/R1/D1 = reverse-polarity protection for this board's own +V draw\\n"
         "only (VBUS_RAW keeps passing raw/unprotected between J1<->J2 for the\\n"
         "rest of the chain). See power_protection.png for the full explanation.",
         20, 100, 1.27)
add_text("D1 is optional (Vgs clamp) - DNP by default, populate only if needed.\\n"
         "R_TERM (120R) is DNP by default too - only the physical first and last\\n"
         "board in the installed chain should have it populated, see README\\n"
         "'Termination'.", 260, 155, 1.27)
add_text("J3 = OLED module header, pin order GND/VCC/SCL/SDA - this is a common\\n"
         "layout for 0.96in SSD1306 I2C modules but CONFIRM against your exact\\n"
         "module's silkscreen before wiring, same caveat as kegsensor's J6.",
         160, 215, 1.27)
add_text("Status LED = bi-color yellow/green sharing a GND cathode, drawn as two\\n"
         "discrete LEDs (electrically identical to a 3-lead common-cathode part).\\n"
         "Yellow=powered/unaddressed, Green=addressed+polled, blinking green=\\n"
         "missed heartbeat. See README 'Status LED'.", 200, 20, 1.27)

sch = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A3")
\t(title_block
\t\t(title "KegDisplay")
\t\t(company "Sallaup Electronics")
\t\t(comment 1 "Arduino Nano + SSD1306 OLED carrier, RS-485 (MAX485) daisy-chain to KegStation")
\t\t(comment 2 "Part of the Sallaup KegSense keg-monitoring system")
\t)
\t(lib_symbols
{indent(chr(10).join(LIB_SYMBOLS), 2)}
\t)
{chr(10).join(symbol_blocks)}
{chr(10).join(wire_blocks)}
{chr(10).join(label_blocks)}
{chr(10).join(noconn_blocks)}
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
