import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = pathlib.Path(__file__).resolve().parent / "power_wiring_diagram.png"

fig, ax = plt.subplots(figsize=(18, 9))
ax.set_xlim(0, 172)
ax.set_ylim(0, 90)
ax.axis("off")

RED = "#d1332e"      # 5V
BLACK = "#1a1a1a"    # GND
BLUE = "#2b5fd9"     # 3.3V
ORANGE = "#c97a1a"   # data-only signal


def box(x, y, w, h, label, fc="#f4f4f4", ec="#333333", fontsize=11, weight="bold"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4",
                                 linewidth=1.8, edgecolor=ec, facecolor=fc, zorder=3))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, fontweight=weight, color="#111111", zorder=4)


def wire(x0, y0, x1, y1, color, label=None, lw=2.2, ls="-", label_dy=1.6, label_frac=0.5):
    ax.plot([x0, x1], [y0, y1], color=color, linewidth=lw, linestyle=ls, zorder=2)
    if label:
        lx = x0 + (x1 - x0) * label_frac
        ly = y0 + (y1 - y0) * label_frac
        ax.text(lx, ly + label_dy, label,
                 ha="center", fontsize=8.3, color=color, zorder=4,
                 bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85))


# ============ boxes ============
brick_x, brick_y, brick_w, brick_h = 4, 32, 20, 36
box(brick_x, brick_y, brick_w, brick_h,
    "Mean Well\nGST60A05-P1J\n5V, 6A, 30W\ncaptive DC cable,\nno PD negotiation",
    fc="#fdeceb", ec="#a32c26", fontsize=8.6)

bo_x, bo_y, bo_w, bo_h = 30, 40, 20, 20
box(bo_x, bo_y, bo_w, bo_h,
    "USB-C breakout\n(non-negotiating)\nsingle external\npower-entry connector",
    fc="#fdeceb", ec="#a32c26", fontsize=8.2)
wire(brick_x + brick_w, brick_y + brick_h * 0.65, bo_x, bo_y + bo_h * 0.7, RED, lw=2.2)
wire(brick_x + brick_w, brick_y + brick_h * 0.35, bo_x, bo_y + bo_h * 0.3, BLACK, lw=2.2)

pi_x, pi_y, pi_w, pi_h = 62, 34, 30, 40
box(pi_x, pi_y, pi_w, pi_h, "Raspberry Pi 4\n(KegStation)\n\n(onboard USB-C\nport unused)",
    fc="#eef3fb", ec="#2b4c7e", fontsize=12)

hub_x, hub_y, hub_w, hub_h = 136, 58, 32, 18
box(hub_x, hub_y, hub_w, hub_h,
    "KegHub →\n5× KegSensor bus\n(3.3V, tens of mA total)",
    fc="#f0eefc", ec="#4b2e91", fontsize=9.5)

disp_x, disp_y, disp_w, disp_h = 136, 12, 32, 18
box(disp_x, disp_y, disp_w, disp_h,
    "KegDisplay chain\n(5 taps, WS2812\ndaisy chain)",
    fc="#eafaf0", ec="#1a7a4a", fontsize=9.5)

# ============ breakout -> Pi GPIO 5V (star leg 1, bypasses onboard USB-C) ============
wire(bo_x + bo_w, bo_y + bo_h * 0.78, pi_x, pi_y + pi_h * 0.85, RED, "5V IN\n(to GPIO pin)", lw=2.6)
wire(bo_x + bo_w, bo_y + bo_h * 0.62, pi_x, pi_y + pi_h * 0.75, BLACK, "GND", lw=2.6)

# ============ Pi -> KegHub (3.3V logic bus, low current) ============
wire(pi_x + pi_w, pi_y + pi_h * 0.8, hub_x, hub_y + hub_h * 0.3, BLUE,
     "3.3V (Pi's own\nregulator)", lw=2.0)
wire(pi_x + pi_w, pi_y + pi_h * 0.68, hub_x, hub_y + hub_h * 0.15, BLACK, "GND", lw=1.6)

# ============ breakout -> J1 direct (star leg 2, own wire, not through the Pi),
# Pi -(3.3V DATA)-> level shifter -(5V DATA)-> J1: the one component
# external to the Pi that this design actually needs ============
j1_x, j1_y = disp_x - 16, disp_y + disp_h * 0.5
box(j1_x - 3, j1_y - 6, 10, 12, "J1", fc="#ffffff", ec="#555555", fontsize=8.5)

ls_x, ls_y, ls_w, ls_h = 94, 40, 22, 16
box(ls_x, ls_y, ls_w, ls_h, "Level shifter\n(e.g. 74AHCT125)\n3.3V→5V DATA\nVCC: 5V (shared rail)\nGND: common",
    fc="#fff4e0", ec="#a3691a", fontsize=7.6)

wire(pi_x + pi_w, pi_y + pi_h * 0.3, ls_x, ls_y + ls_h * 0.6, ORANGE,
     "3.3V DATA (GPIO)", lw=2.0, ls=(0, (5, 2)))
wire(ls_x + ls_w, ls_y + ls_h * 0.45, j1_x, j1_y + 3, ORANGE,
     "5V DATA (shifted)", lw=2.4)
wire(bo_x + bo_w, bo_y + bo_h * 0.35, j1_x, j1_y - 1, RED,
     "5V IN (own wire,\nstraight from breakout)", lw=3.0, label_frac=0.28)
wire(bo_x + bo_w, bo_y + bo_h * 0.18, j1_x, j1_y - 5, BLACK, "GND", lw=3.0)
wire(j1_x + 7, j1_y, disp_x, disp_y + disp_h * 0.5, "#555555",
     "1 cable, 3 conductors\n(J1 chain-in, JST-PH)", lw=3.6)

# ============ annotations ============
ax.text(pi_x + pi_w / 2, pi_y + pi_h + 6,
        "Star wiring off ONE breakout connector: the Pi and the LED\n"
        "chain each get their own wire straight back to it — LED\n"
        "current never passes through the Pi's own GPIO pin/trace.",
        ha="center", fontsize=8.6, color="#444444")

ax.text(disp_x + disp_w / 2, disp_y - 7,
        "6A supply, ~9.3A theoretical worst-case draw (LEDs+Pi) —\n"
        "LED-driving code MUST cap color/brightness to stay safely\n"
        "under 6A, not just assume typical usage stays low.",
        ha="center", fontsize=8.3, color="#a32c26", weight="bold")

ax.text(102, 5,
        "The one component external to the Pi this design needs: WS2812 expects DATA-high above ~0.7×5V;\n"
        "the Pi's 3.3V GPIO is marginal, especially at this first LED.",
        ha="center", fontsize=7.8, color="#8a5a10")

ax.text((brick_x + bo_x + bo_w) / 2, 25,
        "Plain 5V brick, not a USB-C PD charger: a PD charger's\n"
        "default 5V output is often current-limited (~3A) without\n"
        "negotiation — not guaranteed to cover LED worst-case draw.",
        ha="center", fontsize=7.6, color="#8a2c26")

fig.suptitle("KegStation Power Wiring — Sallaup KegSense", fontsize=17, fontweight="bold", y=0.985)
ax.text(86, 1.5,
        "Sallaup Electronics  —  plain 5V DC brick → USB-C breakout, star-wired to Pi + LED chain, plus a level shifter on the DATA line",
        ha="center", fontsize=9.1, color="#555555")

plt.tight_layout(rect=[0, 0.02, 1, 0.965])
plt.savefig(OUT, dpi=160)
print("wrote", OUT)
