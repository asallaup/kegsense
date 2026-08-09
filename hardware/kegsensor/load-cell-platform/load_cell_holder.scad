// Load cell holder - derived from a third-party Printables design
// (https://www.printables.com/model/157473-load-cell-holder), reverse
// measured from the downloaded STL rather than guessed - see the
// measurement commands in project history / commit message for how each
// number below was extracted (2D cross-section slices + point-cloud
// analysis of the actual mesh, not eyeballed).
//
// This is a FAITHFUL FUNCTIONAL recreation (same envelope, hole
// positions/sizes, pocket opening, general thickness) expressed as
// editable OpenSCAD instead of an opaque STL, matching how the rest of
// this project's parts are built (case.scad, generate_pcb.py). It is
// NOT a byte-identical mesh clone - fine fillet/lip details are
// approximated. Validate print fit against the original STL
// (load-cell-platform/load_cell_holder_reference.stl) before relying on this
// for a real build.
//
// Snap-fit bracket: two outer ears bolt down to a base plate: the load
// cell itself snaps into the central pocket, gripped by the raised lip
// around it and able to flex slightly thanks to the seam slit at the
// pocket's top edge.

// ---- measured dimensions -------------------------------------------
ear_thickness = 6.0;       // ear tab thickness (measured: ~5.9-6.0mm)
lip_height = 2.0;          // raised pocket lip, on top of ear_thickness
                            // (total part height measured as 8.01mm)

collar_half_w = 22.0;      // central collar half-width (x)
collar_half_h = 23.02;     // central collar half-height (y) - measured
collar_corner_r = 6.0;     // approximate corner rounding

ear_half_h = 12.51;        // ear tab half-height (y) - measured
ear_outer_x = 38.04;       // ear tip x-extent (half of 76.08mm total)
ear_corner_r = 6.0;        // approximate ear end rounding

bolt_hole_x = 29.53;       // bolt hole x position - measured
bolt_hole_r = 2.05;        // bolt hole radius - measured (~M4 clearance)

pocket_half = 13.01;       // pocket opening half-width/height (26.03mm
                            // square) - measured
pocket_corner_r = 3.0;     // approximate pocket corner rounding

seam_half_w = 2.92;        // split-seam slit half-width - measured
seam_y0 = 19.1;            // seam starts at this y (measured) ...
seam_y1 = collar_half_h + 1;  // ... through the outer edge

// ---- added feature: cable exit notch (not present in the original) --
// The original design has NO cable exit - confirmed directly (2D
// cross-section + top-down height projection), not assumed: the pocket
// is fully enclosed on all 4 sides, and the flex-seam slit above does
// not reach the pocket opening (there's solid material between them).
// Without this, a cable coming off the load cell would have to share
// the same ~26x26mm pocket opening as the load cell body itself.
// Placed on the -Y side (opposite the seam slit at +Y) so the two
// features stay clearly separated. Half the part's total height, at the
// bottom (z=0 up), not full height - leaves solid material above it as
// a roof over the cable exit.
cable_notch_half_w = 3.0;  // 6mm wide - fits a small multi-conductor cable
cable_notch_y0 = -pocket_half + 1;   // starts just inside the pocket edge
cable_notch_y1 = -collar_half_h - 1; // ... through the outer collar edge
cable_notch_height = (ear_thickness + lip_height) / 2;  // half of 8mm = 4mm

$fn = 64;

module rounded_rect(w, h, r) {
    offset(r = r)
        offset(delta = -r)
            square([w, h], center = true);
}

module outline_2d() {
    // Ear tabs overlap deep into the collar (starting well inside its
    // half-width, not right at the edge) so their rounded corners land
    // entirely within the collar's solid area instead of both shapes'
    // roundings landing at the same seam and leaving a gap there - first
    // version of this had exactly that bug, caught by rendering and
    // comparing against the original rather than trusting it blind.
    ear_inner_x = collar_half_w * 0.4;
    union() {
        rounded_rect(collar_half_w * 2, collar_half_h * 2, collar_corner_r);
        translate([(ear_inner_x + ear_outer_x) / 2, 0])
            rounded_rect(ear_outer_x - ear_inner_x, ear_half_h * 2, ear_corner_r);
        translate([-(ear_inner_x + ear_outer_x) / 2, 0])
            rounded_rect(ear_outer_x - ear_inner_x, ear_half_h * 2, ear_corner_r);
    }
}

module pocket_2d() {
    rounded_rect(pocket_half * 2, pocket_half * 2, pocket_corner_r);
}

module holder() {
    difference() {
        union() {
            // base body (ears + collar), to ear_thickness
            linear_extrude(height = ear_thickness)
                difference() {
                    outline_2d();
                    pocket_2d();
                }
            // raised lip around the pocket, on top of the base body
            translate([0, 0, ear_thickness])
                linear_extrude(height = lip_height)
                    difference() {
                        offset(r = 2) pocket_2d();  // lip wall ~2mm thick
                        pocket_2d();
                    }
        }
        // bolt holes, through everything
        translate([bolt_hole_x, 0, -1])
            cylinder(r = bolt_hole_r, h = ear_thickness + 2);
        translate([-bolt_hole_x, 0, -1])
            cylinder(r = bolt_hole_r, h = ear_thickness + 2);
        // split-seam flex slit, through the lip at the pocket's top edge
        translate([-seam_half_w, seam_y0, ear_thickness - 0.5])
            cube([seam_half_w * 2, seam_y1 - seam_y0, lip_height + 1]);
        // cable exit notch (added - see comment above), half height, at
        // the bottom (z=-1 for a clean cut through the bottom face, up
        // to cable_notch_height above z=0)
        translate([-cable_notch_half_w, cable_notch_y1, -1])
            cube([cable_notch_half_w * 2, cable_notch_y0 - cable_notch_y1,
                  cable_notch_height + 1]);
    }
}

holder();
