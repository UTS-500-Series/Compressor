#!/usr/bin/env python3
"""STEP model of the printed faceplate, for CAD (Fusion, FreeCAD, SolidWorks, Onshape).

OpenSCAD only writes meshes, so this rebuilds the same faceplate as a real solid with
CadQuery: true cylinders, cones and fillets, and the legend from the font's own curves.
Every dimension comes from faceplate.scad and panel_data.scad, so it follows any change
to hole_comp, legend_scale and the rest. It writes three files:

    faceplate.step         "panel" with the legend engraved, and "legend", the inlay
                           that fills it
    faceplate-blank.step   the panel with every hole and LED slot but no legend
    faceplate-legend.dxf   the legend as outlines, one layer per label, plus the outline
                           and holes for lining it up

All three are front face up, in faceplate.scad's model coordinates: x right, y up from
the bottom of the nominal 38.10 x 133.35 outline, back face at z = 0, front at z = thk.

Needs: pip install cadquery uharfbuzz, and the Liberation Sans Bold font.
Run:   python3 make_step.py
"""
import json, math, os, re, sys

import cadquery as cq
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from cadquery.occ_impl.exporters.dxf import DxfDocument

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATHS = ['/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
              '/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf',
              '/Library/Fonts/LiberationSans-Bold.ttf',
              os.path.expanduser('~/Library/Fonts/LiberationSans-Bold.ttf')]


# ------------------------------------------------------------------ read the .scad files
def scad_params(path):
    """Top-level `name = literal;` assignments (numbers, strings, booleans)."""
    out = {}
    for m in re.finditer(r'^(\w+)\s*=\s*([^;]+);', open(path).read(), re.M):
        v = m.group(2).split('//')[0].strip()
        try:
            out[m.group(1)] = json.loads(v)
        except ValueError:
            pass
    return out


def scad_data(path):
    """panel_data.scad: scalars and the nested lists, which are JSON once comments go."""
    text = re.sub(r'//[^\n]*', '', open(path).read())
    return {m.group(1): json.loads(m.group(2))
            for m in re.finditer(r'^(\w+)\s*=\s*(.+?);', text, re.M | re.S)}


p = scad_params(os.path.join(HERE, 'faceplate.scad'))
d = scad_data(os.path.join(HERE, 'panel_data.scad'))
W, H = d['W'], d['H']
thk = p['thk']


def P(x, y):
    """Panel coordinates (y down from top-left) to model coordinates (y up)."""
    return (x, H - y)


# ------------------------------------------------------------------ blank
x0, y0 = (W - p['trim_w']) / 2, (H - p['trim_h']) / 2
blank = (cq.Workplane().box(p['trim_w'], p['trim_h'], thk, centered=False)
         .translate((x0, y0, 0))
         .edges('|Z').fillet(p['corner_r'])
         .faces('>Z').edges().chamfer(p['edge_chamfer'])).val()


# ------------------------------------------------------------------ holes
def cyl(x, y, dia, z0, h):
    return cq.Solid.makeCylinder(dia / 2, h, cq.Vector(*P(x, y), z0))


def cone(x, y, d0, z0, half_angle, h):
    """A cone opening upwards from diameter d0 at z0, h tall."""
    return cq.Solid.makeCone(d0 / 2, d0 / 2 + h * math.tan(math.radians(half_angle)), h,
                             cq.Vector(*P(x, y), z0))


def through(x, y, dia, c):
    """Through hole, chamfered c deep at 45 degrees on the front face."""
    s = [cyl(x, y, dia, -1, thk + 2)]
    if c > 0:
        s.append(cone(x, y, dia, thk - c, 45, c + 1))
    return s


comp = p['hole_comp']
cutters = []
for _, x, y, bush, _knob in d['POTS']:
    cutters += through(x, y, bush + comp, p['hole_chamfer'])
for _, x, y, bush in d['SWITCHES']:
    cutters += through(x, y, bush + comp, p['hole_chamfer'])
led_hole = p['led_tower_d'] + p['led_comp']
for _, x, y, _dia in d['LEDS']:
    cutters += through(x, y, led_hole, 0)
# the slot along each meter column that the LED bases' shoulders stop against
slot_h = min(max(thk - p['led_tower_h'] - p['led_proud'], 0), thk - p['led_min_web'])
slot_w = p['led_base_d'] + p['led_base_clear']
if slot_h > 0:
    for x in sorted({l[1] for l in d['LEDS']}):
        ys = [l[2] for l in d['LEDS'] if l[1] == x]
        (_, top), (_, bot) = P(x, min(ys)), P(x, max(ys))
        cutters += [cyl(x, min(ys), slot_w, -1, 1 + slot_h),
                    cyl(x, max(ys), slot_w, -1, 1 + slot_h),
                    cq.Solid.makeBox(slot_w, top - bot, 1 + slot_h,
                                     cq.Vector(x - slot_w / 2, bot, -1))]
for x, y in d['MTG']:
    dia = d['MTG_D'] + comp
    csk_h = (d['CSINK_D'] - dia) / 2 / math.tan(math.radians(41))
    cutters += through(x, y, dia, 0)
    # 82 degree countersink, its cone carried a little into the hole and out past the face
    sink = 0.05
    cutters.append(cone(x, y, dia - 2 * sink * math.tan(math.radians(41)),
                        thk - csk_h - sink, 41, csk_h + sink + 1))


# ------------------------------------------------------------------ legend
font_path = next((f for f in FONT_PATHS if os.path.exists(f)), None)
if not font_path:
    sys.exit('Liberation Sans Bold not found; add its path to FONT_PATHS')
font = TTFont(font_path)
glyphs = font.getGlyphSet()
order = font.getGlyphOrder()
hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(font_path)))
upem = font['head'].unitsPerEm


class Contours(BasePen):
    """Glyph outline as contours of ('L', a, b) and ('Q', a, ctrl, b) segments."""
    def __init__(self, gs):
        super().__init__(gs)
        self.contours, self.cur, self.start = [], None, None

    def _moveTo(self, pt):
        self.contours.append([])
        self.cur = self.start = pt

    def _lineTo(self, pt):
        self.contours[-1].append(('L', self.cur, pt))
        self.cur = pt

    def _qCurveToOne(self, c, pt):
        self.contours[-1].append(('Q', self.cur, c, pt))
        self.cur = pt

    def _closePath(self):
        if self.cur != self.start:
            self._lineTo(self.start)


def signed_area(contour):
    pts = [s[1] for s in contour]
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def inside(pt, contour):
    pts = [s[1] for s in contour]
    x, y, n = pt[0], pt[1], False
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            n = not n
    return n


def wire(contour, f):
    edges = []
    for s in contour:
        q = [cq.Vector(*f(pt), 0) for pt in s[1:]]
        if (q[-1] - q[0]).Length < 1e-9:
            continue
        edges.append(cq.Edge.makeLine(*q) if s[0] == 'L' else cq.Edge.makeBezier(q))
    return cq.Wire.assembleEdges(edges)


def _left(t, dist):
    n = math.hypot(*t)
    return (-t[1] / n * dist, t[0] / n * dist)


def _meet(p, t, q, u):
    """Where the line through p along t crosses the line through q along u (None if
    they're parallel)."""
    den = t[0] * u[1] - t[1] * u[0]
    if abs(den) < 1e-9 * math.hypot(*t) * math.hypot(*u):
        return None
    k = ((q[0] - p[0]) * u[1] - (q[1] - p[1]) * u[0]) / den
    return (p[0] + k * t[0], p[1] + k * t[1])


def grown(contour, dist):
    """The contour moved dist outwards, as OpenSCAD's offset(delta=): every line and
    every control-polygon leg shifts dist to the left (TrueType keeps the ink on the
    right), and corners are mitred where the shifted legs meet. Shifting a quadratic
    Bezier's control polygon is a close approximation of its offset that keeps it a
    Bezier; the whole legend comes out within 0.1% of the area OpenSCAD gives it. A
    segment shorter than the offset can turn round (the tip of the hole in A); it's
    dropped and its neighbours mitred together instead."""
    if dist == 0:
        return contour
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1])
    add = lambda a, b: (a[0] + b[0], a[1] + b[1])
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1]
    t_in = lambda s: sub(s[-1], s[-2]) if s[-1] != s[-2] else sub(s[-1], s[1])
    t_out = lambda s: sub(s[2], s[1]) if s[2] != s[1] else sub(s[-1], s[1])
    segs = list(contour)
    while True:
        # each segment's new start: its shifted start tangent meets the shifted end
        # tangent of the segment before it
        starts = []
        for i, s in enumerate(segs):
            prev = segs[i - 1]
            ti, to = t_in(prev), t_out(s)
            q = add(s[1], _left(to, dist))
            m = _meet(add(prev[-1], _left(ti, dist)), ti, q, to)
            # (a mitre that runs off a long way is a cusp, not a corner)
            starts.append(m if m and math.hypot(*sub(m, s[1])) < 100 * dist else q)
        out = []
        for i, s in enumerate(segs):
            a, b = starts[i], starts[(i + 1) % len(segs)]
            if s[0] == 'L':
                out.append(('L', a, b))
            else:
                c = _meet(a, t_out(s), b, t_in(s))
                if c and dot(sub(c, a), t_out(s)) > 0 and dot(sub(b, c), t_in(s)) > 0:
                    out.append(('Q', a, c, b))
                else:
                    # the offset ate past the control point (a curve running into a
                    # narrow notch, as inside M): what's left is short and straight
                    out.append(('L', a, b))
        bad = [i for i, (o, s) in enumerate(zip(out, segs))
               if dot(sub(o[-1], o[1]), sub(s[-1], s[1])) <= 0]
        if not bad:
            return out
        # drop the shortest and look again: one loose segment can make its neighbour
        # look reversed too
        segs.pop(min(bad, key=lambda i: math.hypot(*sub(segs[i][-1], segs[i][1]))))


def text_faces(txt, size, halign, k):
    """Faces of one line of text, laid out exactly as OpenSCAD 2021's text() does:
    outlines at size * 100/72 per em, advances 2.4% shorter (its 1000/1024 factor)."""
    so = size * 100 / 72 / upem
    sa = so / 1.024
    buf = hb.Buffer()
    buf.add_str(txt)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)
    width = sum(gp.x_advance for gp in buf.glyph_positions) * sa
    xo = {'left': 0, 'center': -width / 2, 'right': -width}[halign]
    faces, pen_x = [], 0.0
    for gi, gp in zip(buf.glyph_infos, buf.glyph_positions):
        pen = Contours(glyphs)
        glyphs[order[gi.codepoint]].draw(pen)
        ox = xo + pen_x + gp.x_offset * sa
        f = lambda pt, ox=ox: (k * (ox + pt[0] * so), pt[1] * so)
        g = lambda c: grown(c, p['legend_bold'] / so)
        # TrueType: outer contours run clockwise, holes anticlockwise
        outers = [c for c in pen.contours if signed_area(c) < 0]
        inners = [c for c in pen.contours if signed_area(c) > 0]
        for o in outers:
            mine = [i for i in inners if inside(i[0][1], o)]
            ow = wire(g(o), f)
            iw = [wire(g(i), f) for i in mine]
            faces.append(cq.Face.makeFromWires(ow, iw))
        pen_x += gp.x_advance * sa
    return faces


# (name, faces) for each label and each pot's ticks, so the DXF can keep them apart
labels = []
for txt, x, y, size, anchor in d['LEGENDS']:
    a = {'start': 'left', 'end': 'right'}.get(anchor, 'center')
    labels.append((txt, [f.translate(cq.Vector(*P(x, y), 0)) for f in
                         text_faces(txt, size * 0.8 * p['legend_scale'], a,
                                    p['legend_condense'])]))
if p['ticks']:
    tw, tl = p['tick_w'], p['tick_len']
    for ref, x, y, _bush, knob in d['POTS']:
        r0 = knob / 2 + p['tick_gap']
        cx, cy = P(x, y)
        faces = []
        for a in (135, 270, 405):
            c, s = math.cos(math.radians(-a)), math.sin(math.radians(-a))
            pts = [(r0, -tw / 2), (r0 + tl, -tw / 2), (r0 + tl, tw / 2), (r0, tw / 2)]
            pts = [cq.Vector(cx + u * c - v * s, cy + u * s + v * c, 0) for u, v in pts]
            faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon(pts, close=True)))
        # named after the pot's label: the nearest one below it on the same centreline
        below = [lg for lg in d['LEGENDS'] if abs(lg[1] - x) < 0.01 and lg[2] > y]
        name = min(below, key=lambda lg: lg[2])[0] if below else ref
        labels.append(('TICKS-' + name, faces))
legend_2d = [f for _, faces in labels for f in faces]


def extrude(z0, h):
    solids = [cq.Solid.extrudeLinear(f.translate(cq.Vector(0, 0, z0)), cq.Vector(0, 0, h))
              for f in legend_2d]
    return solids[0].fuse(*solids[1:]).clean()


depth = p['legend_depth']
engraving = extrude(thk - depth, depth + 1)
panel = blank.cut(*cutters, engraving).clean()
plain = blank.cut(*cutters).clean()
legend = extrude(thk - depth, depth).intersect(blank).cut(*cutters).clean()
if not (panel.isValid() and legend.isValid() and plain.isValid()):
    sys.exit('the model came out invalid; check the legend settings')


# ------------------------------------------------------------------ write
def write_step(path, parts):
    assy = cq.Assembly(name=os.path.splitext(os.path.basename(path))[0])
    for name, shape, colour in parts:
        assy.add(shape, name=name, color=cq.Color(*colour))
    # CAD programs work out the parametric curves themselves; leaving them out halves
    # the file
    cq.exporters.assembly.exportAssembly(assy, path, write_pcurves=False)
    print('wrote', os.path.relpath(path))


def write_dxf(path):
    """The legend for a sketch: each label and each pot's ticks on its own layer, and the
    printed outline, through holes and knobs on reference layers."""
    dxf = DxfDocument()
    # via a Workplane: CadQuery's DXF writer only handles Bezier edges that way
    add = lambda shape, layer: dxf.add_shape(cq.Workplane().add(shape), layer)
    dxf.add_layer('OUTLINE', color=8).add_layer('HOLES', color=8)
    dxf.add_layer('KNOBS', color=9, linetype='DASHED')
    back = [f for f in blank.Faces() if f.Center().z < 1e-6][0]
    add(back.outerWire(), 'OUTLINE')
    circles = [(x, y, bush + comp) for _, x, y, bush, _ in d['POTS']]
    circles += [(x, y, bush + comp) for _, x, y, bush in d['SWITCHES']]
    circles += [(x, y, led_hole) for _, x, y, _ in d['LEDS']]
    circles += [(x, y, d['MTG_D'] + comp) for x, y in d['MTG']]
    for x, y, dia in circles:
        add(cq.Edge.makeCircle(dia / 2, cq.Vector(*P(x, y), 0)), 'HOLES')
    for _, x, y, _, knob in d['POTS']:
        add(cq.Edge.makeCircle(knob / 2, cq.Vector(*P(x, y), 0)), 'KNOBS')
    for name, faces in labels:
        dxf.add_layer(name, color=2 if name.startswith('TICKS') else 7)
        for f in faces:
            add(f, name)
    dxf.document.saveas(path)
    print('wrote', os.path.relpath(path))


if __name__ == '__main__':
    dark, light = (0.165, 0.184, 0.2), (0.949, 0.937, 0.906)
    write_step(os.path.join(HERE, 'faceplate.step'),
               [('panel', panel, dark), ('legend', legend, light)])
    write_step(os.path.join(HERE, 'faceplate-blank.step'), [('panel', plain, dark)])
    write_dxf(os.path.join(HERE, 'faceplate-legend.dxf'))
    for name, s in (('panel', panel), ('legend', legend), ('blank', plain)):
        bb = s.BoundingBox()
        print('%-6s  %8.2f mm3  %4d faces  %.2f x %.2f x %.2f mm'
              % (name, s.Volume(), len(s.Faces()), bb.xlen, bb.ylen, bb.zlen))
