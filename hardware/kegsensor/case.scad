// KegSensor (Sallaup Electronics / Sallaup KegSense) - 3D printable case
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
// J1-J4 sensor wires exit near the board's top edge (board-local x
// 17.28-122.88 - the row's unrotated courtyard span: each part's
// courtyard is 15.6mm wide, 30mm pitch, first at x=20 last at x=110, see
// generate_pcb.py) - cut the case's front wall (y=0, the wall the
// board's own y=0 edge sits against) over that span with margin.
front_cut_x0 = board_x0 + 10;
front_cut_x1 = board_x0 + 120;
front_cut_z0 = floor_t + 2;
front_cut_z1 = floor_t + wall_ht - 2;

// J7 (RJ11 jack, RJ14 footprint) sits flush with the board's bottom edge
// (y=90), rotated so its cable/plug face points +Y - its shell spans
// board-local x=138.27-150.67 (see generate_pcb.py's J7 placement
// comment - read back from actual DRC-reported pad/courtyard
// coordinates, not assumed). Cut the BACK wall (y=outer_h, the wall the
// board's own y=90 edge sits against) over that span with margin.
// Previously flush with the right edge instead, with a right-wall
// cutout - moved when J7 moved to the bottom edge per explicit request.
back_cut_x0 = board_x0 + 131;
back_cut_x1 = board_x0 + 148;
back_cut_z0 = floor_t + 2;
back_cut_z1 = floor_t + wall_ht - 2;

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
        // front-wall wire cutout for J1-J4
        translate([front_cut_x0, -1, front_cut_z0])
            cube([front_cut_x1 - front_cut_x0, wall + 2, front_cut_z1 - front_cut_z0]);
        // back-wall cutout for J7 / RJ11 cable
        translate([back_cut_x0, outer_h - wall - 1, back_cut_z0])
            cube([back_cut_x1 - back_cut_x0, wall + 2, back_cut_z1 - back_cut_z0]);
        // engraved branding, both lines on the right wall - the one wall
        // without a connector cutout now that J1-J4 (front) and J7 (back)
        // both claim one. Previously on the back wall, before J7 moved
        // there.
        wall_text_right("KegSensor", 5, text_z + 3.3, false);
        wall_text_right("Sallaup Electronics", 2.6, text_z - 3, true);
    }
}

// Engraved (recessed) branding on the back wall (y=outer_h) - the one
// wall without a connector cutout, now that J1-J4 (front) and J7 (back)
// both claim one. 0.6mm deep into the 2mm wall (1.4mm remains - plenty
// strong), centered vertically in the same safe z-band as the connector
// cutouts (floor_t+2 .. floor_t+wall_ht-2) and horizontally clear of the
// corner posts.
engrave_d = 0.6;
text_z = floor_t + wall_ht / 2;

// Getting front/back right took two iterations of actually rendering and
// checking (a true 2D orthographic projection of just the wall in
// question, not eyeballing a 3D perspective view - that first misled me
// into "fixing" this with a 180deg rotation, which turned out to swap the
// wrong axis). Two different corrections were needed, for two different
// reasons:
//  - front wall: rotate([-90,0,0]) alone renders text upside down (letters
//    vertically flipped) - mirror([0,1,0]) on the text before extrusion
//    fixes it.
//  - back wall: rotate([90,0,0]) alone renders letters right-side up and
//    in the same left-to-right order as world +X - but a viewer actually
//    standing behind the box looking at that face has their own "right"
//    pointing in world -X (they're facing the opposite direction), so
//    text in unflipped +X order reads backwards *to them* even though the
//    raw geometry isn't mirrored. mirror([1,0,0]) corrects for that.
// wall_text_front/back are both unused now (branding moved to the right
// wall below) but kept in case a wall needs text again later - each
// still needs its own from-scratch verification if reused, not just
// reasoning by analogy from another wall (that's exactly what went wrong
// here the first time).
module wall_text_front(msg, size, z = text_z, italic = false) {
    // front wall, exterior face at y=0 - cutter pokes out to y=-0.1 for a
    // clean boolean and goes engrave_d into the wall (+Y).
    style = italic ? "Italic" : "Bold";
    translate([outer_w / 2, -0.1, z])
        rotate([-90, 0, 0])
            linear_extrude(height = engrave_d + 0.1)
                mirror([0, 1, 0])
                    text(msg, size = size, halign = "center", valign = "center",
                         font = str("Liberation Sans:style=", style));
}

module wall_text_back(msg, size, z = text_z, italic = false) {
    // back wall, exterior face at y=outer_h - cutter pokes out to
    // y=outer_h+0.1 and goes engrave_d into the wall (-Y).
    style = italic ? "Italic" : "Bold";
    translate([outer_w / 2, outer_h + 0.1, z])
        rotate([90, 0, 0])
            linear_extrude(height = engrave_d + 0.1)
                mirror([1, 0, 0])
                    text(msg, size = size, halign = "center", valign = "center",
                         font = str("Liberation Sans:style=", style));
}

// Right wall: exterior face at x=outer_w, engraving into the wall in -X.
// Derived the same way as front/back (checking what each transform
// actually does to a known point, not guessing) rather than assumed by
// analogy - a right wall isn't just "front/back with axes swapped",
// since the viewer's own "right" for someone standing to the box's right
// (looking in -X, up=+Z) works out to world +Y, not a trivial relabeling.
// rotate([90,0,90]) alone maps text-local X to world Y and text-local Y
// to world Z correctly (verified against known rotate-about-X-axis and
// rotate-about-Z-axis formulas applied in OpenSCAD's actual [x,y,z]
// rotate order), but leaves the engrave/extrude direction pointing +X
// (out of the wall, wrong way) - mirror([0,0,1]) on the extruded solid,
// applied before that rotate, flips just that direction without
// disturbing the already-correct X/Y mapping. Verified after the fact
// with the same true-2D-cross-section method as front/back, not assumed
// correct from the derivation alone.
module wall_text_right(msg, size, z = text_z, italic = false) {
    style = italic ? "Italic" : "Bold";
    translate([outer_w + 0.1, outer_h / 2, z])
        rotate([90, 0, 90])
            mirror([0, 0, 1])
                linear_extrude(height = engrave_d + 0.1)
                    text(msg, size = size, halign = "center", valign = "center",
                         font = str("Liberation Sans:style=", style));
}

module lid() {
    difference() {
        cube([outer_w, outer_h, lid_t]);
        for (p = corner_posts)
            translate([p[0], p[1], -0.1])
                cylinder(d = corner_post_hole_d + 0.6, h = lid_t + 0.2); // clearance for screw head shaft
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
