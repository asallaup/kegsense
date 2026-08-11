import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

OUT = pathlib.Path(__file__).resolve().parent / "enable_wiring_options.png"

fig, ax = plt.subplots(figsize=(13, 8.6))
ax.set_xlim(0, 100)
ax.set_ylim(22, 100)
ax.axis("off")

def box(x, y, w, h, label, fc="#f4f4f4", ec="#333333", fontsize=9.5, weight="bold", lw=1.6, va="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3",
                                 linewidth=lw, edgecolor=ec, facecolor=fc, zorder=3))
    ax.text(x + w/2, y + h/2, label, ha="center", va=va, fontsize=fontsize, fontweight=weight,
            color="#111111", zorder=4)

def wire(x1, y1, x2, y2, color="#222222", lw=2, ls="-", zorder=2):
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, linestyle=ls, zorder=zorder, solid_capstyle="round")

def dot(x, y, r=0.7, color="#222222"):
    ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor=color, zorder=5))

def label(x, y, text, fontsize=9, ha="center", va="center", weight="normal", color="#111111"):
    ax.text(x, y, text, fontsize=fontsize, ha=ha, va=va, fontweight=weight, color=color, zorder=6)

RED = "#c0392b"
GREEN = "#1a7a34"

# =========================================================
# PANEL A (top half): fixed ENABLE_IN / ENABLE_OUT pins
# =========================================================
label(50, 97, "Option A: fixed ENABLE_IN / ENABLE_OUT pins", fontsize=13, weight="bold")
label(50, 93.5, "Cables accidentally swapped at install time", fontsize=9.5, color=RED)

# upstream cable (wrong: plugged into what the board wired as its OUT jack)
label(8, 82, "from\nKegStation\n(upstream)", fontsize=8, ha="center", color="#555555")
wire(15, 82, 30, 82, color=RED, lw=2.2, ls=(0, (5, 2)))
label(45, 84.5, "plugged into J2 by mistake", fontsize=7.5, color=RED)

# board A
box(30, 72, 30, 20, "", fc="#eef3fb", ec="#2b4c7e")
box(31.5, 86, 8, 5, "J1", fc="#ffffff", ec="#555555", fontsize=8)
box(50.5, 86, 8, 5, "J2", fc="#ffffff", ec="#555555", fontsize=8)
wire(35.5, 86, 35.5, 82.5, color="#333333")
wire(54.5, 86, 54.5, 82.5, color="#333333")
box(33, 74, 24, 7, "Nano\nENABLE_IN=J1 pin, ENABLE_OUT=J2 pin\n(fixed roles)", fc="#ffffff", ec="#1a3d8f", fontsize=6.8)
wire(35.5, 82.5, 35.5, 81, color="#333333")
wire(35.5, 81, 40, 81, color="#333333")
wire(54.5, 82.5, 54.5, 81, color="#333333")
wire(54.5, 81, 49, 81, color="#333333")

# the actual incoming (upstream) cable really lands on J2's wire, shown by rerouting the red dashed line to J2
wire(15, 82, 15, 88.5, color=RED, lw=2.2, ls=(0, (5, 2)))
wire(15, 88.5, 54.5, 88.5, color=RED, lw=2.2, ls=(0, (5, 2)))
wire(54.5, 88.5, 54.5, 86, color=RED, lw=2.2, ls=(0, (5, 2)))

# downstream cable, from J1 (which the board thinks is its input, but is now unused/misused)
wire(35.5, 86, 35.5, 90, color="#888888", lw=2, ls=(0, (5, 2)))
wire(35.5, 90, 70, 90, color="#888888", lw=2, ls=(0, (5, 2)))
label(80, 90, "to keg 2's\nboard", fontsize=8, color="#555555")

label(45, 69.5, "✗ ENABLE arrives on the ENABLE_OUT pin - board never sees it as\n\"I'm enabled,\" chain doesn't propagate past here",
      fontsize=8.3, color=RED, weight="bold")

# =========================================================
# PANEL B (bottom half): auto-detecting enable
# =========================================================
label(50, 58, "Option B: auto-detecting enable (either jack works)", fontsize=13, weight="bold")
label(50, 54.5, "Same cabling mistake - doesn't matter this time", fontsize=9.5, color=GREEN)

label(8, 43, "from\nKegStation\n(upstream)", fontsize=8, ha="center", color="#555555")
wire(15, 43, 15, 49.5, color=GREEN, lw=2.2, ls=(0, (5, 2)))
wire(15, 49.5, 54.5, 49.5, color=GREEN, lw=2.2, ls=(0, (5, 2)))
wire(54.5, 49.5, 54.5, 47, color=GREEN, lw=2.2, ls=(0, (5, 2)))
label(45, 45.5, "plugged into J2 - same \"mistake\" as above", fontsize=7.5, color=GREEN)

box(30, 33, 30, 20, "", fc="#eef3fb", ec="#2b4c7e")
box(31.5, 47, 8, 5, "J1", fc="#ffffff", ec="#555555", fontsize=8)
box(50.5, 47, 8, 5, "J2", fc="#ffffff", ec="#555555", fontsize=8)
wire(35.5, 47, 35.5, 43.5, color="#333333")
wire(54.5, 47, 54.5, 43.5, color="#333333")
box(33, 35, 24, 7.5, "Nano\nGPIO_A=J1 pin, GPIO_B=J2 pin (no fixed role)\nboot: whichever reads HIGH = upstream,\ndrive the OTHER one to enable next board",
    fc="#ffffff", ec="#1a3d8f", fontsize=6.5)

wire(35.5, 47, 35.5, 51, color="#888888", lw=2, ls=(0, (5, 2)))
wire(35.5, 51, 70, 51, color="#888888", lw=2, ls=(0, (5, 2)))
label(80, 51, "to keg 2's\nboard", fontsize=8, color="#555555")

label(45, 30.5, "✓ firmware sees GPIO_B already high at boot, treats J2 as upstream,\ndrives GPIO_A high to enable the next board via J1 - chain still works",
      fontsize=8.3, color=GREEN, weight="bold")

label(50, 24, "Sallaup Electronics — KegDisplay ENABLE wiring: fixed-pin vs. auto-detecting", fontsize=9, color="#555555")

plt.tight_layout()
plt.savefig(OUT, dpi=155)
print("wrote", OUT)
