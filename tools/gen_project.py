#!/usr/bin/env python3
"""
gen_project.py - build the compressor schematic as a real hierarchical project:
one sheet per section, parts placed by role, wires routed, then verified.

Sheets mirror the drawn documentation:

    1 Connector   2 Input   3 VCA   4 Output   5 Sidechain   6 Power

Nets that stay inside one sheet are drawn as wire. Nets that cross sheets become
global labels. Rails and grounds become power symbols, which are global in KiCad
anyway, so they need no labels at all.

As with route_sch.py, nothing is trusted: after writing the files it asks
kicad-cli for the netlist of the whole hierarchy, diffs it against design.py, and
demotes any net that came out wrong to a label before trying again.

Usage:  python3 gen_project.py [-d outdir] [--fanout N] [--passes N]
"""
import argparse, os, collections, uuid, datetime, subprocess
import sexp, design, place
from sexp import Q, dumps
from route_sch import (sym, pins_of, place_pin, outward, label_angle, Part,
                       load_parts, Router, merge_runs, split_at_vertices,
                       net_is_connected, junctions_for, RAILS, GROUNDS, GRID, KC)

NS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
# FROZEN IDENTIFIER - not a display name. Every uuid in the drawn sheets derives from this
# prefix. Change it and regenerated uuids stop matching the sheets on disk: sheet-symbol
# instance paths break and KiCad silently drops the connections. Rename the project freely,
# never this string.
def U(s): return str(uuid.uuid5(NS, 'steer500p:' + s))
ROOT = U('root')
PROJ = 'UTS Mini Mixing Desk - Compressor'
STUB = 2

SHEETS = [
    ('connector', '1 Connector',  ['CONNECTOR']),
    ('input',     '2 Input',      ['SH1 INPUT RECEIVER AND PAD']),
    ('vca',       '3 VCA',        ['SH2 STEERING VCA AND RECOVERY AMP']),
    ('output',    '4 Output',     ['SH3 MAKEUP, OUTPUT DRIVERS AND AUX']),
    ('sidechain', '5 Sidechain',  ['SH4 SIDECHAIN DETECTOR']),
    ('power',     '6 Power',      ['SH5 POWER, REFERENCES AND METER',
                                   'SH5 SUPPLY DECOUPLING']),
    ('meters',    '7 Meters',     ['SH6 LED METERS']),
]
BLOCK2SHEET = {b: k for k, _, bs in SHEETS for b in bs}


def sheet_symbol(o, key, title, x, y, page):
    o.append('\t(sheet (at %.2f %.2f) (size 44.45 25.4)' % (x, y))
    o.append('\t\t(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))')
    o.append('\t\t(uuid "%s")' % U('sheet.' + key))
    o.append('\t\t(property "Sheetname" %s (at %.2f %.2f 0)'
             ' (effects (font (size 1.27 1.27)) (justify left bottom)))'
             % (dumps(Q(title)), x, y - 0.7))
    o.append('\t\t(property "Sheetfile" %s (at %.2f %.2f 0)'
             ' (effects (font (size 1.27 1.27)) (justify left top)))'
             % (dumps(Q(key + '.kicad_sch')), x, y + 26.1))
    o.append('\t\t(instances (project %s (path "/%s" (page "%d"))))'
             % (dumps(Q(PROJ)), ROOT, page))
    o.append('\t)')


def emit_symbol(o, p, path_uuid, hide=False, uid=None, refname=None, value=None):
    ref = refname or p.ref
    sid = uid or U('%s.%s' % (ref, p.unit))
    o.append('\t(symbol')
    o.append('\t\t(lib_id "%s:%s") (at %.2f %.2f %d) (unit %d)'
             % (p.lib, p.name, p.X, p.Y, p.rot, p.unit))
    o.append('\t\t(exclude_from_sim no) (in_bom %s) (on_board %s) (dnp no)'
             % ('no' if hide else 'yes', 'no' if hide else 'yes'))
    o.append('\t\t(uuid "%s")' % sid)
    h = ' (hide yes)' if hide else ''
    # Keep text off the body: beside a vertical part, above/below a horizontal one,
    # and clear of the triangle on an op amp.
    if p.name == 'NE5532':
        rx, ry, vx, vy = p.X - 6.35, p.Y - 12.7, p.X - 6.35, p.Y - 10.16
    elif p.rot in (90, 270):
        rx, ry, vx, vy = p.X - 5.08, p.Y - 3.18, p.X - 5.08, p.Y + 4.45
    else:
        rx, ry, vx, vy = p.X + 3.81, p.Y - 1.27, p.X + 3.81, p.Y + 1.9
    o.append('\t\t(property "Reference" %s (at %.2f %.2f 0)'
             ' (effects (font (size 1.27 1.27)) (justify left)%s))'
             % (dumps(Q(ref)), rx, ry, h))
    o.append('\t\t(property "Value" %s (at %.2f %.2f 0)'
             ' (effects (font (size 1.27 1.27)) (justify left)%s))'
             % (dumps(Q(value if value is not None else p.value)), vx, vy, h))
    o.append('\t\t(property "Footprint" %s (at %.2f %.2f 0)'
             ' (effects (font (size 1.27 1.27)) (hide yes)))' % (dumps(Q(p.fp)), p.X, p.Y))
    o.append('\t\t(property "Datasheet" "" (at %.2f %.2f 0)'
             ' (effects (font (size 1.27 1.27)) (hide yes)))' % (p.X, p.Y))
    for pn in p.pins:
        o.append('\t\t(pin "%s" (uuid "%s"))' % (pn, U('%s.%s.%s.pin' % (ref, p.unit, pn))))
    o.append('\t\t(instances (project %s (path "/%s/%s" (reference %s) (unit %d))))'
             % (dumps(Q(PROJ)), ROOT, path_uuid, dumps(Q(ref)), p.unit))
    o.append('\t)')


class Fake:
    """A minimal part stand-in so power/ground symbols reuse emit_symbol()."""
    def __init__(self, lib, name, X, Y, rot, pins, fp=''):
        self.lib, self.name, self.X, self.Y, self.rot = lib, name, X, Y, rot
        self.pins, self.fp, self.unit, self.value, self.ref = pins, fp, 1, '', ''


def build_sheet(key, title, parts, kind, sheet_uuid, path_uuid, force_label, fanout):
    """Place, route and write one sheet. Returns (path, stats)."""
    if key == 'power':
        W, H, headings = place.place_power_sheet(parts, kind)
    else:
        W, H, headings = place.place_sheet(parts, kind)
    gw, gh = int(W / GRID) + 20, int(H / GRID) + 20
    R = Router(gw, gh)
    for p in parts: R.block_body(p)

    stub_geo = collections.defaultdict(list)
    plain, terms = [], collections.defaultdict(list)
    rails, gnds, lbls, glbls, ncs = [], [], [], [], []
    for p in parts:
        geo = pins_of(p.lib, p.name, p.unit)
        for pn, net in p.pins.items():
            px, py, ang = geo[pn][0], geo[pn][1], geo[pn][2]
            mx, my = place_pin(px, py, p.X, p.Y, p.rot)
            n0 = (int(round(mx / GRID)), int(round(my / GRID)))
            v = outward(ang, p.rot)
            n1 = (n0[0] + v[0] * STUB, n0[1] + v[1] * STUB)
            k = kind[net]
            if k == 'nc':
                ncs.append(n0); continue
            axis = 'H' if v[0] else 'V'
            for a in range(STUB + 1):
                nn = (n0[0] + v[0] * a, n0[1] + v[1] * a)
                if a in (0, STUB): R.mark_vertex(nn, net)
                else:              R.mark_pass(nn, net, axis)
            stub_geo[net].append((n0, n1))
            if   k == 'rail':   rails.append((n1, net, v)); plain.append((n0, n1))
            elif k == 'gnd':    gnds.append((n1, net, v));  plain.append((n0, n1))
            elif k == 'global': glbls.append((n1, net, v)); plain.append((n0, n1))
            elif k == 'label':  lbls.append((n1, net, v));  plain.append((n0, n1))
            else:               terms[net].append(n1)

    segs_by_net, failed = {}, []
    def span(n):
        ns = terms[n]
        return max(abs(a[0]-b[0]) + abs(a[1]-b[1]) for a in ns for b in ns)
    for net in sorted(terms, key=span, reverse=True):
        ns = terms[net]
        if len(ns) < 2: continue
        tree, segs, ok = {ns[0]}, [], True
        for t in ns[1:]:
            if t in tree: continue
            path = R.route([t], tree, net)
            if path is None: ok = False; break
            R.commit(path, net); segs += merge_runs(path); tree.update(path)
        if ok and not all(t in tree for t in ns): ok = False
        if ok:
            allsegs = split_at_vertices(segs + stub_geo[net])
            if net_is_connected(allsegs, [a for a, _ in stub_geo[net]]):
                segs_by_net[net] = allsegs
            else: ok = False
        if not ok:
            failed.append(net)
            for a, b in stub_geo[net]:
                plain.append((a, b)); lbls.append((b, net, (1, 0)))

    jn = set()
    for segs in segs_by_net.values(): jn |= junctions_for(segs)

    o = ['(kicad_sch', '\t(version 20250114)', '\t(generator "uts-compressor-gen")',
         '\t(generator_version "9.0")', '\t(uuid "%s")' % sheet_uuid,
         '\t(paper "User" %.2f %.2f)' % (max(W, 200), max(H, 150)),
         '\t(title_block (title %s) (date "%s") (rev "A") (company "UTS Mini Mixing Desk"))'
         % (dumps(Q(PROJ)), datetime.date.today().isoformat())]
    used = {('%s:%s' % (p.lib, p.name)): (p.lib, p.name) for p in parts}
    for _, n, _ in rails: used['power:' + RAILS[n]] = ('power', RAILS[n])
    for _, n, _ in gnds:  used['power:' + GROUNDS[n]] = ('power', GROUNDS[n])
    if key == 'power': used['power:PWR_FLAG'] = ('power', 'PWR_FLAG')
    o.append('\t(lib_symbols')
    for k2 in sorted(used): o.append('\t\t' + dumps(sym(*used[k2])))
    o.append('\t)')

    for p in parts: emit_symbol(o, p, path_uuid)

    ROT = {(0, 1): 0, (0, -1): 180, (1, 0): 270, (-1, 0): 90}
    for i, (node, net, v) in enumerate(gnds):
        f = Fake('power', GROUNDS[net], node[0]*GRID, node[1]*GRID, ROT[v], {'1': net})
        emit_symbol(o, f, path_uuid, hide=True, uid=U('%s.g%d' % (key, i)),
                    refname='#PWR%s%03d' % (key[:2].upper(), i), value=net)
    for i, (node, net, v) in enumerate(rails):
        f = Fake('power', RAILS[net], node[0]*GRID, node[1]*GRID,
                 ROT[(-v[0], -v[1])], {'1': net})
        emit_symbol(o, f, path_uuid, hide=True, uid=U('%s.r%d' % (key, i)),
                    refname='#PWR%sR%03d' % (key[:2].upper(), i), value=net)

    for a, b in plain:
        o.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0)'
                 ' (type default)) (uuid "%s"))'
                 % (a[0]*GRID, a[1]*GRID, b[0]*GRID, b[1]*GRID,
                    U('%s.s%d.%d.%d.%d' % (key, a[0], a[1], b[0], b[1]))))
    for net, segs in segs_by_net.items():
        for a, b in segs:
            o.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0)'
                     ' (type default)) (uuid "%s"))'
                     % (a[0]*GRID, a[1]*GRID, b[0]*GRID, b[1]*GRID,
                        U('%s.w%s.%d.%d.%d.%d' % (key, net, a[0], a[1], b[0], b[1]))))
    for pt in sorted(jn):
        o.append('\t(junction (at %.2f %.2f) (diameter 0) (color 0 0 0 0) (uuid "%s"))'
                 % (pt[0]*GRID, pt[1]*GRID, U('%s.j%d.%d' % (key, pt[0], pt[1]))))
    for node, net, v in glbls:
        o.append('\t(global_label %s (shape bidirectional) (at %.2f %.2f %d)'
                 ' (effects (font (size 1.27 1.27)) (justify left)) (uuid "%s"))'
                 % (dumps(Q(net)), node[0]*GRID, node[1]*GRID, label_angle(v),
                    U('%s.gl%s.%d.%d' % (key, net, node[0], node[1]))))
    for node, net, v in lbls:
        o.append('\t(label %s (at %.2f %.2f %d) (effects (font (size 1.27 1.27))'
                 ' (justify left bottom)) (uuid "%s"))'
                 % (dumps(Q(net)), node[0]*GRID, node[1]*GRID, label_angle(v),
                    U('%s.l%s.%d.%d' % (key, net, node[0], node[1]))))
    for node in ncs:
        o.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))'
                 % (node[0]*GRID, node[1]*GRID, U('%s.nc%d.%d' % (key, node[0], node[1]))))
    if key == 'power':
        # ERC wants every power net driven by something. The rails arrive on a
        # connector, not from a regulator, so flag them explicitly.
        for i, net in enumerate(['+16V', '-16V', 'AGND', '-5V1', 'PGND', 'CHASSIS']):
            fx, fy = 25.4 + i * 25.4, H - 12.7
            f = Fake('power', 'PWR_FLAG', fx, fy, 0, {'1': net})
            emit_symbol(o, f, path_uuid, hide=True, uid=U('flag.%d' % i),
                        refname='#FLG%03d' % i, value='PWR_FLAG')
            o.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0)'
                     ' (type default)) (uuid "%s"))' % (fx, fy, fx, fy - 5.08, U('flagw%d' % i)))
            o.append('\t(global_label %s (shape bidirectional) (at %.2f %.2f 90)'
                     ' (effects (font (size 1.27 1.27)) (justify left)) (uuid "%s"))'
                     % (dumps(Q(net)), fx, fy - 5.08, U('flagl%d' % i)))
    for hx, hy, ht in headings:
        o.append('\t(text %s (at %.2f %.2f 0) (effects (font (size 2.2 2.2) (bold yes))'
                 ' (justify left bottom)) (uuid "%s"))'
                 % (dumps(Q(ht)), hx, hy, U('%s.h%s' % (key, ht))))
    o.append('\t(embedded_fonts no)')
    o.append(')')
    return '\n'.join(o) + '\n', {'wired': len(segs_by_net), 'failed': failed,
                                 'gnd': len(gnds), 'rail': len(rails),
                                 'global': len(set(n for _, n, _ in glbls)),
                                 'label': len(set(n for _, n, _ in lbls))}


def build(outdir, force_label=frozenset(), fanout=6):
    os.makedirs(outdir, exist_ok=True)
    parts = load_parts()
    for p in parts:
        p.sheet = BLOCK2SHEET[p.block]

    # net -> which sheets touch it
    sheets_of = collections.defaultdict(set)
    fan = collections.Counter()
    for p in parts:
        for net in p.pins.values():
            sheets_of[net].add(p.sheet); fan[net] += 1

    kind = {}
    for net in fan:
        if   net in design.NO_CONNECT:  kind[net] = 'nc'
        elif net in RAILS:              kind[net] = 'rail'
        elif net in GROUNDS:            kind[net] = 'gnd'
        elif len(sheets_of[net]) > 1:   kind[net] = 'global'
        elif fan[net] > fanout:         kind[net] = 'label'
        else:                           kind[net] = 'wire'
    for n in force_label:
        if kind.get(n) == 'wire': kind[n] = 'label'

    stats = {}
    for page, (key, title, _blocks) in enumerate(SHEETS, start=2):
        sp = [p for p in parts if p.sheet == key]
        # the sub-sheet file has its own uuid; symbol instance paths must instead
        # name the SHEET SYMBOL's uuid in the parent, or KiCad ignores the sheet
        txt, st = build_sheet(key, title, sp, kind, U('sub.' + key),
                              U('sheet.' + key), force_label, fanout)
        open(os.path.join(outdir, key + '.kicad_sch'), 'w').write(txt)
        stats[key] = dict(st, parts=len(sp))

    o = ['(kicad_sch', '\t(version 20250114)', '\t(generator "uts-compressor-gen")',
         '\t(generator_version "9.0")', '\t(uuid "%s")' % ROOT, '\t(paper "A3")',
         '\t(title_block (title "UTS Mini Mixing Desk - Compressor") (date "%s") (rev "A")'
         ' (company "500-series module"))' % datetime.date.today().isoformat(),
         '\t(lib_symbols)']
    for i, (key, title, _b) in enumerate(SHEETS):
        sheet_symbol(o, key, title, 30.0 + (i % 3) * 76.2, 40.0 + (i // 3) * 50.8, i + 2)
    o.append('\t(text "UTS Mini Mixing Desk - Compressor - one sheet per section" (at 30 25 0)'
             ' (effects (font (size 3 3) (bold yes)) (justify left bottom)) (uuid "%s"))'
             % U('roottext'))
    o.append('\t(sheet_instances')
    o.append('\t\t(path "/" (page "1"))')
    o.append('\t)')
    o.append('\t(embedded_fonts no)')
    o.append(')')
    root = os.path.join(outdir, PROJ + '.kicad_sch')
    open(root, 'w').write('\n'.join(o) + '\n')

    pro = os.path.join(outdir, PROJ + '.kicad_pro')
    if not os.path.exists(pro):
        import json
        open(pro, 'w').write(json.dumps({
            "board": {"design_settings": {"defaults": {}, "rules": {}}},
            "boards": [], "cvpcb": {"equivalence_files": []},
            "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
            "meta": {"filename": PROJ + ".kicad_pro", "version": 3},
            "net_settings": {"classes": [{"name": "Default", "clearance": 0.2,
                                          "track_width": 0.25}], "meta": {"version": 4}},
            "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
            "schematic": {"legacy_lib_dir": "", "legacy_lib_list": [],
                          "meta": {"version": 1}},
            "sheets": [[ROOT, "Root"]] + [[U('sheet.' + k), t] for k, t, _ in SHEETS],
            "text_variables": {}}, indent=2) + '\n')
    return root, stats


def check(root):
    net = root.replace('.kicad_sch', '.net')
    r = subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                        '-o', net, root], capture_output=True, text=True)
    if not os.path.exists(net):
        raise RuntimeError('kicad-cli failed:\n' + r.stderr[-800:])
    node, _ = sexp.parse_one(sexp.tokenize(open(net).read()))
    got = {}
    for n in sexp.getall(sexp.get(node, 'nets'), 'net'):
        nm = str(sexp.get(n, 'name')[1])
        nm = nm.rsplit('/', 1)[-1] if nm.startswith('/') else nm
        got[nm] = {(str(sexp.get(x, 'ref')[1]), str(sexp.get(x, 'pin')[1]))
                   for x in sexp.getall(n, 'node')}
    want = {}
    for p in design.PARTS:
        if p[0].startswith('#'): continue
        for pn, nt in p[6].items():
            if nt in design.NO_CONNECT: continue
            want.setdefault(nt, set()).add((p[0], pn))
    gs = {frozenset(v): k for k, v in got.items()}
    bad = set()
    for nt, pinset in want.items():
        if frozenset(pinset) in gs: continue
        bad.add(nt)
        for nm, mem in got.items():
            if mem & pinset:
                for other, opins in want.items():
                    if opins & mem: bad.add(other)
    ncomp = len(sexp.getall(sexp.get(node, 'components'), 'comp'))
    return bad, ncomp, len(want)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # NOT 'kicad': this regenerates every sheet and would destroy hand-drawn layout.
    ap.add_argument('-d', '--outdir', default='regenerated')
    ap.add_argument('--fanout', type=int, default=6)
    ap.add_argument('--passes', type=int, default=6)
    args = ap.parse_args()

    forced = set()
    for i in range(1, args.passes + 1):
        root, stats = build(args.outdir, forced, args.fanout)
        bad, ncomp, nnets = check(root)
        bad -= forced
        print('pass %d: %d/%d nets ok, %d to fix' % (i, nnets - len(bad), nnets, len(bad)))
        if not bad: break
        forced |= bad
        print('   ->', ', '.join(sorted(bad)))
    print()
    print('%-11s %5s %6s %5s %5s %7s %6s' %
          ('sheet', 'parts', 'wired', 'gnd', 'rail', 'global', 'label'))
    for k, t, _ in SHEETS:
        s = stats[k]
        print('%-11s %5d %6d %5d %5d %7d %6d'
              % (t, s['parts'], s['wired'], s['gnd'], s['rail'], s['global'], s['label']))
    print('\ncomponents %d, nets %d' % (ncomp, nnets))
    print('->', root)


if __name__ == '__main__':
    main()
