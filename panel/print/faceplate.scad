// 3D-printable faceplate for the OPN-500 / CMP-01 compressor.
//
// Hole positions and legends come from panel_data.scad, which make_panel.py writes
// from the same definition as the drawing and the DXF. Everything here is how to print
// it: thicknesses, fit allowances and the engraving.
//
// Printed face down: the front face sits on the bed, so it comes out as smooth (or as
// textured) as the build plate, and the legend is engraved into it. Nothing needs
// supports.
//
//   part = "panel"        the faceplate
//   part = "legend"       the engraving as a separate body, to print in a second colour
//   part = "fit_test"     a 27 mm strip through THRESHOLD, HPF, KEY and the meter
//                         bottoms, to check the fits before printing the whole panel
//   part = "fit_legend"   the fit test's engraving
//   part = "panel" also carries the main-board bracket on its back (bracket = true)
//   part = "retainer"     a thin plate that clips over the back of both meters and holds
//                         the LEDs in their slots; prints flat, ribs and pins up
//   part = "preview"      both, front face up, in colour (for the picture in README.md)
//
// openscad -o faceplate.stl -D 'part="panel"' faceplate.scad   (or run build.sh)

include <panel_data.scad>

part = "panel";

/* [Outline] */
// printed width; nominal is 38.10, trimmed so it slides in beside its neighbours
trim_w = 37.8;
// printed height; nominal is 133.35
trim_h = 132.6;
corner_r = 1.0;
// 45 degree chamfer round the front face, so first-layer squish doesn't flare the edge
edge_chamfer = 0.4;

/* [Thickness] */
// overall, as the 1/8 inch metal panel, so the rack screws and every part behind the
// panel sit exactly as drawn
thk = 3.2;
// the front is flat at the pots, so the knobs sit down close to it. The Altronics 9 mm
// pots have no nut; the toggle nuts hold the front board.

/* [Fits] */
// added to the pot, switch and screw holes; FDM holes print undersize
hole_comp = 0.2;
// meter LEDs: Jaycar 2 mm tower LEDs (ZD0060 orange, ZD0070 green, ZD0040 red), measured:
// a 2.0 mm round tower, 1.5 mm tall, on a 3.25 x 2.5 mm base, 1.5 mm tall, its long side
// across the column (the leads' direction). The tower pushes through a snug hole from the
// back and the base's shoulder stops against a slot along each meter column, so every LED
// sits square and at the same height.
led_tower_d = 2.0;
// tower length above the shoulder
led_tower_h = 1.5;
// base across the meter column
led_base_w = 3.25;
// base along the meter column
led_base_l = 2.5;
// added to the tower hole; FDM holes print undersize, so this gives a push fit
led_comp = 0.2;
// added to the base slot's width and length
led_base_clear = 0.3;
// how far the tower tips stand proud of the front face (0 = flush, negative = recessed)
led_proud = 0;
// extra slot depth behind the flush position, so an LED that sits a little high still
// leaves the retainer room to close (the retainer's ribs don't grow with it)
led_slot_extra = 0.6;
// the slot never leaves less than this much plastic between it and the front
led_min_web = 0.8;
// chamfer on the bed side of pot, switch and screw holes
hole_chamfer = 0.3;

/* [Legend] */
// 0.6 = the 0.2 mm first layer plus five 0.08 mm layers
legend_depth = 0.6;
// 1.0 = the mockup's type sizes, which are too small for a 0.4 mm nozzle
legend_scale = 1.3;
// squeeze the type horizontally to keep the ATTACK / RELEASE row apart
legend_condense = 0.85;
// grows every stroke by this much on each side: 0.15 keeps the thin strokes at
// 0.5 mm or more, wider than a 0.4 mm nozzle's line
legend_bold = 0.15;
// letter spacing (OpenSCAD's text() spacing), opened up to keep the bolder letters apart
legend_spacing = 1.2;
legend_font = "Liberation Sans:style=Bold";
// tick marks at the start, middle and end of each pot's travel
ticks = true;
tick_w = 0.6;
tick_len = 1.2;
// gap between the knob skirt and the inner end of a tick
tick_gap = 0.9;

/* [LED retainer] */
// height of the LED base below the tower's shoulder
led_base_h = 1.5;
retainer_t = 1.2;
// plate border round the two slots
retainer_margin = 1.5;
// a rib on the plate goes into each slot; it reaches this far past the backs of the
// LED bases, so it presses them into the panel (0.2 = one layer)
retainer_press = 0.2;
// gap each side of the rib in its slot
retainer_rib_clear = 0.15;
// LED leads: two per LED, across the column, as the front board's pads
lead_pitch = 2.54;
lead_hole_d = 1.3;
// two pins between the meters press into blind holes in the back of the panel
retainer_pin_d = 2.0;
retainer_pin_h = 1.2;
// added to the pin holes; the 2.2 mm LED holes slide on a 2.0 mm tower, so 0.1 grips
retainer_pin_fit = 0.1;

/* [Main board bracket] */
// a wall down the back of the panel's left edge with two ears that the main board
// screws to (M3 x 8 through H1 and H2, into nuts captive in the ears)
bracket = true;
// main board: centre plane left of the panel centreline (front view), as the 500 rack's
// edge connector, 11.12 mm left of centre
board_offset = 11.12;
board_t = 1.6;
// main board front edge, behind the back of the panel
board_setback = 24.0;
// main board top edge, down from the top of the panel: the 105 mm card centred on it
board_top = (133.35 - 105) / 2;
// H1 and H2 on the main board: [down from its top edge, back from its front edge]
board_holes = [[11.0, 4.85], [96.0, 4.85]];
// air between each ear and the board's solder side; shim with washers if the board
// sits further over in your rack
bracket_gap = 0.3;
// the wall: up the panel's left edge, clear of the front board (x from 1.55)
bracket_wall_x = 0.2;
bracket_wall_t = 1.1;
// the 500 rack's rails cover the panel back above and below the 118.42 mm opening
rack_opening = 118.42;
// the ears stay this far behind the panel, clear of the front board (12.2 mm to its back
// face) and the lead ends on it: trim those flush near the ears
ear_front = 15.0;
// ear length along the board, each side of its hole
ear_half = 6.0;
// past each hole, away from the panel
ear_back = 5.0;
// screw clearance, as a slot along the depth so the board can sit a little nearer or
// further: the captive nut slides in its slot to suit
screw_d = 3.4;
screw_slot = 3.0;
// M3 nut: across flats and thickness, plus clearance
nut_af = 5.5;
nut_t = 2.4;
nut_clear = 0.3;
// plastic between the board face and the nut
nut_wall = 1.5;

/* [Fit test strip] */
fit_y0 = 36;
fit_y1 = 63;

$fn = 96;
eps = 0.01;

// panel coordinates (y down from the top-left of the front) to model coordinates
// (y up, front face on top at z = thk). The print orientation flips it at the end.
function P(x, y) = [x, H - y];

// ------------------------------------------------------------------ legend
// OpenSCAD's size is close to the font's ascent; the mockup's numbers are SVG font
// sizes. 0.8 brings the cap heights level with the mockup at legend_scale 1.
module legend_2d() {
    for (t = LEGENDS) {
        a = t[4] == "start" ? "left" : t[4] == "end" ? "right" : "center";
        translate(P(t[1], t[2]))
            scale([legend_condense, 1])
                offset(delta = legend_bold)
                    text(t[0], size = t[3] * 0.8 * legend_scale, font = legend_font,
                         halign = a, valign = "baseline", spacing = legend_spacing);
    }
    if (ticks)
        for (p = POTS) {
            r0 = p[4] / 2 + tick_gap;
            // the mockup's scale runs 270 degrees from bottom left over the top
            for (a = [135, 270, 405])
                translate(P(p[1], p[2]))
                    rotate(-a)
                        translate([r0, -tick_w / 2]) square([tick_len, tick_w]);
        }
}

module legend_body() {
    translate([0, 0, thk - legend_depth])
        linear_extrude(legend_depth + eps) legend_2d();
}

// ------------------------------------------------------------------ blank
module rounded_rect(w, h, r) {
    offset(r = r) offset(delta = -r) square([w, h]);
}

module blank() {
    x0 = (W - trim_w) / 2;
    y0 = (H - trim_h) / 2;
    translate([x0, y0, 0])
        hull() {
            linear_extrude(thk - edge_chamfer) rounded_rect(trim_w, trim_h, corner_r);
            linear_extrude(thk)
                translate([edge_chamfer, edge_chamfer])
                    rounded_rect(trim_w - 2 * edge_chamfer, trim_h - 2 * edge_chamfer,
                                 max(corner_r - edge_chamfer, 0.01));
        }
}

// ------------------------------------------------------------------ holes
// a through hole of diameter d, chamfered c deep on the front face
module through(x, y, d, c = hole_chamfer) {
    translate(concat(P(x, y), [-1])) {
        cylinder(d = d, h = thk + 2);
        translate([0, 0, 1 + thk - c]) cylinder(d1 = d, d2 = d + 2 * c + 2 * eps, h = c + eps);
    }
}

// depth of the slot the LED bases sit in, from the back face
led_slot_h = min(max(thk - led_tower_h - led_proud + led_slot_extra, 0), thk - led_min_web);

// one slot along each meter column, as wide as an LED base: at a 3.0 mm pitch the bases
// are only 0.5 mm apart, too little to leave plastic between separate pockets
module led_slots() {
    if (led_slot_h > 0)
        for (i = [0 : len(LEDS) - 1]) if (i == 0 || LEDS[i][1] != LEDS[i - 1][1]) {
            x = LEDS[i][1];
            ys = [for (l = LEDS) if (l[1] == x) l[2]];
            w = led_base_w + led_base_clear;
            slot_len = max(ys) - min(ys) + led_base_l + led_base_clear;
            translate([x - w / 2, H - max(ys) - (led_base_l + led_base_clear) / 2, -1])
                cube([w, slot_len, 1 + led_slot_h]);
        }
}

module holes() {
    for (p = POTS) through(p[1], p[2], p[3] + hole_comp);
    for (s = SWITCHES) through(s[1], s[2], s[3] + hole_comp);
    for (l = LEDS) through(l[1], l[2], led_tower_d + led_comp, 0);
    led_slots();
    for (p = retainer_pins())
        translate(concat(P(p[0], p[1]), [-1]))
            cylinder(d = retainer_pin_d + retainer_pin_fit, h = 1 + retainer_pin_h + 0.2);
    for (m = MTG) {
        d = MTG_D + hole_comp;
        // 82 degree countersink on the front face
        csk_h = (CSINK_D - d) / 2 / tan(41);
        through(m[0], m[1], d, 0);
        // the cone starts just inside the hole, so its edge never lands on the
        // hole's own edge (which leaves a non-manifold seam in the mesh)
        sink = 0.05;
        translate(concat(P(m[0], m[1]), [thk - csk_h - sink]))
            cylinder(d1 = d - 2 * sink * tan(41), d2 = CSINK_D + 2 * eps * tan(41),
                     h = csk_h + sink + eps);
    }
}

module plate() {
    difference() {
        blank();
        holes();
        legend_body();
    }
}

module panel() {
    plate();
    if (bracket) main_board_bracket();
}

module legend() {
    intersection() {
        blank();
        difference() { legend_body(); holes(); }
    }
}

// ------------------------------------------------------------------ LED retainer
// the meter columns' x, and the first and last LED's y in each
function led_cols() = [for (i = [0 : len(LEDS) - 1])
                         if (i == 0 || LEDS[i][1] != LEDS[i - 1][1]) LEDS[i][1]];
function led_ys(x) = [for (l = LEDS) if (l[1] == x) l[2]];
// halfway between the columns, level with the top and bottom LEDs
function retainer_pins() = let(c = led_cols(), ys = led_ys(c[0]))
    [[(c[0] + c[len(c) - 1]) / 2, min(ys)], [(c[0] + c[len(c) - 1]) / 2, max(ys)]];

// in model coordinates: the plate against the back face (z below 0), the ribs and pins
// pointing up into the panel
module retainer() {
    sw = led_base_w + led_base_clear;
    sl = led_base_l + led_base_clear;
    rib_h = led_slot_h - led_slot_extra - led_base_h + retainer_press;
    assert(rib_h > 0, "the LED bases stand out of their slots; deepen them or thin the plate");
    c = led_cols();
    ys = led_ys(c[0]);
    x0 = min(c) - sw / 2 - retainer_margin;
    x1 = max(c) + sw / 2 + retainer_margin;
    y0 = min(ys) - sl / 2 - retainer_margin;
    y1 = max(ys) + sl / 2 + retainer_margin;
    difference() {
        union() {
            translate([x0, H - y1, -retainer_t])
                linear_extrude(retainer_t) rounded_rect(x1 - x0, y1 - y0, 1);
            for (x = c)
                translate([x - sw / 2 + retainer_rib_clear,
                           H - max(ys) - sl / 2 + retainer_rib_clear, -eps])
                    cube([sw - 2 * retainer_rib_clear,
                          max(ys) - min(ys) + sl - 2 * retainer_rib_clear, rib_h + eps]);
            for (p = retainer_pins())
                translate(concat(P(p[0], p[1]), [-eps]))
                    cylinder(d = retainer_pin_d, h = retainer_pin_h + eps, $fn = 48);
        }
        for (l = LEDS, s = [-1, 1])
            translate(concat(P(l[1] + s * lead_pitch / 2, l[2]), [-retainer_t - 1]))
                cylinder(d = lead_hole_d, h = retainer_t + rib_h + 2, $fn = 24);
    }
}

// ------------------------------------------------------------------ main board bracket
// In model coordinates, behind the panel is z < 0. Printed face down, the wall and ears
// stand up off the back; the ears' undersides slope at 45 degrees, so no supports.
module main_board_bracket() {
    face = W / 2 - board_offset - board_t / 2 - bracket_gap;  // the ears' board-side face
    x0 = bracket_wall_x;
    x1 = x0 + bracket_wall_t;
    depth = board_setback + max([for (h = board_holes) h[1]]) + ear_back;
    y_top = (H - rack_opening) / 2 + 0.3;
    y_bot = H - y_top;
    difference() {
        union() {
            translate([x0, H - y_bot, -depth]) cube([x1 - x0, y_bot - y_top, depth + eps]);
            for (h = board_holes) {
                y = board_top + h[0];
                // the ear's cross-section in x and depth, swept along the board
                translate([0, H - y + ear_half, 0]) rotate([90, 0, 0])
                    linear_extrude(2 * ear_half)
                        polygon([[x1 - eps, -ear_front], [face, -ear_front - (face - x1)],
                                 [face, -depth], [x1 - eps, -depth]]);
            }
        }
        for (h = board_holes) {
            y = board_top + h[0];
            z = -(board_setback + h[1]);
            // screw slot, along the depth
            translate([x0 - 1, H - y, z]) rotate([0, 90, 0])
                hull() for (dz = [-screw_slot / 2, screw_slot / 2])
                    translate([-dz, 0, 0]) cylinder(d = screw_d, h = face - x0 + 2, $fn = 32);
            // nut slot, open at the back so the nut drops in and slides to suit
            translate([face - nut_wall - nut_t - nut_clear, H - y - (nut_af + nut_clear) / 2,
                       -depth - 1])
                cube([nut_t + nut_clear, nut_af + nut_clear,
                      depth + 1 + z + screw_slot / 2 + (nut_af + nut_clear) / 2]);
        }
    }
}

// ------------------------------------------------------------------ fit test
module fit_window() {
    translate([-1, H - fit_y1, -1]) cube([W + 2, fit_y1 - fit_y0, thk + 2]);
}

// ------------------------------------------------------------------ output
// flipped face down, with the panel's top edge at +y and its corner at the origin
module print_orient() {
    translate([W, 0, thk]) rotate([0, 180, 0]) children();
}

if (part == "preview") {
    color("#2a2f33") panel();
    color("#f2efe7") translate([0, 0, 0.02]) legend();  // lifted clear of the face
} else if (part == "retainer") {
    // flat on the bed, ribs and pins up
    translate([0, 0, retainer_t]) retainer();
} else print_orient()
    if (part == "panel") panel();
    else if (part == "legend") legend();
    else if (part == "fit_test") intersection() { plate(); fit_window(); }
    else if (part == "fit_legend") intersection() { legend(); fit_window(); }
