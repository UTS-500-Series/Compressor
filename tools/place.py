"""Role-based placement: put each part where a person would draw it.

A schematic reads well because parts sit in conventional positions relative to the
active device they belong to - feedback over the top of an op amp, the input
resistor on its left, the leg to ground hanging below, collector loads above a
transistor and emitter resistors below. None of that comes out of a connectivity
sort, which is why the first attempt looked like a parts bin.

So: op amps and transistors are ANCHORS, laid left to right in signal order. Every
two-pin passive is then assigned to an anchor and a SLOT by looking at which of the
anchor's pins its nets touch. Whatever is left over goes in a row underneath.
"""
import collections
from route_sch import pins_of, place_pin

CELL = 2.54          # occupancy resolution, mm
PAD  = 3.81          # keep-out ring around every part so wires have channels
MARGIN = 25.4        # clear border; nothing may sit at a negative coordinate


def bbox(p, X, Y, rot):
    geo = pins_of(p.lib, p.name, p.unit)
    pts = [place_pin(v[0], v[1], X, Y, rot) for v in geo.values()] or [(X, Y)]
    xs = [q[0] for q in pts] + [X]; ys = [q[1] for q in pts] + [Y]
    return (min(xs) - PAD, min(ys) - PAD, max(xs) + PAD, max(ys) + PAD)


class Space:
    """Coarse occupancy map. Without this, two parts land on top of each other,
    their pins coincide, and every net through them shorts - which is exactly what
    happened the first time this placer ran."""
    def __init__(self): self.used = set()

    def cells(self, box):
        x0, y0, x1, y1 = box
        return {(cx, cy)
                for cx in range(int(x0 // CELL), int(x1 // CELL) + 1)
                for cy in range(int(y0 // CELL), int(y1 // CELL) + 1)}

    def free(self, box): return not (self.cells(box) & self.used)

    def take(self, box): self.used |= self.cells(box)

    def put(self, p, X, Y, rot, slide=(0, 0), tries=24):
        """Place at (X,Y), sliding along `slide` until it fits."""
        for i in range(tries):
            x, y = X + slide[0] * i * CELL * 2, Y + slide[1] * i * CELL * 2
            b = bbox(p, x, y, rot)
            if self.free(b):
                self.take(b); p.X, p.Y, p.rot = x, y, rot; return True
        p.X, p.Y, p.rot = X, Y, rot
        self.take(bbox(p, X, Y, rot))
        return False

# spacing, in mm; generous enough that the router has channels to work in
ANCHOR_DX = 38.1
SPINE_Y   = 63.5
ROW_DY    = 63.5
PER_ROW   = 5
SLOT      = 15.24
STEP      = 20.32

OPAMP  = 'NE5532'
TRANS  = 'BC549'

def is_anchor(p):
    return (p.name == OPAMP and p.unit in (1, 2)) or p.name == TRANS

def anchor_pins(p):
    """(inputs, output) net names for whichever anchor kind this is."""
    if p.name == OPAMP:
        if p.unit == 1: neg, pos, out = p.pins.get('2'), p.pins.get('3'), p.pins.get('1')
        else:           neg, pos, out = p.pins.get('6'), p.pins.get('5'), p.pins.get('7')
        return dict(neg=neg, pos=pos, out=out, kind='op')
    return dict(c=p.pins.get('1'), b=p.pins.get('2'), e=p.pins.get('3'), kind='q')

def order_anchors(anchors, parts):
    """Left-to-right by signal flow: an anchor whose output feeds another anchor's
    input (directly, or through one two-pin passive) is placed before it."""
    by_net = collections.defaultdict(list)
    for p in parts:
        for n in p.pins.values(): by_net[n].append(p)

    def reaches(net, hops=2):
        """Nets a signal at `net` can arrive at through <=hops two-pin passives."""
        seen, frontier = {net}, [net]
        for _ in range(hops):
            nxt = []
            for n in frontier:
                for q in by_net.get(n, []):
                    if len(q.pins) != 2 or is_anchor(q): continue
                    for m in q.pins.values():
                        if m not in seen: seen.add(m); nxt.append(m)
            frontier = nxt
        return seen

    idx = {id(a): i for i, a in enumerate(anchors)}
    succ = {id(a): set() for a in anchors}
    indeg = collections.Counter()
    for a in anchors:
        ap = anchor_pins(a)
        out = ap.get('out') if ap['kind'] == 'op' else ap.get('c')
        if not out: continue
        downstream = reaches(out)
        for b in anchors:
            if b is a: continue
            bp = anchor_pins(b)
            ins = [bp.get('neg'), bp.get('pos')] if bp['kind'] == 'op' else [bp.get('b')]
            if any(i in downstream for i in ins if i):
                if id(b) not in succ[id(a)]:
                    succ[id(a)].add(id(b)); indeg[id(b)] += 1

    ready = sorted([a for a in anchors if indeg[id(a)] == 0], key=lambda z: idx[id(z)])
    out, seen = [], set()
    while ready:
        a = ready.pop(0)
        if id(a) in seen: continue
        seen.add(id(a)); out.append(a)
        for b in anchors:
            if id(b) in succ[id(a)]:
                indeg[id(b)] -= 1
                if indeg[id(b)] == 0: ready.append(b)
        ready.sort(key=lambda z: idx[id(z)])
    for a in anchors:                      # anything in a cycle
        if id(a) not in seen: out.append(a)
    return out

def assign_slot(part, anchors_meta, kind):
    """Which anchor does this passive belong to, and where does it hang?"""
    nets = set(part.pins.values())
    best = None
    for a, ap in anchors_meta:
        if ap['kind'] == 'op':
            neg, pos, out = ap['neg'], ap['pos'], ap['out']
            if neg in nets and out in nets:        return (a, 'above', 0)
            if neg in nets:
                other = (nets - {neg}).pop() if len(nets) == 2 else None
                if other and kind.get(other) in ('gnd', 'rail'): return (a, 'below', 0)
                return (a, 'left_hi', 0)
            if pos in nets:
                other = (nets - {pos}).pop() if len(nets) == 2 else None
                if other and kind.get(other) in ('gnd', 'rail'): return (a, 'below', 1)
                return (a, 'left_lo', 0)
            if out in nets and best is None:       best = (a, 'right', 0)
        else:
            c, b, e = ap['c'], ap['b'], ap['e']
            if c in nets:                          return (a, 'above', 0)
            if e in nets:                          return (a, 'below', 0)
            if b in nets and best is None:         best = (a, 'left_hi', 0)
    return best

def place_sheet(parts, kind, x0=38.1, y0=SPINE_Y):
    """Assign .X .Y .rot to every part on one sheet, without overlaps."""
    sp = Space()
    anchors = [p for p in parts if is_anchor(p)]
    others  = [p for p in parts if not is_anchor(p) and not (p.name == OPAMP and p.unit == 3)]
    power   = [p for p in parts if p.name == OPAMP and p.unit == 3]

    anchors = order_anchors(anchors, parts)
    for i, a in enumerate(anchors):
        sp.put(a, x0 + (i % PER_ROW) * ANCHOR_DX,
                  y0 + (i // PER_ROW) * ROW_DY, 0, slide=(0, 1))
    meta = [(a, anchor_pins(a)) for a in anchors]

    used = collections.Counter()
    leftovers = []
    for p in others:
        slot = assign_slot(p, meta, kind) if len(p.pins) == 2 else None
        if not slot:
            leftovers.append(p); continue
        a, name, lane = slot
        k = (id(a), name, lane)
        n = used[k]; used[k] += 1
        if   name == 'above':
            ok = sp.put(p, a.X + lane * STEP, a.Y - SLOT - n * STEP, 0, slide=(0, -1))
        elif name == 'below':
            ok = sp.put(p, a.X + lane * STEP, a.Y + SLOT + n * STEP, 0, slide=(0, 1))
        elif name == 'left_hi':
            ok = sp.put(p, a.X - SLOT - n * STEP, a.Y - 6.35, 90, slide=(-1, 0))
        elif name == 'left_lo':
            ok = sp.put(p, a.X - SLOT - n * STEP, a.Y + 12.7, 90, slide=(-1, 0))
        else:
            ok = sp.put(p, a.X + SLOT + n * STEP, a.Y, 90, slide=(1, 0))
        if not ok: leftovers.append(p)

    base = max([a.Y for a in anchors], default=y0) + ROW_DY
    col, row = 0, 0
    for p in leftovers + power:
        while True:
            X = x0 + col * (ANCHOR_DX * 0.7)
            Y = base + row * 33.02
            if sp.put(p, X, Y, 0, slide=(0, 1), tries=6): break
            col += 1
            if col > PER_ROW * 2: col = 0; row += 1
        col += 1
        if col > PER_ROW * 2: col = 0; row += 1

    allp = anchors + others + power
    if not allp: return (200, 150, [])

    # Slots slide left and up, so parts routinely end up at negative coordinates.
    # KiCad silently drops geometry off the page - it costs you whole nets and
    # gives no error - so shift everything into positive space before returning.
    boxes = [bbox(p, p.X, p.Y, p.rot) for p in allp]
    dx = MARGIN - min(b[0] for b in boxes)
    dy = MARGIN - min(b[1] for b in boxes)
    for p in allp:
        p.X = round(p.X + dx, 2); p.Y = round(p.Y + dy, 2)
    boxes = [bbox(p, p.X, p.Y, p.rot) for p in allp]
    return (max(b[2] for b in boxes) + MARGIN,
            max(b[3] for b in boxes) + MARGIN, [])


# ---------------------------------------------------------------------------
# The power sheet needs its own layout. It is not a signal path, so the anchor
# rules above have nothing to grip: it is five small independent supply circuits
# plus a block of decoupling. Generic placement turns that into a wall. Grouping
# it by function, with a heading over each group, is what makes it legible.
# ---------------------------------------------------------------------------

POWER_GROUPS = [
    ('+16 V RAIL ENTRY',    ['R50', 'C16', 'D8']),
    ('-16 V RAIL ENTRY',    ['R51', 'C17', 'D9']),
    ('-5V1 REFERENCE',      ['R53', 'D10', 'C19', 'C20']),
    ('CELL BIAS',           ['R9', 'R10', 'C6', 'C7']),
    ('STEERING REFERENCE',  ['R60', 'R61', 'R62', 'C21', 'C22', 'R68', 'R69', 'U6']),
    ('GAIN-REDUCTION METER',['R77', 'LED1']),
    ('GROUNDING',           ['R52', 'C18', 'R48']),
]
GROUP_W  = 101.6      # column width per group
GROUP_H  = 88.9       # row height per group
GROUPS_PER_ROW = 3
DECAP_DX = 43.18


def _shunt(p, kind):
    """One end on a ground or rail net -> draw it vertical, hanging off the line."""
    return any(kind.get(n) in ('gnd', 'rail') for n in p.pins.values())


def place_power_sheet(parts, kind, x0=MARGIN + 12.7, y0=MARGIN + 22.86):
    """Group the supply circuits by function and pack them by measured size.

    Each group is laid out on its own, measured, and only then placed - a fixed
    grid pitch leaves most of the sheet empty, which is what made the first
    version unreadable even though the grouping was right.
    """
    byref = collections.defaultdict(list)
    for p in parts:
        key = p.ref + ('#P' if (p.name == OPAMP and p.unit == 3) else '')
        byref[key].append(p)

    laid, claimed = [], set()
    for title, refs in POWER_GROUPS:
        members = [q for r in refs for q in byref.get(r, [])]
        if not members: continue
        series = [q for q in members if not _shunt(q, kind)]
        shunts = [q for q in members if _shunt(q, kind)]
        loc = []
        for i, q in enumerate(series):
            rot = 90 if len(q.pins) == 2 else 0
            loc.append((q, i * 27.94, 0.0, rot))
        # only drop the shunt row down if there is a series row above it
        sy = 30.48 if series else 0.0
        for i, q in enumerate(shunts):
            loc.append((q, i * 22.86, sy, 0))
        w = max(x for _, x, _, _ in loc) + 27.94
        h = max(y for _, _, y, _ in loc) + 33.02
        laid.append((title, loc, w, h))
        claimed |= {id(q) for q in members}

    # Groups are already internally spaced, and packing keeps them apart, so place
    # directly. Running these through Space() makes the collision slider shove
    # parts tens of millimetres below their own heading.
    PAGE_W, headings = 355.6, []
    cx, cy, rowh = x0, y0, 0.0
    for title, loc, w, h in laid:
        if cx > x0 and cx + w > PAGE_W:
            cx, cy, rowh = x0, cy + rowh + 22.86, 0.0
        headings.append((cx - 7.62, cy - 10.16, title))
        for q, dx, dy, rot in loc:
            q.X, q.Y, q.rot = cx + dx, cy + dy, rot
        cx += w + 15.24
        rowh = max(rowh, h)

    rest = [p for p in parts if id(p) not in claimed]
    units = sorted([p for p in rest if p.name == OPAMP and p.unit == 3],
                   key=lambda q: q.ref)
    caps = [p for p in rest if p not in units]
    dy = cy + rowh + 30.48
    if units or caps:
        headings.append((x0 - 7.62, dy - 10.16, 'OP-AMP SUPPLY DECOUPLING'))
    bycap = collections.defaultdict(list)
    for c in caps: bycap[c.ref].append(c)
    order = sorted(bycap, key=lambda r: (len(r), r))
    for i, q in enumerate(units):
        q.X, q.Y, q.rot = x0 + i * DECAP_DX, dy + 25.4, 0
    n = max(len(units), 1)
    for i, r in enumerate(order):
        col, row = i % n, i // n
        for q in bycap[r]:
            q.X, q.Y, q.rot = (x0 + col * DECAP_DX + 20.32,
                               dy + 5.08 + row * 27.94, 0)

    allp = list(parts)
    boxes = [bbox(p, p.X, p.Y, p.rot) for p in allp]
    ddx = MARGIN - min(b[0] for b in boxes)
    ddy = MARGIN - min(b[1] for b in boxes)
    for p in allp:
        p.X = round(p.X + ddx, 2); p.Y = round(p.Y + ddy, 2)
    headings = [(x + ddx, y + ddy, t) for x, y, t in headings]
    boxes = [bbox(p, p.X, p.Y, p.rot) for p in allp]
    return (max(b[2] for b in boxes) + MARGIN,
            max(b[3] for b in boxes) + MARGIN, headings)
