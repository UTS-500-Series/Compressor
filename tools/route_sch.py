#!/usr/bin/env python3
"""
route_sch.py - turn the label-wired compressor schematic into a drawn-wire one.

The approach is the one a human drafter uses, not "route everything":

  * Rails (+16V / -16V / -5V1) become power symbols at each pin.
  * Grounds (AGND / PGND / CHASSIS) become ground symbols at each pin.
  * Any net with more pins than MAX_FANOUT stays a named label - drawing 14
    wires to one node makes a schematic less readable, not more.
  * Everything left - the local signal nets - is drawn as orthogonal wire.

Routing is A* on a 1.27 mm grid with a turn penalty, so paths come out with as
few corners as possible. Occupancy is tracked per *edge*, not per cell, which
is what lets two different nets cross at right angles (legal, no junction dot)
while forbidding them to run collinearly on top of each other (illegal - it
would merge the nets).

Correctness is not assumed. After emitting the file the script asks kicad-cli for
the netlist, diffs it against design.py, and demotes any net that came out wrong
to labels - then does it again until KiCad and the design agree. A net that is
drawn is therefore drawn correctly, and one that could not be is still connected.

One KiCad rule this depends on, found by experiment and worth knowing: KiCad joins
wires only where they share an ENDPOINT. A wire running straight through a point
is NOT connected to a wire ending there, even with a junction dot on it. Every T
must be three segments meeting at a point, which is what split_at_vertices() does.

What this script does not do is place the parts well, and placement - not routing -
is what makes a schematic readable. Parts are laid out on a connectivity-ordered
grid, so the wires are short and orthogonal but the drawing does not read as signal
flow. Treat the output as a correct starting point to drag into shape in Eeschema.

Usage:  python3 route_sch.py [-o out.kicad_sch] [--fanout N] [--turn N] [--passes N]
"""
import argparse, heapq, math, os, uuid, datetime, collections
import sexp
from sexp import Q, dumps, resolve_symbol, symbol_pins
import design

# ----------------------------------------------------------------- parameters
GRID      = 1.27           # mm - every pin in this design lands on it
CELL_W    = 26             # grid units per placement cell (33.0 mm)
CELL_H    = 22             # grid units per placement cell (27.9 mm)
COLS      = 10
MARGIN    = 14             # grid units of border
STUB      = 2              # grid units of escape wire off every pin
TURN_COST = 4              # A* penalty per corner; higher = straighter, longer
MAX_POP   = 120000         # A* expansion cap per connection

RAILS   = {'+16V': 'VCC', '-16V': 'VEE', '-5V1': 'VEE'}
GROUNDS = {'AGND': 'GND', 'PGND': 'GNDD', 'CHASSIS': 'GNDA'}

NS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
# FROZEN IDENTIFIER, as in gen_project.py - see the note there before touching it.
def U(s): return str(uuid.uuid5(NS, 'steer500r:' + s))
ROOT = U('root')
PROJ = 'UTS Mini Mixing Desk - Compressor'

_sc = {}
def sym(lib, name):
    k = (lib, name)
    if k not in _sc: _sc[k] = resolve_symbol(lib, name)
    return _sc[k]

def pins_of(lib, name, unit):
    p = symbol_pins(sym(lib, name))
    out = dict(p.get(unit, {}))
    for k, v in p.get(0, {}).items(): out.setdefault(k, v)
    return out

def place_pin(px, py, X, Y, rot):
    """Symbol-space pin -> schematic mm. Verified against kicad-cli for all four
    angles (rot 90 puts Device:R pin 1 to the west, rot 270 to the east)."""
    if rot == 0:   return (X + px, Y - py)
    if rot == 90:  return (X - py, Y - px)
    if rot == 180: return (X - px, Y + py)
    return (X + py, Y + px)

def outward(ang, rot):
    """Unit vector pointing away from the symbol body, in schematic space.
    Same transform as place_pin, minus the translation."""
    a = math.radians((ang + 180) % 360)
    dx, dy = math.cos(a), math.sin(a)
    if   rot == 0:   v = (dx, -dy)
    elif rot == 90:  v = (-dy, -dx)
    elif rot == 180: v = (-dx, dy)
    else:            v = (dy, dx)
    return (int(round(v[0])), int(round(v[1])))

def label_angle(vec):
    return {(1,0):0, (0,-1):90, (-1,0):180, (0,1):270}[vec]

# ------------------------------------------------------------------ the parts
class Part:
    __slots__ = ('ref','lib','name','value','fp','block','pins','unit',
                 'X','Y','rot','gx','gy','sheet')
    def __init__(self, p):
        self.ref, self.lib, self.name, self.value, self.fp, self.block, self.pins = p[:7]
        self.unit = p[7] if len(p) > 7 else 1
        self.rot = 0

def load_parts():
    out = []
    for p in design.PARTS:
        if p[0].startswith('#'):        # PWR_FLAGs are re-created after routing
            continue
        out.append(Part(p))
    return out

def classify(parts, max_fanout):
    fan = collections.Counter()
    for p in parts:
        for net in p.pins.values(): fan[net] += 1
    kind = {}
    for net, n in fan.items():
        if net in design.NO_CONNECT:  kind[net] = 'nc'
        elif net in RAILS:            kind[net] = 'rail'
        elif net in GROUNDS:          kind[net] = 'gnd'
        elif n > max_fanout:          kind[net] = 'label'
        else:                         kind[net] = 'wire'
    return kind, fan

# ------------------------------------------------------------------ placement
def order_block(items):
    """Greedy connectivity chain: after the first part, repeatedly take whichever
    unplaced part shares the most nets with the ones already down. Keeps parts
    that talk to each other physically near each other, which is most of what
    makes the router's job easy."""
    if not items: return []
    rest = list(items)
    seq  = [rest.pop(0)]
    live = collections.Counter(seq[0].pins.values())
    while rest:
        best, bi = -1, 0
        for i, cand in enumerate(rest):
            s = sum(live[n] for n in cand.pins.values())
            if s > best: best, bi = s, i
        nxt = rest.pop(bi); seq.append(nxt)
        for n in nxt.pins.values(): live[n] += 1
    return seq

def orient(part, kind):
    """Two-pin passives: ground pin at the bottom, rail pin at the top. Costs
    nothing and removes most of the crossing wires around the supply."""
    pins = pins_of(part.lib, part.name, part.unit)
    if len(part.pins) != 2: return 0
    vert = all(abs(pins[k][0]) < 0.01 for k in part.pins if k in pins)
    if not vert: return 0
    for pn, net in part.pins.items():
        if pn not in pins: continue
        k = kind.get(net)
        top = pins[pn][1] > 0                      # symbol +y renders upward
        if k == 'gnd':  return 180 if top else 0
        if k == 'rail': return 0 if top else 180
    return 0

def place(parts, kind):
    blocks, seen = [], set()
    for p in parts:
        if p.block not in seen: seen.add(p.block); blocks.append(p.block)
    row, heads = 0, []
    for b in blocks:
        heads.append((MARGIN, MARGIN + row * CELL_H - 6, b))
        row += 1
        col = 0
        for p in order_block([x for x in parts if x.block == b]):
            if col >= COLS: col = 0; row += 1
            p.gx = MARGIN + col * CELL_W + CELL_W // 2
            p.gy = MARGIN + row * CELL_H + CELL_H // 2
            p.X, p.Y = round(p.gx * GRID, 2), round(p.gy * GRID, 2)
            p.rot = orient(p, kind)
            col += 1
        row += 1
    return heads, MARGIN * 2 + COLS * CELL_W, MARGIN + (row + 1) * CELL_H

# -------------------------------------------------------------------- routing
class Router:
    """Grid router whose occupancy model mirrors KiCad's connectivity rules.

    KiCad joins two wires at a point only if at least one of them has a *vertex*
    there - an endpoint or a corner. Two wires that run straight through the same
    point on perpendicular axes simply cross, and are not connected. So each node
    tracks two things separately:

        vertex[node]        -> the one net allowed a corner/endpoint here
        through[node][axis] -> the one net allowed to pass straight along that axis

    A vertex touches everything at its node, so it needs the node clear of other
    nets entirely. A straight pass only conflicts with the same axis. Getting this
    distinction right is the difference between a router that shorts nets and one
    that can legally cross them."""
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.blocked = set()
        self.vertex  = {}
        self.through = {}

    def block_body(self, part):
        pins = pins_of(part.lib, part.name, part.unit)
        pts = [place_pin(v[0], v[1], part.X, part.Y, part.rot) for v in pins.values()]
        gx = [int(round(x / GRID)) for x, _ in pts]
        gy = [int(round(y / GRID)) for _, y in pts]
        pad = 1
        for x in range(min(gx) - pad, max(gx) + pad + 1):
            for y in range(min(gy) - pad, max(gy) + pad + 1):
                self.blocked.add((x, y))

    def inb(self, n): return 0 <= n[0] < self.w and 0 <= n[1] < self.h

    def can_vertex(self, n, net):
        if self.vertex.get(n, net) != net: return False
        for a, o in self.through.get(n, {}).items():
            if o != net: return False
        return True

    def can_pass(self, n, net, axis):
        if self.vertex.get(n, net) != net: return False
        return self.through.get(n, {}).get(axis, net) == net

    def enterable(self, n, net):
        if not self.inb(n): return False
        if n in self.blocked and self.vertex.get(n) != net \
           and net not in self.through.get(n, {}).values():
            return False
        return True

    def mark_vertex(self, n, net):
        self.vertex[n] = net; self.blocked.discard(n)

    def mark_pass(self, n, net, axis):
        self.through.setdefault(n, {})[axis] = net; self.blocked.discard(n)

    def commit(self, path, net):
        for i, n in enumerate(path):
            if i == 0 or i == len(path) - 1:
                self.mark_vertex(n, net); continue
            d0 = (n[0]-path[i-1][0], n[1]-path[i-1][1])
            d1 = (path[i+1][0]-n[0], path[i+1][1]-n[1])
            if d0 == d1: self.mark_pass(n, net, 'H' if d0[0] else 'V')
            else:        self.mark_vertex(n, net)

    def route(self, starts, targets, net):
        tg = set(targets)
        if not tg: return None
        def h(n):
            return min(abs(n[0]-t[0]) + abs(n[1]-t[1]) for t in tg)
        pq, best, prev, pops = [], {}, {}, 0
        for s in starts:
            if not self.inb(s) or not self.can_vertex(s, net): continue
            st = (s, (0, 0)); best[st] = 0
            heapq.heappush(pq, (h(s), 0, st))
        while pq:
            f, g, st = heapq.heappop(pq)
            node, d = st
            if best.get(st, 1e18) < g: continue
            if node in tg and g > 0 and self.can_vertex(node, net):
                path, cur = [node], st
                while cur in prev:
                    cur = prev[cur]; path.append(cur[0])
                path.reverse(); return path
            pops += 1
            if pops > MAX_POP: return None
            for nd in ((1,0), (-1,0), (0,1), (0,-1)):
                # leaving `node` in direction nd: is `node` a corner or a straight run?
                if d == (0,0):
                    ok_here = self.can_vertex(node, net)
                elif nd != d:
                    ok_here = self.can_vertex(node, net)
                else:
                    ok_here = self.can_pass(node, net, 'H' if nd[0] else 'V')
                if not ok_here: continue
                nxt = (node[0] + nd[0], node[1] + nd[1])
                if not self.enterable(nxt, net): continue
                ng = g + 1 + (TURN_COST if d != (0,0) and nd != d else 0)
                nst = (nxt, nd)
                if ng < best.get(nst, 1e18):
                    best[nst] = ng; prev[nst] = st
                    heapq.heappush(pq, (ng + h(nxt), ng, nst))
        return None


def merge_runs(path):
    """Collapse a node path into the fewest straight segments."""
    segs, i = [], 0
    while i < len(path) - 1:
        d = (path[i+1][0]-path[i][0], path[i+1][1]-path[i][1])
        j = i + 1
        while j < len(path) - 1 and \
              (path[j+1][0]-path[j][0], path[j+1][1]-path[j][1]) == d:
            j += 1
        segs.append((path[i], path[j])); i = j
    return segs


def split_at_vertices(segs):
    """Break every segment wherever another segment of the same net ends on it.

    This is not cosmetic. KiCad only joins wires that share an ENDPOINT - a wire
    running straight through a junction point is not connected to it, even with a
    junction dot present (verified against kicad-cli). So a T has to be three
    segments meeting at a point, never one long wire plus a stub touching it."""
    pts = set()
    for a, b in segs: pts.add(a); pts.add(b)
    out = []
    for a, b in segs:
        if a == b: continue
        if a[0] == b[0]:
            lo, hi = sorted((a[1], b[1]))
            cuts = sorted({lo, hi} | {p[1] for p in pts
                                      if p[0] == a[0] and lo < p[1] < hi})
            out += [((a[0], y1), (a[0], y2)) for y1, y2 in zip(cuts, cuts[1:])]
        else:
            lo, hi = sorted((a[0], b[0]))
            cuts = sorted({lo, hi} | {p[0] for p in pts
                                      if p[1] == a[1] and lo < p[0] < hi})
            out += [((x1, a[1]), (x2, a[1])) for x1, x2 in zip(cuts, cuts[1:])]
    return out


def net_is_connected(segs, must_touch):
    """Union-find over SHARED ENDPOINTS only - the rule KiCad actually uses.
    Segments that merely cross are deliberately not unioned."""
    par = {}
    def find(a):
        par.setdefault(a, a)
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    def uni(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    for a, b in segs: uni(a, b)
    if not must_touch: return True
    if any(p not in par for p in must_touch): return False
    return len({find(p) for p in must_touch}) == 1


def junctions_for(segs):
    """After splitting, a dot is needed wherever three or more segment ends meet."""
    deg = collections.Counter()
    for a, b in segs: deg[a] += 1; deg[b] += 1
    return {p for p, d in deg.items() if d >= 3}


# --------------------------------------------------------------- file writing
def sym_block(out, lib, name, unit, ref, value, fp, X, Y, rot, pinnums,
              hide_ref=False, uid=None):
    sid = uid or U('%s.%s' % (ref, unit))
    out.append('\t(symbol')
    out.append('\t\t(lib_id "%s:%s") (at %.2f %.2f %d) (unit %d)' % (lib, name, X, Y, rot, unit))
    out.append('\t\t(exclude_from_sim no) (in_bom %s) (on_board %s) (dnp no)'
               % ('no' if hide_ref else 'yes', 'no' if hide_ref else 'yes'))
    out.append('\t\t(uuid "%s")' % sid)
    hid = ' (hide yes)' if hide_ref else ''
    out.append('\t\t(property "Reference" %s (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)%s))'
               % (dumps(Q(ref)), X - 8.89, Y - 8.89, hid))
    out.append('\t\t(property "Value" %s (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)%s))'
               % (dumps(Q(value)), X - 8.89, Y - 6.35, hid))
    out.append('\t\t(property "Footprint" %s (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))'
               % (dumps(Q(fp)), X, Y))
    out.append('\t\t(property "Datasheet" "" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))' % (X, Y))
    for pn in pinnums:
        out.append('\t\t(pin "%s" (uuid "%s"))' % (pn, U('%s.%s.%s.pin' % (ref, unit, pn))))
    out.append('\t\t(instances (project "%s" (path "/%s" (reference %s) (unit %d))))'
               % (PROJ, ROOT, dumps(Q(ref)), unit))
    out.append('\t)')

def build(out_path, force_label=frozenset(), fanout=6):
    ap = None
    parts = load_parts()
    kind, fan = classify(parts, fanout)
    for n in force_label:
        if kind.get(n) == 'wire': kind[n] = 'label'
    heads, W, H = place(parts, kind)

    R = Router(W + MARGIN, H + MARGIN)
    for p in parts: R.block_body(p)

    # ---- escape stubs; every pin gets one, whatever happens to its net
    stubs, terms = [], collections.defaultdict(list)
    stub_geo = collections.defaultdict(list)
    plain_stubs = []
    railsyms, gndsyms, lbls, ncs = [], [], [], []
    for p in parts:
        pin_geo = pins_of(p.lib, p.name, p.unit)
        for pn, net in p.pins.items():
            px, py, ang = pin_geo[pn][0], pin_geo[pn][1], pin_geo[pn][2]
            mx, my = place_pin(px, py, p.X, p.Y, p.rot)
            n0 = (int(round(mx / GRID)), int(round(my / GRID)))
            v = outward(ang, p.rot)
            n1 = (n0[0] + v[0] * STUB, n0[1] + v[1] * STUB)
            k = kind[net]
            if k == 'nc':
                ncs.append((n0, p.ref, pn)); continue
            stubs.append((n0, n1, net))
            axis = 'H' if v[0] else 'V'
            for a in range(STUB + 1):
                nn = (n0[0] + v[0]*a, n0[1] + v[1]*a)
                if a in (0, STUB): R.mark_vertex(nn, net)
                else:              R.mark_pass(nn, net, axis)
            stub_geo[net].append((n0, n1))
            if   k == 'rail': railsyms.append((n1, net, v))
            elif k == 'gnd':  gndsyms.append((n1, net, v))
            elif k == 'label': lbls.append((n1, net, v))
            else: terms[net].append(n1)
            if k != 'wire': plain_stubs.append((n0, n1, net))

    # ---- route the local nets, longest-span first (they need the room)
    segs_by_net, failed = {}, []
    def span(net):
        ns = terms[net]
        return max(abs(a[0]-b[0]) + abs(a[1]-b[1]) for a in ns for b in ns)
    for net in sorted(terms, key=span, reverse=True):
        ns = terms[net]
        if len(ns) < 2: continue
        tree, segs, ok = {ns[0]}, [], True
        for t in ns[1:]:
            if t in tree: continue
            path = R.route([t], tree, net)
            if path is None: ok = False; break
            R.commit(path, net)
            segs += merge_runs(path)
            tree.update(path)
        if ok and not all(t in tree for t in ns):
            ok = False
        if ok:
            allsegs = split_at_vertices(segs + stub_geo[net])
            pinpts = [a for a, _ in stub_geo[net]]
            if not net_is_connected(allsegs, pinpts):
                ok = False                   # drawn, but not actually one node
            else:
                segs_by_net[net] = allsegs
        else:                                   # fall back: label every pin
            failed.append(net)
            for t in ns: lbls.append((t, net, (1, 0)))

    jn = set()
    for segs in segs_by_net.values(): jn |= junctions_for(segs)

    # ------------------------------------------------------------- emit
    o = []
    o.append('(kicad_sch')
    o.append('\t(version 20250114)')
    o.append('\t(generator "uts-compressor-router")')
    o.append('\t(generator_version "9.0")')
    o.append('\t(uuid "%s")' % ROOT)
    o.append('\t(paper "User" %.2f %.2f)' % ((W + MARGIN) * GRID, (H + MARGIN) * GRID))
    o.append('\t(title_block (title "UTS Mini Mixing Desk - Compressor - routed") (date "%s") (rev "A")'
             ' (company "500-series module"))' % datetime.date.today().isoformat())

    used = {('%s:%s' % (p.lib, p.name)): (p.lib, p.name) for p in parts}
    for net in set(n for _, n, _ in railsyms): used['power:'+RAILS[net]] = ('power', RAILS[net])
    for net in set(n for _, n, _ in gndsyms):  used['power:'+GROUNDS[net]] = ('power', GROUNDS[net])
    used['power:PWR_FLAG'] = ('power', 'PWR_FLAG')
    o.append('\t(lib_symbols')
    for k in sorted(used): o.append('\t\t' + dumps(sym(*used[k])))
    o.append('\t)')

    for p in parts:
        sym_block(o, p.lib, p.name, p.unit, p.ref, p.value, p.fp,
                  p.X, p.Y, p.rot, list(p.pins))

    # power / ground symbols, rotated so the glyph points sensibly
    ROT = {(0,1): 0, (0,-1): 180, (1,0): 270, (-1,0): 90}
    n = 0
    for node, net, v in gndsyms:
        n += 1
        sym_block(o, 'power', GROUNDS[net], 1, '#PWR%03d' % n, net, '',
                  node[0]*GRID, node[1]*GRID, ROT[v], ['1'], hide_ref=True,
                  uid=U('gnd%d' % n))
    for node, net, v in railsyms:
        n += 1
        sym_block(o, 'power', RAILS[net], 1, '#PWR%03d' % n, net, '',
                  node[0]*GRID, node[1]*GRID, ROT[(-v[0], -v[1])], ['1'],
                  hide_ref=True, uid=U('rail%d' % n))
    for i, net in enumerate(['+16V', '-16V', 'AGND', '-5V1', 'PGND', 'CHASSIS']):
        x, y = (MARGIN + i*6) * GRID, (H + 4) * GRID
        sym_block(o, 'power', 'PWR_FLAG', 1, '#FLG%03d' % i, net, '',
                  x, y, 0, ['1'], hide_ref=True, uid=U('flg%d' % i))
        o.append('\t(label %s (at %.2f %.2f 90) (effects (font (size 1.27 1.27))'
                 ' (justify left bottom)) (uuid "%s"))' % (dumps(Q(net)), x, y, U('flgl%d' % i)))

    for a, b, net in plain_stubs:
        o.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default))'
                 ' (uuid "%s"))' % (a[0]*GRID, a[1]*GRID, b[0]*GRID, b[1]*GRID,
                                    U('s%d.%d.%d.%d' % (a[0], a[1], b[0], b[1]))))
    for net, segs in segs_by_net.items():
        for a, b in segs:
            o.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default))'
                     ' (uuid "%s"))' % (a[0]*GRID, a[1]*GRID, b[0]*GRID, b[1]*GRID,
                                        U('w%s.%d.%d.%d.%d' % (net, a[0], a[1], b[0], b[1]))))
    for p in sorted(jn):
        o.append('\t(junction (at %.2f %.2f) (diameter 0) (color 0 0 0 0) (uuid "%s"))'
                 % (p[0]*GRID, p[1]*GRID, U('j%d.%d' % p)))
    for node, net, v in lbls:
        o.append('\t(label %s (at %.2f %.2f %d) (effects (font (size 1.27 1.27))'
                 ' (justify left bottom)) (uuid "%s"))'
                 % (dumps(Q(net)), node[0]*GRID, node[1]*GRID, label_angle(v),
                    U('l%s.%d.%d' % (net, node[0], node[1]))))
    for node, ref, pn in ncs:
        o.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))'
                 % (node[0]*GRID, node[1]*GRID, U('nc%s%s' % (ref, pn))))
    for gx, gy, t in heads:
        o.append('\t(text %s (at %.2f %.2f 0) (effects (font (size 2.5 2.5) (bold yes))'
                 ' (justify left bottom)) (uuid "%s"))'
                 % (dumps(Q(t)), gx*GRID, gy*GRID, U('t'+t)))
    o.append('\t(sheet_instances (path "/" (page "1")))')
    o.append('\t(embedded_fonts no)')
    o.append(')')
    open(out_path, 'w').write('\n'.join(o) + '\n')

    return {
        'parts': len(parts),
        'nets': len(kind),
        'wired': len(segs_by_net),
        'gnd': len(gndsyms),
        'rail': len(railsyms),
        'labels': len(set(n for _, n, _ in lbls)),
        'segments': sum(len(v) for v in segs_by_net.values()) + len(stubs),
        'junctions': len(jn),
        'failed': sorted(failed),
    }


def _find_kicad_cli():
    """Locate kicad-cli. Override with KICAD_CLI."""
    import shutil
    env = os.environ.get('KICAD_CLI')
    if env: return env
    found = shutil.which('kicad-cli')
    if found: return found
    for c in ['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli',
              '/usr/bin/kicad-cli', '/usr/local/bin/kicad-cli',
              'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe']:
        if os.path.exists(c): return c
    return 'kicad-cli'          # let it fail loudly with a useful message

KC = _find_kicad_cli()

def kicad_nets(sch):
    """Ask KiCad what the drawing actually says. This is the oracle - my own
    idea of its connectivity rules is not authoritative, and a schematic that
    reads well but nets wrongly is worse than useless."""
    import subprocess, tempfile, os
    net = sch.replace('.kicad_sch', '.net')
    r = subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                        '-o', net, sch], capture_output=True, text=True)
    if not os.path.exists(net):
        raise RuntimeError('kicad-cli failed: ' + r.stderr[-400:])
    node, _ = sexp.parse_one(sexp.tokenize(open(net).read()))
    out = {}
    for n in sexp.getall(sexp.get(node, 'nets'), 'net'):
        nm = str(sexp.get(n, 'name')[1]).lstrip('/')
        out[nm] = {(str(sexp.get(x, 'ref')[1]), str(sexp.get(x, 'pin')[1]))
                   for x in sexp.getall(n, 'node')}
    return out

def intended():
    w = {}
    for p in design.PARTS:
        if p[0].startswith('#'): continue
        for pn, net in p[6].items():
            if net in design.NO_CONNECT: continue
            w.setdefault(net, set()).add((p[0], pn))
    return w

def bad_nets(sch):
    """Nets whose drawn connectivity does not match the design."""
    want, got = intended(), kicad_nets(sch)
    gs = {frozenset(v): k for k, v in got.items()}
    bad = set()
    for net, pins in want.items():
        if frozenset(pins) in gs: continue
        bad.add(net)
        # anything tangled up with it has to be retried too
        for nm, mem in got.items():
            if mem & pins:
                for other, opins in want.items():
                    if opins & mem: bad.add(other)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-o', '--out', default='compressor-routed.kicad_sch')
    ap.add_argument('--fanout', type=int, default=6,
                    help='nets with more pins than this stay as labels (default 6)')
    ap.add_argument('--turn', type=int, default=TURN_COST,
                    help='A* corner penalty; higher = straighter but longer (default 4)')
    ap.add_argument('--passes', type=int, default=6,
                    help='max verify-and-repair rounds against kicad-cli (default 6)')
    ap.add_argument('--no-verify', action='store_true',
                    help='skip the kicad-cli check (not recommended)')
    args = ap.parse_args()
    globals()['TURN_COST'] = args.turn

    forced, st = set(), None
    for p in range(1, args.passes + 1):
        st = build(args.out, forced, args.fanout)
        if args.no_verify: break
        bad = bad_nets(args.out)
        bad -= {n for n in bad if n in forced}
        print('pass %d: %d nets drawn, %d mismatched' % (p, st['wired'], len(bad)))
        if not bad:
            break
        forced |= bad
        print('   demoting to labels:', ', '.join(sorted(bad)))
    else:
        print('gave up after %d passes' % args.passes)

    print()
    for k in ('parts', 'nets', 'wired', 'gnd', 'rail', 'labels', 'segments', 'junctions'):
        print('%-12s %d' % (k, st[k]))
    if st['failed']: print('router gave up on:', ', '.join(st['failed']))
    if forced: print('demoted by verify:', ', '.join(sorted(forced)))
    print('->', args.out)


if __name__ == '__main__':
    main()
