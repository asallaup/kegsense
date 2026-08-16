// KegDisplay Bar (Sallaup Electronics / Sallaup KegSense) - 3D printable
// enclosure for the WS2812-strip-on-backer-PCB module (revision 8). See
// keg_display_bar_module.kicad_pcb / ../README.md.
//
// Board: 34 x 132 x 1.6mm. All board-local coordinates below are taken
// straight from generate_bar_pcb.py's hand-tuned placements, converted
// from the PCB file's own offset origin (9.5, -2) to board-local (0, 0)
// = the board's own top-left corner in KiCad's Y-down convention. That
// convention is kept here too: local Y increases toward the board's
// PHYSICAL BOTTOM (where J1/J2 and the strip's bottom/IN end sit), same
// as in the PCB file - not flipped to a more "typical" OpenSCAD +Y-up
// layout, so these numbers can be checked directly against the PCB
// without a mental mirroring step.
//
// FIRST DRAFT - not verified against real hardware. Component depths
// (connector body height, strip thickness) are typical values, not
// measured off real parts - re-check before printing for real.
//
// Two parts, printed separately: base (solid wall + side walls +
// standoffs + collar mounting flanges, this file's default - this is
// the part that mounts flush against the collar) and lid (flat cover
// with the diffuser window cut into it, screwed onto the base's corner
// posts). Assembly: PCB mounts to the two standoff posts (at MH1/MH2)
// rising from the base's solid wall, strip-covered front face pointing
// AWAY from the base/collar, toward the lid's window; lid closes over
// the front, facing outward into the room so the LEDs are visible.
// Render one or the other via the PART variable below, or use
// generate_case_bar.sh which renders both plus an assembled preview.

PART = "base"; // "base" | "lid" | "preview" (assembled, lid made transparent)

// ---- board + layout (board-local, see header) --------------------------
board_w = 34;
board_h = 132;
board_t = 1.6;

// Mounting holes (MH1/MH2), 2.2mm, board-local.
mtg_hole_d = 2.4;         // M2 clearance, +0.2mm over the board's 2.2mm hole
mtg_x1 = 15.5; mtg_y1 = 5.5;
mtg_x2 = 15.5; mtg_y2 = 122.5;

// J1 (chain in, near the left edge) / J2 (chain out, near the right
// edge) - both near the board's physical bottom (large local Y), cable
// exits sideways through the case's left/right walls. Positions/size
// from generate_bar_pcb.py (J1 at absolute (11.55,124.5), J2 at
// (41.45,120.5), converted to board-local by subtracting the PCB's
// (9.5,-2) origin offset) and the JST-PH footprint's own courtyard
// (~6.75mm body height, ~9mm long including the cable-exit overhang).
j1_x = 2.05;  j1_y = 126.5;
j2_x = 31.95; j2_y = 122.5;
conn_cut_h = 9;   // wire/plug clearance slot height, centered on j*_y
conn_cut_z = 8;   // slot height in Z (depth), centered in the case depth

// Strip span (board-local Y): from TP4-6 (top/OUT end, y=12) down to
// TP1-3 (bottom/IN end, y=108) - the diffuser window covers this span,
// not the full board (top/bottom margins hold J1/J2/R1/C1/TP1-3 and
// need solid front wall + component clearance instead of an opening).
strip_y_top = 12;
strip_y_bottom = 108;

// ---- case shell ----------------------------------------------------------
wall = 2.0;
margin = 2.5;              // gap between board edge and inner wall
back_t = 2.0;                // base's solid wall thickness (mounts to collar)
lid_t = 2.0;                 // lid thickness (carries the window)

standoff_h = 3.0;            // base's solid wall inner face -> board back
pcb_to_window = 10.0;        // board front face -> inside of lid
                              // (clears J1/J2/R1/C1/TP1-3/TP4-6 bodies in
                              // the margin bands, and the strip's own
                              // thickness in the window band)

inner_w = board_w + 2*margin;
inner_h = board_h + 2*margin;
outer_w = inner_w + 2*wall;
outer_h = inner_h + 2*wall;
case_depth = standoff_h + board_t + pcb_to_window;   // base's inner face -> lid's inner face

board_x0 = wall + margin;   // board origin, in case-outer (X,Y) coordinates
board_y0 = wall + margin;

// ---- corner lid-mounting posts (at the box's actual corners) -----------
corner_post_d = 6;
corner_post_hole_d = 2.5;   // pilot hole, self-tapping M3
corner_inset = 4;
corner_posts = [
    [corner_inset, corner_inset],
    [outer_w - corner_inset, corner_inset],
    [corner_inset, outer_h - corner_inset],
    [outer_w - corner_inset, outer_h - corner_inset],
];

// ---- PCB standoff posts (at the board's own MH1/MH2 mounting holes) ----
standoff_post_d = 5;
standoff_pilot_d = 1.8;   // self-tapping pilot for the board's own screw
pcb_posts = [
    [board_x0 + mtg_x1, board_y0 + mtg_y1],
    [board_x0 + mtg_x2, board_y0 + mtg_y2],
];

// ---- diffuser window (in the LID, over the strip's span) ---------------
window_margin = 3;   // frame width left/right of the strip
window_x0 = board_x0 + window_margin;
window_x1 = board_x0 + board_w - window_margin;
window_y0 = board_y0 + strip_y_top - 2;
window_y1 = board_y0 + strip_y_bottom + 2;

// ---- collar mounting flanges (on the BASE, not the lid) -----------------
// The base is the part that sits flush against the collar's side wall -
// the lid carries the window and needs to face OUTWARD into the room so
// the LEDs are actually visible, not into the collar. Two flanges, top
// and bottom short edges, each with a clearance hole for a wood screw
// driven straight into the collar.
flange_w = 14;
flange_h = 10;
flange_hole_d = 4.0;   // clearance for a small wood screw shank

module mount_flange() {
    difference() {
        cube([flange_w, flange_h, back_t]);
        translate([flange_w / 2, flange_h / 2, -0.1])
            cylinder(d = flange_hole_d, h = back_t + 0.2);
    }
}

$fn = 48;

module pcb_post(h) {
    difference() {
        cylinder(d = standoff_post_d, h = h);
        translate([0, 0, h - standoff_h + 0.1])
            cylinder(d = standoff_pilot_d, h = standoff_h + 1);
    }
}

module corner_post(h) {
    difference() {
        cylinder(d = corner_post_d, h = h);
        translate([0, 0, h - 8])
            cylinder(d = corner_post_hole_d, h = 8 + 1);
    }
}

module base() {
    union() {
        // solid back wall + side walls + top/bottom walls (shell) - no
        // window, this face mounts flush against the collar
        difference() {
            cube([outer_w, outer_h, back_t + case_depth]);
            translate([wall, wall, back_t])
                cube([inner_w, inner_h, case_depth + 1]);
            // J1 cable cutout, left wall
            translate([-1, board_y0 + j1_y - conn_cut_h/2, back_t + (case_depth - conn_cut_z)/2])
                cube([wall + 2, conn_cut_h, conn_cut_z]);
            // J2 cable cutout, right wall
            translate([outer_w - wall - 1, board_y0 + j2_y - conn_cut_h/2, back_t + (case_depth - conn_cut_z)/2])
                cube([wall + 2, conn_cut_h, conn_cut_z]);
        }
        // corner lid posts (rise from the solid wall's inner face, full
        // case depth, so the lid closes flush at the open/front end)
        for (p = corner_posts)
            translate([p[0], p[1], back_t])
                corner_post(case_depth);
        // PCB standoff posts (top of post = board back = back_t +
        // pcb_to_window + board_t)
        for (p = pcb_posts)
            translate([p[0], p[1], back_t])
                pcb_post(pcb_to_window + board_t);
        // collar mounting flanges, top and bottom short edges, flush
        // with the solid wall's exterior face (z=0..back_t)
        translate([outer_w / 2 - flange_w / 2, -flange_h, 0])
            mount_flange();
        translate([outer_w / 2 - flange_w / 2, outer_h, 0])
            mount_flange();
    }
}

module lid() {
    difference() {
        cube([outer_w, outer_h, lid_t]);
        for (p = corner_posts)
            translate([p[0], p[1], -0.1])
                cylinder(d = corner_post_hole_d + 0.6, h = lid_t + 0.2); // clearance for screw head shaft
        // diffuser window - straight through the lid
        translate([window_x0, window_y0, -1])
            cube([window_x1 - window_x0, window_y1 - window_y0, lid_t + 2]);
    }
}

if (PART == "base") {
    base();
} else if (PART == "lid") {
    lid();
} else if (PART == "preview") {
    base();
    color("SteelBlue", 0.5)
        translate([0, 0, back_t + case_depth])
            lid();
}
