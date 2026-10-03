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
// left under each pot nut: the 9 mm pots' 5 mm bushing needs the panel this thin
pot_web = 2.0;
// counterbore on the front round each pot, for the nut and washer; the knob covers it
pot_well_d = 12.5;

/* [Fits] */
// added to the pot, switch and screw holes; FDM holes print undersize
hole_comp = 0.2;
// meter windows; the LEDs sit behind the panel, so these only let the light out
led_d = 2.2;
// chamfer on the bed side of pot, switch and screw holes
hole_chamfer = 0.3;

/* [Legend] */
legend_depth = 0.4;
// 1.0 = the mockup's type sizes, which are too small for a 0.4 mm nozzle
legend_scale = 1.3;
// squeeze the type horizontally to keep the ATTACK / RELEASE row apart
legend_condense = 0.85;
// grows every stroke by this much on each side
legend_bold = 0.05;
legend_font = "Liberation Sans:style=Bold";
// tick marks at the start, middle and end of each pot's travel
ticks = true;
tick_w = 0.5;
tick_len = 1.2;
// gap between the knob skirt and the inner end of a tick
tick_gap = 0.9;

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
                         halign = a, valign = "baseline");
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

module holes() {
    for (p = POTS) {
        through(p[1], p[2], p[3] + hole_comp);
        translate(concat(P(p[1], p[2]), [pot_web])) cylinder(d = pot_well_d, h = thk);
    }
    for (s = SWITCHES) through(s[1], s[2], s[3] + hole_comp);
    for (l = LEDS) through(l[1], l[2], led_d, 0);
    for (m = MTG) {
        d = MTG_D + hole_comp;
        // 82 degree countersink on the front face
        csk_h = (CSINK_D - d) / 2 / tan(41);
        through(m[0], m[1], d, 0);
        translate(concat(P(m[0], m[1]), [thk - csk_h]))
            cylinder(d1 = d, d2 = CSINK_D + 2 * eps * tan(41), h = csk_h + eps);
    }
}

module panel() {
    difference() {
        blank();
        holes();
        legend_body();
    }
}

module legend() {
    intersection() {
        blank();
        difference() { legend_body(); holes(); }
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
} else print_orient()
    if (part == "panel") panel();
    else if (part == "legend") legend();
    else if (part == "fit_test") intersection() { panel(); fit_window(); }
    else if (part == "fit_legend") intersection() { legend(); fit_window(); }
