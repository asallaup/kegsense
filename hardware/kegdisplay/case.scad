// KegDisplay (Sallaup Electronics / Sallaup KegSense) - 3D printable case
// CONCEPT SKETCH, not a board-fitted enclosure yet. keg_display_module.kicad_pcb
// is currently 160x120mm - a generous first-pass ROUTING board, explicitly not
// size-optimized (see hardware/kegdisplay/README.md). This sketches the
// TARGET size/shape a size-optimized respin should aim for instead.
//
// Two explicit constraints driving this version (both from user feedback on
// the first sketch, which was tap-mounted with a small OLED window in a much
// bigger box):
//   1. NOT tap-mounted - no clip/bracket modeled here. Physical mounting is
//      still genuinely undecided (see README "Still open"); this version
//      just leaves the back plain rather than guessing again.
//   2. The OLED should cover most of the front face, not sit as a small
//      window in a big box.
//
// That second constraint is a real trade-off, not just a cosmetic tweak: the
// front footprint is sized to the OLED module (~28x28mm) rather than to the
// Arduino Nano (18x45mm on its headers), which is physically the bigger
// part. To still fit the Nano, it has to stand on edge BEHIND the display
// (its 45mm length running front-to-back, along the case's depth) instead of
// lying flat in the same plane as the OLED - which makes this case a deep,
// squarish "puck" (~34x34mm face, ~55mm deep) rather than a thin slab. A
// thinner case is possible, but only by letting the OLED go back to being a
// smaller fraction of a wider front face - flagging that trade explicitly
// rather than quietly picking one.

PART = "base"; // "base" | "lid" | "preview" (assembled, lid made transparent)

// ---- case shell (target size, not board-driven yet) --------------------
// Front footprint set by the OLED module, not the Nano - see header note.
outer_w = 34;
outer_h = 34;
wall = 1.6;
floor_t = 2.0;              // back plate
lid_t = 1.6;                // front plate (mostly cut away by the OLED window)
wall_ht = 50;                // cavity depth - Nano standing on edge (~45mm) + clearance

inner_w = outer_w - 2*wall;
inner_h = outer_h - 2*wall;

// ---- OLED window (front) ------------------------------------------------
// 0.96" SSD1306 active area is ~21.7x11.2mm, but the module's PCB (what the
// window needs to clear, not just the pixels) runs closer to 27.8x27.3mm on
// common breakouts - window sized just inside that, centered, so only a
// ~2mm bezel remains around it.
oled_w = 30;
oled_h = 30;
oled_x = (outer_w - oled_w) / 2;
oled_y = (outer_h - oled_h) / 2;

// ---- RJ12 daisy-chain cable cutouts ----------------------------------
// On the left/right side walls, near the BACK (away from the display face) -
// upstream in one side, downstream out the other.
rj12_cut_w = 10;   // along the wall's own face (Y)
rj12_cut_h = 8;    // height (Z)
rj12_cut_z = floor_t + wall_ht - 14;

// ---- corner lid-mounting posts ------------------------------------------
corner_post_d = 5;
corner_post_hole_d = 2;    // pilot hole, self-tapping M2
corner_inset = 4;
corner_posts = [
    [corner_inset, corner_inset],
    [outer_w - corner_inset, corner_inset],
    [corner_inset, outer_h - corner_inset],
    [outer_w - corner_inset, outer_h - corner_inset],
];

module rounded_rect(w, h, r) {
    hull() {
        for (dx = [r, w - r])
            for (dy = [r, h - r])
                translate([dx, dy]) circle(r = r, $fn = 32);
    }
}

module cavity() {
    translate([wall, wall, 0])
        linear_extrude(height = wall_ht + 1)
            rounded_rect(inner_w, inner_h, 3);
}

module base() {
    difference() {
        union() {
            linear_extrude(height = floor_t + wall_ht)
                rounded_rect(outer_w, outer_h, 4);
            // corner posts for lid screws
            for (p = corner_posts)
                translate([p[0], p[1], floor_t])
                    cylinder(d = corner_post_d, h = wall_ht, $fn = 24);
        }
        // hollow out the interior, leaving the floor
        translate([0, 0, floor_t]) cavity();
        // pilot holes down through the posts
        for (p = corner_posts)
            translate([p[0], p[1], -1])
                cylinder(d = corner_post_hole_d, h = floor_t + wall_ht + 2, $fn = 16);
        // RJ12 cable cutouts, left/right walls near the back
        translate([-0.5, (outer_h - rj12_cut_w) / 2, rj12_cut_z])
            cube([wall + 1, rj12_cut_w, rj12_cut_h]);
        translate([outer_w - wall - 0.5, (outer_h - rj12_cut_w) / 2, rj12_cut_z])
            cube([wall + 1, rj12_cut_w, rj12_cut_h]);
    }
}

module lid() {
    difference() {
        union() {
            linear_extrude(height = lid_t)
                rounded_rect(outer_w, outer_h, 4);
            // screw bosses matching the base's corner posts
            for (p = corner_posts)
                translate([p[0], p[1], lid_t])
                    cylinder(d = corner_post_d + 1, h = 2, $fn = 24);
        }
        // OLED viewing window
        translate([oled_x, oled_y, -1])
            linear_extrude(height = lid_t + 2)
                rounded_rect(oled_w, oled_h, 2);
        // screw clearance holes through the bosses
        for (p = corner_posts)
            translate([p[0], p[1], -1])
                cylinder(d = corner_post_hole_d + 0.6, h = lid_t + 4, $fn = 16);
    }
}

if (PART == "base") {
    base();
} else if (PART == "lid") {
    lid();
} else {
    // assembled preview - lid shown translucent, offset for visibility
    color("lightgray") base();
    translate([0, 0, floor_t + wall_ht + 0.2])
        color([0.2, 0.6, 0.9, 0.35]) lid();
}
