#!/usr/bin/env python3
"""STEP models for the Jaycar ST0300 (SPDT) and ST0310 (DPDT) sub-miniature toggles.

Jaycar publishes no 3D models, so these are simple solids built to the ST0300 datasheet:
an 8.13 x 5.08 x 8.64 mm case (9.4 mm wide for the DPDT, which has no published drawing),
a 10-48 UNS bushing 4.06 mm long, a 2.54 mm lever and 0.76 x 1.52 mm solder lugs. Good
enough for clearances and the Fusion 360 assembly, not a replacement for the real part.

The origin is the bushing centre on the board surface, matching the footprints in
kicad_withpcb/compressor_front/compressor_front.pretty.

Run: python3 tools/make_toggle_models.py   (writes kicad_withpcb/compressor_front/3dmodels/)
"""
import math, os, datetime

class Step:
    def __init__(self):
        self.lines = []; self.n = 0
    def add(self, s):
        self.n += 1; self.lines.append('#%d=%s;' % (self.n, s)); return '#%d' % self.n

def f(v): return ('%.6f' % v).rstrip('0').rstrip('.') + ('' if '.' in ('%.6f' % v).rstrip('0').rstrip('.') else '.')

def prism(poly, z0, z1):
    """Vertices and outward-facing faces of a straight prism over a CCW polygon."""
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return verts, faces

def box(x0, y0, x1, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)

def cyl(cx, cy, r, z0, z1, seg=24):
    return prism([(cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)], z0, z1)

def write(path, name, parts):
    s = Step()
    ctx_unit_mm = s.add("(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))")
    rad = s.add("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    sr = s.add("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    unc = s.add("UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-06),%s,'distance_accuracy_value','')" % ctx_unit_mm)
    ctx = s.add("(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((%s)) "
                "GLOBAL_UNIT_ASSIGNED_CONTEXT((%s,%s,%s)) REPRESENTATION_CONTEXT('',''))" % (unc, ctx_unit_mm, rad, sr))
    o = s.add("CARTESIAN_POINT('',(0.,0.,0.))"); dz = s.add("DIRECTION('',(0.,0.,1.))"); dx = s.add("DIRECTION('',(1.,0.,0.))")
    axis = s.add("AXIS2_PLACEMENT_3D('',%s,%s,%s)" % (o, dz, dx))
    solids, styled = [], []
    for label, (verts, faces), rgb in parts:
        vp = []
        for v in verts:
            p = s.add("CARTESIAN_POINT('',(%s,%s,%s))" % tuple(f(c) for c in v)); vp.append((s.add("VERTEX_POINT('',%s)" % p), p))
        edges = {}
        def edge(a, b):
            key = (min(a, b), max(a, b))
            if key not in edges:
                pa, pb = verts[key[0]], verts[key[1]]
                d = [pb[i] - pa[i] for i in range(3)]; L = math.sqrt(sum(c * c for c in d))
                di = s.add("DIRECTION('',(%s,%s,%s))" % tuple(f(c / L) for c in d))
                vec = s.add("VECTOR('',%s,%s)" % (di, f(L)))
                line = s.add("LINE('',%s,%s)" % (vp[key[0]][1], vec))
                edges[key] = s.add("EDGE_CURVE('',%s,%s,%s,.T.)" % (vp[key[0]][0], vp[key[1]][0], line))
            return edges[key], '.T.' if a < b else '.F.'
        fl = []
        for fc in faces:
            oe = []
            for i in range(len(fc)):
                e, sense = edge(fc[i], fc[(i + 1) % len(fc)])
                oe.append(s.add("ORIENTED_EDGE('',*,*,%s,%s)" % (e, sense)))
            loop = s.add("EDGE_LOOP('',(%s))" % ','.join(oe))
            bound = s.add("FACE_OUTER_BOUND('',%s,.T.)" % loop)
            a, b, c = (verts[fc[0]], verts[fc[1]], verts[fc[2]])
            u = [b[i] - a[i] for i in range(3)]; w = [c[i] - b[i] for i in range(3)]
            nrm = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            nl = math.sqrt(sum(x * x for x in nrm)); ul = math.sqrt(sum(x * x for x in u))
            pn = s.add("DIRECTION('',(%s,%s,%s))" % tuple(f(x / nl) for x in nrm))
            pr = s.add("DIRECTION('',(%s,%s,%s))" % tuple(f(x / ul) for x in u))
            plane = s.add("PLANE('',%s)" % s.add("AXIS2_PLACEMENT_3D('',%s,%s,%s)" % (vp[fc[0]][1], pn, pr)))
            fl.append(s.add("ADVANCED_FACE('',(%s),%s,.T.)" % (bound, plane)))
        shell = s.add("CLOSED_SHELL('',(%s))" % ','.join(fl))
        solid = s.add("MANIFOLD_SOLID_BREP('%s',%s)" % (label, shell))
        solids.append(solid)
        col = s.add("COLOUR_RGB('',%s,%s,%s)" % tuple(f(c) for c in rgb))
        fill = s.add("FILL_AREA_STYLE('',(%s))" % s.add("FILL_AREA_STYLE_COLOUR('',%s)" % col))
        side = s.add("SURFACE_SIDE_STYLE('',(%s))" % s.add("SURFACE_STYLE_FILL_AREA(%s)" % fill))
        psa = s.add("PRESENTATION_STYLE_ASSIGNMENT((%s))" % s.add("SURFACE_STYLE_USAGE(.BOTH.,%s)" % side))
        styled.append(s.add("STYLED_ITEM('color',(%s),%s)" % (psa, solid)))
    rep = s.add("ADVANCED_BREP_SHAPE_REPRESENTATION('%s',(%s,%s),%s)" % (name, ','.join(solids), axis, ctx))
    s.add("MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',(%s),%s)" % (','.join(styled), ctx))
    app = s.add("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
    s.add("APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,%s)" % app)
    pc = s.add("PRODUCT_CONTEXT('',%s,'mechanical')" % app)
    prod = s.add("PRODUCT('%s','%s','',(%s))" % (name, name, pc))
    pdf = s.add("PRODUCT_DEFINITION_FORMATION('','',%s)" % prod)
    pdc = s.add("PRODUCT_DEFINITION_CONTEXT('part definition',%s,'design')" % app)
    pd = s.add("PRODUCT_DEFINITION('design','',%s,%s)" % (pdf, pdc))
    pds = s.add("PRODUCT_DEFINITION_SHAPE('','',%s)" % pd)
    s.add("SHAPE_DEFINITION_REPRESENTATION(%s,%s)" % (pds, rep))
    head = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('%s'),'2;1');\n"
            "FILE_NAME('%s','%s',(''),(''),'make_toggle_models.py','','');\n"
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n") % (
            name, os.path.basename(path), datetime.date.today().isoformat())
    open(path, 'w').write(head + '\n'.join(s.lines) + '\nENDSEC;\nEND-ISO-10303-21;\n')

CASE, STEEL, NICKEL, CHROME, TIN = (0.55, 0.08, 0.08), (0.62, 0.63, 0.65), (0.78, 0.78, 0.74), (0.85, 0.86, 0.88), (0.80, 0.80, 0.78)
H_CASE, H_BUSH, BUSH_R, LEVER_R, LEVER_L = 8.64, 4.06, 4.83 / 2, 2.54 / 2, 9.40
LUG_W, LUG_T, LUG_L = 1.52, 0.76, 2.80

def toggle(width, lug_cols):
    hw = width / 2
    parts = [('case', box(-hw, -4.065, hw, 4.065, 0.0, H_CASE - 0.6), CASE),
             ('frame', box(-hw - 0.1, -4.165, hw + 0.1, 4.165, H_CASE - 0.6, H_CASE), STEEL),
             ('bushing', cyl(0, 0, BUSH_R, H_CASE, H_CASE + H_BUSH), NICKEL),
             ('lever', cyl(0, 0, LEVER_R, H_CASE + H_BUSH, H_CASE + H_BUSH + LEVER_L, 16), CHROME)]
    for x in lug_cols:
        for y in (-2.54, 0.0, 2.54):
            parts.append(('lug', box(x - LUG_W / 2, y - LUG_T / 2, x + LUG_W / 2, y + LUG_T / 2, -LUG_L, 0.0), TIN))
    return parts

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kicad_withpcb', 'compressor_front', '3dmodels')
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, 'SW_Toggle_SubMini_SPDT_Jaycar_ST0300.step'), 'SW_Toggle_SubMini_SPDT_Jaycar_ST0300', toggle(5.08, [0.0]))
    write(os.path.join(out, 'SW_Toggle_SubMini_DPDT_Jaycar_ST0310.step'), 'SW_Toggle_SubMini_DPDT_Jaycar_ST0310', toggle(9.40, [-2.35, 2.35]))
    print('wrote', out)
