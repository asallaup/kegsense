import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = pathlib.Path(__file__).resolve().parent / "wiring_diagram.png"

fig, ax = plt.subplots(figsize=(22, 9.5))
ax.set_xlim(0, 225)
ax.set_ylim(0, 95)
ax.axis("off")

WIRE = {"Red": "#d1332e", "Black": "#1a1a1a", "White": "#999999",
        "Green": "#2e8b3d", "Yellow": "#c9a300"}

def box(x, y, w, h, label, fc="#f4f4f4", ec="#333333", fontsize=10, weight="bold", lw=1.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3",
                                 linewidth=lw, edgecolor=ec, facecolor=fc, zorder=3))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, fontweight=weight, color="#111111", zorder=4)

def pin_box(x, y, w, h, title, pins, fc="#ffffff", ec="#555555"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25",
                                 linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=3))
    ax.text(x + w / 2, y + h + 1.8, title, ha="center", fontsize=9.5, fontweight="bold", color=ec, zorder=4)
    n = len(pins)
    ys = []
    # fontsize=11, bold - was 7/normal, easy to lose (e.g. A+/A- on J5) once
    # the image is scaled down to a typical inline viewing size, not just at
    # full resolution.
    for i, p in enumerate(pins):
        py = y + h - (i + 0.5) * (h / n)
        ys.append(py)
        ax.text(x + w / 2, py, p, ha="center", va="center", fontsize=11, fontweight="bold", zorder=4)
    return ys

# ============ 4 sensors ============
sensors = [("Sensor – FL corner", 78, "J1"), ("Sensor – BR corner", 58, "J3"),
           ("Sensor – FR corner", 38, "J2"), ("Sensor – BL corner", 18, "J4")]

pcb_x0, pcb_y0, pcb_w, pcb_h = 46, 6, 60, 80
ax.add_patch(FancyBboxPatch((pcb_x0, pcb_y0), pcb_w, pcb_h, boxstyle="round,pad=0.4",
                             linewidth=2, edgecolor="#2b4c7e", facecolor="#eef3fb", zorder=1))
ax.text(pcb_x0 + pcb_w / 2, pcb_y0 + pcb_h + 2.4, "KegSensor carrier PCB",
        ha="center", fontsize=13, fontweight="bold", color="#2b4c7e", zorder=4)

term_x, term_w = pcb_x0 + 4, 15
for label, ycenter, ref in sensors:
    sy = ycenter
    box(4, sy - 6, 26, 12, label, fc="#fff7e6", ec="#8a6d00", fontsize=9)
    box(term_x, sy - 6, term_w, 12, f"{ref}\nE+  E-  Sig", fc="#ffffff", ec="#555555", fontsize=7.5, weight="normal")
    ax.plot([30, term_x], [sy + 3.2, sy + 3.2], color=WIRE["Red"], linewidth=2, zorder=2)
    ax.plot([30, term_x], [sy, sy], color=WIRE["Black"], linewidth=2, zorder=2)
    ax.plot([30, term_x], [sy - 3.2, sy - 3.2], color=WIRE["White"], linewidth=2, zorder=2)

ax.text(17, 90, "4x half-bridge load cell sensors\n(one per keg-platform corner)",
        ha="center", fontsize=9.5, color="#8a6d00")

# ============ bus: J1-J4 -> J5 ============
j5_x, j5_y, j5_w, j5_h = pcb_x0 + 32, 40, 11, 20
j5_ys = pin_box(j5_x, j5_y, j5_w, j5_h, "J5", ["E+", "E-", "A+", "A-"])

bx1, bx2, bx3, bx4 = term_x + term_w + 2, term_x + term_w + 4.2, term_x + term_w + 6.4, term_x + term_w + 8.6
for label, ycenter, ref in sensors:
    ax.plot([term_x + term_w, bx1], [ycenter + 3.2, ycenter + 3.2], color=WIRE["Red"], linewidth=1.4, zorder=2)
    ax.plot([term_x + term_w, bx2], [ycenter, ycenter], color=WIRE["Black"], linewidth=1.4, zorder=2)
ax.plot([bx1, bx1], [15, 81], color=WIRE["Red"], linewidth=1.4, zorder=2)
ax.plot([bx1, j5_x], [j5_ys[0], j5_ys[0]], color=WIRE["Red"], linewidth=1.4, zorder=2)
ax.plot([bx2, bx2], [15, 81], color=WIRE["Black"], linewidth=1.4, zorder=2)
ax.plot([bx2, j5_x], [j5_ys[1], j5_ys[1]], color=WIRE["Black"], linewidth=1.4, zorder=2)

ax.plot([term_x + term_w, bx3], [78 - 3.2, 78 - 3.2], color=WIRE["White"], linewidth=1.4, zorder=2)
ax.plot([term_x + term_w, bx3], [58 - 3.2, 58 - 3.2], color=WIRE["White"], linewidth=1.4, zorder=2)
ax.plot([bx3, bx3], [58 - 3.2, 78 - 3.2], color=WIRE["White"], linewidth=1.4, zorder=2)
ax.plot([bx3, j5_x], [j5_ys[2], j5_ys[2]], color=WIRE["White"], linewidth=1.4, zorder=2)
ax.plot([term_x + term_w, bx4], [38 - 3.2, 38 - 3.2], color=WIRE["White"], linewidth=1.4, linestyle=(0, (4, 2)), zorder=2)
ax.plot([term_x + term_w, bx4], [18 - 3.2, 18 - 3.2], color=WIRE["White"], linewidth=1.4, linestyle=(0, (4, 2)), zorder=2)
ax.plot([bx4, bx4], [18 - 3.2, 38 - 3.2], color=WIRE["White"], linewidth=1.4, linestyle=(0, (4, 2)), zorder=2)
ax.plot([bx4, j5_x], [j5_ys[3], j5_ys[3]], color=WIRE["White"], linewidth=1.4, linestyle=(0, (4, 2)), zorder=2)

# caption INSIDE the pcb box, under the title, above the J1 row - avoids overlapping the title
ax.text(pcb_x0 + pcb_w / 2, 85.5, "EXC_POS / EXC_NEG bus all 4 sensors  •  SIG_POS = J1+J3 (solid)  •  SIG_NEG = J2+J4 (dashed)",
        ha="center", fontsize=7.3, color="#444444", zorder=4)

# ============ HX711 module ============
hx_x, hx_y, hx_w, hx_h = j5_x + 16, 35, 26, 30
box(hx_x, hx_y, hx_w, hx_h, "HX711\nbreakout\nmodule", fc="#e8f6ec", ec="#1a7a34", fontsize=9.5)
for py in j5_ys:
    ax.plot([j5_x + j5_w, hx_x], [py, hx_y + hx_h * 0.7], color="#1a7a34", linewidth=0.8, zorder=1, alpha=0.6)

j6_x, j6_y, j6_w, j6_h = hx_x + hx_w + 16, 40, 11, 20
j6_ys = pin_box(j6_x, j6_y, j6_w, j6_h, "J6", ["GND", "DT", "SCK", "VCC"])
for py in j6_ys:
    ax.plot([hx_x + hx_w, j6_x], [hx_y + hx_h * 0.3, py], color="#1a7a34", linewidth=0.8, zorder=1, alpha=0.6)
ax.text(hx_x + hx_w / 2, hx_y - 3, "(HX711 plugs into J5 for analog leads, J6 for digital/power)",
        ha="center", fontsize=7.5, color="#1a7a34")

# ============ J7 RJ11 jack ============
j7_x, j7_y, j7_w, j7_h = j6_x + j6_w + 14, 40, 11, 20
j7_ys = pin_box(j7_x, j7_y, j7_w, j7_h, "J7  (RJ11, RJ14 6P4C)", ["GND", "VCC", "SCK", "DT"])

pin_color = {"GND": WIRE["Black"], "VCC": WIRE["Red"], "SCK": WIRE["Green"], "DT": WIRE["Yellow"]}
j6_pins = ["GND", "DT", "SCK", "VCC"]
j7_pins = ["GND", "VCC", "SCK", "DT"]
for i, p in enumerate(j6_pins):
    y6 = j6_ys[i]
    y7 = j7_ys[j7_pins.index(p)]
    ax.plot([j6_x + j6_w, j7_x], [y6, y7], color=pin_color[p], linewidth=1.8, zorder=2)

# ============ RJ11 cable -> KegHub ============
hub_x, hub_y, hub_w, hub_h = 204, 30, 16, 40
box(hub_x, hub_y, hub_w, hub_h, "KegHub", fc="#f0eefc", ec="#4b2e91", fontsize=12)

cable_x = j7_x + j7_w + 10
cable_rows = [("Black", "GND"), ("Red", "VCC (3.3V, in)"), ("Green", "SCK (in, shared)"), ("Yellow", "DT (out, unique per keg)")]
cable_ys_from = [j7_ys[j7_pins.index("GND")], j7_ys[j7_pins.index("VCC")], j7_ys[j7_pins.index("SCK")], j7_ys[j7_pins.index("DT")]]
spread_ys = [j7_y + j7_h - (i + 0.5) * (j7_h / 4) for i in range(4)]
for (cname, sig), y7, ys in zip(cable_rows, cable_ys_from, spread_ys):
    ax.plot([j7_x + j7_w, cable_x], [y7, ys], color=WIRE[cname], linewidth=1.4, zorder=2)
    ax.plot([cable_x, hub_x], [ys, ys], color=WIRE[cname], linewidth=2.2, zorder=2)
    ax.text((cable_x + hub_x) / 2, ys + 1.3, f"{cname} = {sig}",
            ha="center", fontsize=7.3, color=WIRE[cname] if cname != "White" else "#777777", zorder=4)

ax.text((cable_x + hub_x) / 2, j7_y + j7_h + 4.5, "4-wire flat RJ11 cable\n(verify straight-through, not mirrored)",
        ha="center", fontsize=7.5, color="#444444")

fig.suptitle("KegSensor Wiring — Sallaup KegSense", fontsize=17, fontweight="bold", y=0.985)
ax.text(112, 1.5, "Sallaup Electronics  —  4x load cell  →  KegSensor PCB (J1–J4)  →  HX711 (J5/J6)  →  RJ11 (J7)  →  KegHub",
        ha="center", fontsize=9.5, color="#555555")

plt.tight_layout(rect=[0, 0.02, 1, 0.965])
plt.savefig(OUT, dpi=160)
print("wrote", OUT)
