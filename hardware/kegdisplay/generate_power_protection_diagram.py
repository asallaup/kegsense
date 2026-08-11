import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

OUT = pathlib.Path(__file__).resolve().parent / "power_protection.png"

fig, ax = plt.subplots(figsize=(12, 7))
ax.set_xlim(0, 100)
ax.set_ylim(0, 60)
ax.axis("off")

def wire(x1, y1, x2, y2, lw=1.8, color="#222222", zorder=2):
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, zorder=zorder, solid_capstyle="round")

def dot(x, y, r=0.55, color="#222222"):
    ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor=color, zorder=5))

def label(x, y, text, fontsize=10, ha="center", va="center", weight="normal", color="#111111"):
    ax.text(x, y, text, fontsize=fontsize, ha=ha, va=va, fontweight=weight, color=color, zorder=6)

SRC_Y, GATE_Y, GND_Y, DRAIN_Y = 50, 35, 10, 18

label(50, 57, "KegDisplay reverse-polarity protection (P-MOSFET high-side)", fontsize=13, weight="bold")
label(50, 53.5, "Placed in the +V line, right where the RJ12 chain power enters the board", fontsize=9, color="#555555")

# ---- input terminals ----
dot(8, SRC_Y)
label(8, SRC_Y + 3.5, "V+ IN\n(RJ12 cable pin)", fontsize=8.5, color="#8a1a1a", weight="bold")
dot(8, GND_Y)
label(8, GND_Y - 3.5, "GND IN\n(RJ12 cable pin)", fontsize=8.5, weight="bold")

# ---- rails ----
wire(8, SRC_Y, 58, SRC_Y)     # Source / V+IN rail
wire(8, GND_Y, 85, GND_Y)     # common ground rail (full width)
wire(30, GATE_Y, 44, GATE_Y)  # gate rail (R1/D1 junction to MOSFET gate)

# ---- R1: gate PULL-DOWN to GND (not to Source!) - this is what makes
# the protection work. Gate then tracks the board's GND reference, so
# when the cable is reversed and "GND IN" ends up carrying the actual
# +V, Gate sits above Source and the P-MOSFET turns off. A gate tied to
# Source instead would give ~0V Vgs and never turn on at all - wrong;
# this was a real mistake in an earlier draft, caught by working through
# the correct-vs-reversed cases explicitly rather than trusting it.
ax.add_patch(FancyBboxPatch((27, GND_Y), 6, GATE_Y - GND_Y, boxstyle="round,pad=0.15",
                             linewidth=1.6, edgecolor="#555555", facecolor="#ffffff", zorder=3))
label(37, (GATE_Y + GND_Y) / 2, "R1\n10k Ω", fontsize=8.5, weight="bold", ha="left")
dot(30, GATE_Y)
dot(30, GND_Y)

# ---- D1: optional zener, Gate-to-Source - clamps Vgs directly (the
# parameter that actually needs protecting from an overvoltage fault),
# so it spans Source rail -> Gate rail, not Gate -> GND.
ax.add_patch(FancyBboxPatch((27, GATE_Y + 2), 6, SRC_Y - GATE_Y - 2, boxstyle="round,pad=0.15",
                             linewidth=1.4, edgecolor="#7a5200", facecolor="#fff7e6", zorder=3,
                             linestyle=(0, (2, 1))))
label(37, (SRC_Y + GATE_Y) / 2, "D1 (optional)\n15V zener, G→S clamp", fontsize=7.8, color="#7a5200", ha="left")
wire(30, SRC_Y, 30, GATE_Y + 2)
wire(30, GATE_Y, 30, GATE_Y + 2)
dot(30, SRC_Y)

# ---- Q1: P-channel MOSFET, drawn with explicit external pin stubs ----
qx, qy, qw, qh = 50, 25, 16, 20
ax.add_patch(FancyBboxPatch((qx, qy), qw, qh, boxstyle="round,pad=0.3",
                             linewidth=1.8, edgecolor="#1a3d8f", facecolor="#eaf0fb", zorder=3))
label(qx + qw/2, qy + qh + 3, "Q1: P-channel MOSFET", fontsize=9.5, weight="bold", color="#1a3d8f")
label(qx + qw/2, qy + qh - 4, "S", fontsize=10, weight="bold")
label(qx + qw/2, qy + 4, "D", fontsize=10, weight="bold")
label(qx + 3.5, qy + qh/2, "G", fontsize=10, weight="bold")

# S pin stub: top of box up to source rail
wire(qx + qw/2, qy + qh, qx + qw/2, SRC_Y)
dot(qx + qw/2, SRC_Y)
wire(qx + qw/2, SRC_Y, 58, SRC_Y)

# G pin stub: left of box to gate rail
wire(qx, qy + qh/2, 44, qy + qh/2)
wire(44, qy + qh/2, 44, GATE_Y)
dot(44, GATE_Y)

# D pin stub: bottom of box down to drain/output rail
wire(qx + qw/2, qy, qx + qw/2, DRAIN_Y)
dot(qx + qw/2, DRAIN_Y)
wire(qx + qw/2, DRAIN_Y, 75, DRAIN_Y)
label(66, DRAIN_Y + 2.5, "V+ protected", fontsize=9, weight="bold", color="#1a7a34")

# ---- output block ----
ox, oy, ow, oh = 75, 8, 18, 22
ax.add_patch(FancyBboxPatch((ox, oy), ow, oh, boxstyle="round,pad=0.3",
                             linewidth=1.8, edgecolor="#1a7a34", facecolor="#e8f6ec", zorder=3))
label(ox + ow/2, oy + oh/2, "Nano VIN\n(on-board reg.\nfeeds OLED /\nMAX485)", fontsize=7.6, color="#1a7a34")
dot(ox, GND_Y)
wire(ox, GND_Y, ox, oy)  # ground tie into bottom of output block

label(46, GND_Y - 3.5, "common GND rail (board ground, tied to RJ12's GND IN)", fontsize=8, color="#555555")

plt.tight_layout()
plt.savefig(OUT, dpi=160)
print("wrote", OUT)
