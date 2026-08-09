// Keg Sensor Module - 3D printable case
// Board: 155 x 90 x 1.6mm, mounting holes (M3 clearance) at (6,6) (150,6)
// (6,84) (150,84) in board-local coords. See keg_sensor_module.kicad_pcb.
//
// Two parts, printed separately: base (this file's default) and lid.
// Render one or the other via the PART variable below, or use
// generate_case.sh which renders both plus an assembled preview.

PART = "base"; // "base" | "lid" | "preview" (assembled, lid made transparent)

// ---- board + layout ---------------------------------------------------
board_w = 155;
board_h = 90;
board_t = 1.6;

mtg_hole_d = 3.4;         // M3 clearance, +0.2mm over the board's 3.2mm hole
mtg_x1 = 6;  mtg_y1 = 6;  // board-local mounting hole centers
mtg_x2 = 150; mtg_y2 = 6;
mtg_x3 = 6;  mtg_y3 = 84;
mtg_x4 = 150; mtg_y4 = 84;

// ---- case shell ---------------------------------------------------------
wall = 2.0;
margin = 3.0;             // gap between board edge and inner wall
floor_t = 2.0;
lid_t = 2.0;

standoff_h = 5.0;         // case floor top -> board bottom
component_clear = 15.0;   // board top -> inside of lid (tallest part: J7 RJ jack)

inner_w = board_w + 2*margin;
inner_h = board_h + 2*margin;
outer_w = inner_w + 2*wall;
outer_h = inner_h + 2*wall;
wall_ht = standoff_h + board_t + component_clear;   // floor top -> rim top

board_x0 = wall + margin;  // board origin, in case-outer coordinates
board_y0 = wall + margin;

// ---- corner lid-mounting posts (at the box's actual corners) ------------
corner_post_d = 7;
corner_post_hole_d = 2.5;  // pilot hole, self-tapping M3
corner_inset = 5;
corner_posts = [
    [corner_inset, corner_inset],
    [outer_w - corner_inset, corner_inset],
    [corner_inset, outer_h - corner_inset],
    [outer_w - corner_inset, outer_h - corner_inset],
];

// ---- PCB standoff posts (at the board's own mounting holes) -------------
standoff_post_d = 6;
standoff_pilot_d = 2.5;
pcb_posts = [
    [board_x0 + mtg_x1, board_y0 + mtg_y1],
    [board_x0 + mtg_x2, board_y0 + mtg_y2],
    [board_x0 + mtg_x3, board_y0 + mtg_y3],
    [board_x0 + mtg_x4, board_y0 + mtg_y4],
];

// ---- connector cutouts ----------------------------------------------------
// J1-J4 sensor wires exit the board's left edge (board-local x ~7-23,
// y ~11-79) - cut the case's left wall over that span with margin.
left_cut_y0 = board_y0 + 8;
left_cut_y1 = board_y0 + 82;
left_cut_z0 = floor_t + 2;
left_cut_z1 = floor_t + wall_ht - 2;

// J7 (RJ11 jack) sits near the board's top-right corner; exact cable-exit
// direction wasn't confirmed against the physical part (see README), so
// the top wall is left open across that whole corner instead of a single
// precise cutout - easy to reprint narrower once the real connector is in
// hand and its orientation is confirmed.
rj_cut_x0 = board_x0 + 122;
rj_cut_x1 = outer_w - wall + 1;   // through the corner
rj_cut_z0 = floor_t + 2;
rj_cut_z1 = floor_t + wall_ht - 2;

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
    difference() {
        union() {
            // floor + walls
            difference() {
                cube([outer_w, outer_h, floor_t + wall_ht]);
                translate([wall, wall, floor_t])
                    cube([inner_w, inner_h, wall_ht + 1]);
            }
            // corner lid posts
            for (p = corner_posts)
                translate([p[0], p[1], 0])
                    corner_post(floor_t + wall_ht);
            // PCB standoff posts (top of post = board bottom = floor_t+standoff_h)
            for (p = pcb_posts)
                translate([p[0], p[1], 0])
                    pcb_post(floor_t + standoff_h);
        }
        // left-wall wire cutout
        translate([-1, left_cut_y0, left_cut_z0])
            cube([wall + 2, left_cut_y1 - left_cut_y0, left_cut_z1 - left_cut_z0]);
        // top-right corner cutout for J7 / RJ11 cable
        translate([rj_cut_x0, -1, rj_cut_z0])
            cube([rj_cut_x1 - rj_cut_x0, wall + 2, rj_cut_z1 - rj_cut_z0]);
    }
}

module lid() {
    difference() {
        cube([outer_w, outer_h, lid_t]);
        for (p = corner_posts)
            translate([p[0], p[1], -0.1])
                cylinder(d = corner_post_hole_d + 0.6, h = lid_t + 0.2); // clearance for screw head shaft
    }
    // countersink-ish recess so screw heads sit flush
    difference() {
        union() {
            for (p = corner_posts)
                translate([p[0], p[1], lid_t])
                    cylinder(d = 6.5, h = 0.01); // marker only, kept flat
        }
    }
}

if (PART == "base") {
    base();
} else if (PART == "lid") {
    lid();
} else if (PART == "preview") {
    base();
    color("SteelBlue", 0.5)
        translate([0, 0, floor_t + wall_ht])
            lid();
}
