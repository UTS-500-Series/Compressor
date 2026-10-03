#!/usr/bin/env python3
"""Builds the order list for both boards from Altronics (altronics.com.au).

    python3 tools/bom_altronics.py            # writes bom/altronics.csv, prints the table
    python3 tools/bom_altronics.py --check    # also flags parts with no catalogue line

Parts come from the two schematics the boards are built from,
kicad_withpcb/compressor_with_pcb and kicad_withpcb/compressor_front, not from design.py.
The main schematic still draws the front-board parts (excluded from its BOM) so the
circuit reads as one piece; a reference that appears on both sheets belongs to the front
board and is counted once.

The catalogue table below is what Altronics' website showed on CHECKED: code, pack size,
price breaks (inc GST) and stock. Stock is the delivery warehouse and the Auburn NSW store,
the nearest to UTS. Re-check before ordering; prices and stock move.

Where Altronics has nothing that fits, the line says so and names another supplier.
Those lines have no Altronics price and are totalled separately.
"""
import csv, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import tokenize, parse_one, get, getall

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'kicad_withpcb/compressor_with_pcb/compressor_with_pcb.kicad_sch')
FRONT = os.path.join(ROOT, 'kicad_withpcb/compressor_front/compressor_front.kicad_sch')
OUT = os.path.join(ROOT, 'bom/altronics.csv')

CHECKED = '2026-10-03'

# code: (description, pack size, [(min qty, unit price inc GST)], stock as seen)
# Stock: "delivery / Auburn NSW"; IN = in stock, LOW = "Low - call", BO = back order.
CAT = {
 # 0.25 W 1% metal film, sold in tens
 'R7510': ('10R 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7526': ('47R 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7531': ('75R 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7534': ('100R 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7542': ('220R 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / BO'),
 'R7558': ('1k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7562': ('1k5 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7564': ('1k8 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7568': ('2k7 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7572': ('3k9 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7574': ('4k7 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7575': ('5k1 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7578': ('6k8 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7580': ('8k2 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7582': ('10k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7583': ('11k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'LOW / IN'),
 'R7586': ('15k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7588': ('18k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7589': ('20k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7590': ('22k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7591': ('24k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'LOW / IN'),
 'R7595': ('36k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7598': ('47k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7602': ('68k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7604': ('82k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'LOW / IN'),
 'R7606': ('100k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 'R7614': ('220k 0.25W 1% metal film resistor, pk 10', 10, [(1, 1.30), (10, 1.20)], 'IN / IN'),
 # capacitors
 'R2931': ('0.1uF 50V X7R 5mm monolithic ceramic', 1, [(1, .40), (10, .30), (100, .25)], 'IN / IN'),
 'R2910A': ('0.01uF 50V X7R 5mm monolithic ceramic', 1, [(1, .40), (10, .30), (100, .25)], 'IN / IN'),
 'R2900A': ('0.001uF 50V X7R 5mm monolithic ceramic', 1, [(1, .40), (10, .30), (100, .25)], 'IN / IN'),
 'R2822': ('100pF 50V SL 5mm ceramic', 1, [(1, .20), (10, .15), (100, .10)], 'IN / IN'),
 'R6570B': ('22uF 50V bipolar electrolytic', 1, [(1, 1.10), (10, .75), (50, .65)], 'IN / LOW'),
 'R5124': ('100uF 25V electrolytic', 1, [(1, .55), (10, .40), (100, .30)], 'IN / IN'),
 'R5104': ('47uF 25V electrolytic', 1, [(1, .50), (10, .35), (100, .25)], 'IN / IN'),
 'R4748': ('4.7uF 63V 105C electrolytic', 1, [(1, .30), (10, .25), (100, .15)], 'IN / IN'),
 # semiconductors
 'Z0101': ('1N914/1N4148 small signal diode', 1, [(1, .15), (25, .12), (100, .10)], 'IN / IN'),
 'Z0109': ('1N4004 400V 1A diode', 1, [(1, .20), (25, .15), (100, .10)], 'IN / IN'),
 'Z0614': ('5V1 1N4733 1W zener', 1, [(1, 1.75), (10, 1.25), (50, 1.00)], 'IN / IN'),
 'Z1044': ('BC549 NPN TO-92', 1, [(1, .95), (10, .75), (50, .50)], 'IN / IN'),
 'Z2785': ('NE5532AP dual op amp', 1, [(1, 3.50), (10, 3.25), (25, 2.75)], 'IN / IN'),
 'Z2872': ('TL072 dual JFET op amp', 1, [(1, 2.20), (10, 2.00), (25, 1.55)], 'IN / IN'),
 'Z2670': ('LM3914 LED bar/dot driver (linear)', 1, [(1, 9.10), (10, 8.00), (25, 6.35)],
           'LOW / LOW (in stock only at Cannington WA)'),
 'Z0733': ('Yellow 50mcd 3mm flangeless LED', 1, [(1, .40), (10, .35), (100, .30)], 'IN / IN'),
 'Z0731': ('Green 70mcd 3mm flangeless LED', 1, [(1, .40), (10, .35), (100, .30)], 'IN / IN'),
 'Z0730': ('Red 12mcd 3mm flangeless LED', 1, [(1, .30), (10, .25), (100, .20)], 'IN / IN'),
 # pots, trimmers, switches
 'R1946': ('10k lin 18T spline 9mm single vertical PCB pot', 1, [(1, 4.55), (10, 4.10), (20, 3.60)], 'IN / IN'),
 'R1948': ('100k lin 18T spline 9mm single vertical PCB pot', 1, [(1, 4.55), (10, 4.10), (20, 3.60)], 'IN / IN'),
 'R1960': ('100k log 18T spline 9mm single vertical PCB pot', 1, [(1, 4.55), (10, 4.10), (20, 3.60)], 'IN / IN'),
 'R1950': ('1M lin 18T spline 9mm single vertical PCB pot', 1, [(1, 4.55), (10, 4.10), (20, 3.60)], 'IN / IN'),
 'R2378A': ('2k 3296W top adjust 25 turn trimpot', 1, [(1, 3.15), (10, 2.60), (25, 2.00)], 'IN / IN'),
 'R2384A': ('20k 3296W top adjust 25 turn trimpot', 1, [(1, 3.15), (10, 2.60), (25, 2.00)], 'IN / IN'),
 'S1350': ('Salecom DPDT PCB mount mini toggle', 1, [(1, 4.60), (10, 4.15), (40, 3.70)], 'IN / IN'),
 'S1315': ('Salecom SPDT PCB mount mini toggle', 1, [(1, 2.95), (10, 2.60), (40, 2.35)], 'IN / IN'),
 # connectors and hardware
 'P0550': ('8 pin 0.3in DIL tinned IC socket', 1, [(1, .40), (10, .35), (25, .30)], 'IN / IN'),
 'P5410': ('40 way x 2 header pin strip (cut to 2 x 15)', 1, [(1, 1.20), (10, 1.10), (40, 1.00)], 'IN / IN'),
 'P1023': ('Socket to socket 30 way prototyping ribbon strip, 150mm', 1, [(1, 5.20), (4, 4.65), (10, 4.15)], 'IN / IN'),
 'H6545': ('11 x 14mm aluminium black 18T spline knob', 1, [(1, 3.95)], 'IN'),
 'H3110A': ('M3 x 6mm pan pozi nickel bolt, pk 25', 25, [(1, 2.55), (5, 2.25)], 'IN / IN'),
 'H3175': ('M3 hex nut, pk 25', 25, [(1, 2.65), (5, 2.40)], 'IN / IN'),
}

RES = {'10R': 'R7510', '47R': 'R7526', '75R': 'R7531', '100R': 'R7534', '220R': 'R7542',
       '1k': 'R7558', '1k5': 'R7562', '1k8': 'R7564', '2k7': 'R7568', '3k9': 'R7572',
       '4k7': 'R7574', '5k1': 'R7575', '6k8': 'R7578', '8k2': 'R7580', '10k': 'R7582',
       '11k': 'R7583', '15k': 'R7586', '18k': 'R7588', '20k': 'R7589', '22k': 'R7590',
       '24k': 'R7591', '36k': 'R7595', '47k': 'R7598', '68k': 'R7602', '82k': 'R7604',
       '100k': 'R7606', '220k': 'R7614'}

# Parts that need more than the catalogue line: (code or None, note, alternative supplier)
FILM = ('Altronics film stops at 1.0uF (R3037B MKT) at 5 mm pitch, and its 2.2uF film is a '
        '27 mm greencap. The main board is drawn for the element14 part named here.')
# element14 film parts the main board footprints are drawn for (checked 2026-10-03, prices inc GST)
FILM_ALT = {
 '10u': 'element14 3518951: TDK B32562H1106K000, 10uF 63V PET, 15 mm pitch, 16.5 x 11.8 x 13 mm. '
        '$8.86 each, 538 in stock (UK, 3-5 days)',
 '4u7': 'element14 4457285: TDK B32562H1475K000, 4.7uF 100V PET, 15 mm pitch, 16.5 x 7.3 x 10.6 mm. '
        '$5.23 each (min 5), 880 in stock (UK, 3-5 days)',
 '2u2': 'element14 2429330: KEMET MMK5225K63J06L4BULK, 2.2uF 63V PET, 5 mm pitch, 7.2 x 7.2 x 13 mm. '
        '$1.19 each (min 10), 884 in stock, not being restocked',
}
SPECIAL = {
 'R48':  (None, 'Wire link: the 0R is the PGND to AGND star link. Nothing to order.', ''),
 'R61':  (None, '1k33 0.1%. Altronics stocks E24 1% only (nearest is 1k3, R7561). Sets the '
               'gain cell rest point with R62, by absolute value.',
          'element14 / DigiKey: 1k33 0.1% 25 ppm axial metal film, e.g. Vishay CMF55 or '
          'RN55D series (not checked)'),
 'R62':  (None, '23k2 0.1%, see R61. No Altronics equivalent.',
          'element14 / DigiKey: 23k2 0.1% 25 ppm axial metal film (not checked)'),
 'C15':  (None, 'Timing capacitor, must be film (low leakage). ' + FILM, FILM_ALT['10u']),
}
# Value-level rules for lines with no straight catalogue match
FILM_REFS = {'C5', 'C8', 'C9', 'C10', 'C14', 'C35'}
MATCHED = {'R1', 'R2', 'R3', 'R4', 'R23', 'R24', 'R80', 'R81', 'R82', 'R83', 'R21', 'R22'}


def instances(path, take_excluded):
    """{ref: (value, footprint)} for every placed symbol on a sheet."""
    tree, _ = parse_one(tokenize(open(path).read()))
    out = {}
    for sym in getall(tree, 'symbol'):
        if not get(sym, 'lib_id'):
            continue
        props = {str(p[1]): str(p[2]) for p in getall(sym, 'property')}
        ref = props.get('Reference', '')
        if not ref or ref.startswith('#'):
            continue
        in_bom = get(sym, 'in_bom')
        if not take_excluded and in_bom and str(in_bom[1]) == 'no':
            continue
        out.setdefault(ref, (props.get('Value', ''), props.get('Footprint', '')))
    return out


def parts():
    front = instances(FRONT, True)
    main = {r: v for r, v in instances(MAIN, False).items() if r not in front}
    return [('main', r, v, f) for r, (v, f) in main.items()] + \
           [('front', r, v, f) for r, (v, f) in front.items()]


def choose(ref, val, fp):
    """(code, note, alternative) for one part."""
    if ref in SPECIAL:
        return SPECIAL[ref]
    if ref in FILM_REFS:
        return (None, '%s film. ' % val + FILM, FILM_ALT[val])
    if ref.startswith('R') and not ref.startswith('RV'):
        note = ''
        if ref in MATCHED:
            note = ('Wants matching (0.1%% or better as a ratio): buy extra and sort with a '
                    'meter. %s set %s.' % ('R21/R22' if ref in ('R21', 'R22') else
                                          'R1-R4, R23/R24, R80-R83',
                                          'thump rejection' if ref in ('R21', 'R22') else
                                          'input and recovery CMRR'))
        return (RES[val], note, '')
    if ref.startswith('C'):
        if val == '100n':
            return ('R2931', '', '')
        if val == '10n':
            return ('R2910A', '', '')
        if val == '1n':
            return ('R2900A', '', '')
        if val == '100p':
            return ('R2822', 'SL class ceramic; Altronics has no 100pF NP0 leaded part.', '')
        if val == '22u':
            return ('R6570B', 'Bipolar, as the design asks. Check its diameter against the '
                              '6.3 mm outline.', '')
        if val == '100u':
            return ('R5124', '', '')
        if val == '47u':
            return ('R5104', '', '')
        if val == '4u7':
            return ('R4748', 'C22, electrolytic in the design.', '')
    if ref.startswith('D') and ref[1:].isdigit():
        n = int(ref[1:])
        if 20 <= n <= 36:
            # GR column all amber; LVL green, green, green, green, amber, amber, red upward
            colour = 'Z0733' if n < 30 else ('Z0730' if n == 36 else
                                             'Z0733' if n in (34, 35) else 'Z0731')
            return (colour, 'Meter LED. Altronics has no 2 mm round LEDs; 3 mm flangeless '
                            'fit the footprint at 3.5 mm pitch but need the panel holes '
                            'opened from 2.2 to 3.1 mm. No amber: yellow stands in.',
                    'Keep 2 mm: 2 mm round flat-top LEDs from element14 / DigiKey')
        if val == '1N4148':
            return ('Z0101', '', '')
        if val == '1N4004':
            return ('Z0109', '', '')
        if val.startswith('BZX79'):
            return ('Z0614', '1N4733 is the 1 W part in a DO-41 body (fits the 7.62 mm '
                             'footprint; leads 0.81 mm in 0.8 mm holes, ream to 1.0 if tight). '
                             'Altronics has no 500 mW 5V1.', 'BZX79-C5V1 from element14')
    if ref == 'LED1':
        return ('Z0733', 'GR indicator, 3 mm. Yellow standing in for amber.', '')
    if ref.startswith('Q'):
        return ('Z1044', 'Q1/Q2 a matched pair, Q6-Q9 a matched quad, glued together: buy '
                         'a batch and sort by Vbe. Altronics does not state the gain group '
                         '(the design wants BC549C).', '')
    if ref.startswith('U'):
        if val == 'NE5532':
            return ('Z2785', 'Socketed (P0550).', '')
        if val == 'TL072':
            return ('Z2872', 'U4, socketed (P0550).', '')
        if val == 'LM3914':
            return ('Z2670', 'Both meters (U10 was an LM3915, which nobody stocks). Low stock: '
                    'order early or call the store.', '')
    if ref.startswith('RV'):
        code = {'2k': 'R2378A', '20k': 'R2384A', '10k': 'R1946', '100kA': 'R1960',
                '100k': 'R1948', '1M': 'R1950'}.get(val)
        if code and code.startswith('R19'):
            return (code, '9 mm vertical, 18T spline. Same pins and lugs as the RK09K '
                          'footprint (lugs 8.6 mm apart, pins 7.0 mm behind them); body '
                          'stands 10.6 mm off the board. Altronics doesn\'t dimension the '
                          'shaft: check it lines up with the panel hole before cutting.', '')
        if code:
            return (code, '', '')
    if ref.startswith('SW'):
        if ref == 'SW1':
            return ('S1350', 'BYPASS. DPDT on-on.', '')
        return ('S1315', '%s. SPDT on-on (S1332 centre-off fits the same footprint).' % val, '')
    if ref == 'J1' and 'EDA' in val:
        return (None, 'Card-edge fingers on the main board: no part.', '')
    if ref in ('J1', 'J2'):
        return ('P5410', 'Altronics has no 30-way box header or IDC socket (their boxed '
                         'headers go 26, 34, 40). A plain 2 x 15 header fits both '
                         'footprints; one 2 x 40 strip covers both boards.',
                '30-way IDC box header, two IDC sockets and 30-way cable from element14')
    return (None, 'No rule for this part.', '')


def nk(s):
    return [(1, int(t)) if t.isdigit() else (0, t) for t in re.findall(r'\d+|\D+', s)]


def spare(code, need):
    """Units to buy for `need` fitted parts, before rounding to packs."""
    if code in ('R7590',):
        return 30                    # 22k: ten to match from thirty
    if code in ('R7578',):
        return max(need + 8, 10)     # 6k8: R21/R22 matched from a pack
    if code == 'Z1044':
        return 50                    # sort a matched pair and quad from fifty
    if code == 'P5410':
        return 1                     # one 2 x 40 strip makes both headers
    if code.startswith(('R75', 'R76')):
        return need + 2
    if code.startswith(('R2', 'R4', 'R5', 'R6', 'Z0')):
        return need + 2
    if code.startswith(('Z27', 'Z28')):
        return need + 1
    return need


# Not in either schematic, still needed to build one module
EXTRAS = [
 ('P0550', 'U1-U7', 10, 'DIP-8 sockets for the op amps (the footprints are socket outlines). '
                        'The LM391x go in direct: sockets would foul the meter LEDs.'),
 ('H6545', 'RV2-RV6', 5, 'Knobs. 11 mm across: ATTACK and RELEASE are only 15.1 mm apart, '
                         'so anything over ~13 mm clashes.'),
 ('P1023', 'J1-J2', 1, 'Board-to-board ribbon: 30 single-way sockets each end, 150 mm. '
                       'Unkeyed, so keep wire 1 on pin 1 at both ends. Lay the boards out '
                       'first: 150 mm is an estimate.'),
 ('H3110A', 'bracket', 1, 'M3 screws for the L-bracket to H1/H2 and the panel.'),
 ('H3175', 'bracket', 1, 'M3 nuts.'),
]
ELSEWHERE = [
 ('bracket', '25 x 25 mm aluminium angle, ~40 mm long', 'hardware store'),
 ('panel', 'Faceplate 38.10 x 133.35 x 3.18 mm aluminium, from panel/faceplate.dxf', 'panel shop'),
]


def build():
    lines = {}
    for board, ref, val, fp in parts():
        code, note, alt = choose(ref, val, fp)
        key = (board, code or 'none:' + val + ':' + ref.rstrip('0123456789'), note, alt)
        lines.setdefault(key, []).append((ref, val))
    rows = []
    for (board, code, note, alt), refs in lines.items():
        refs.sort(key=lambda r: nk(r[0]))
        rows.append(dict(board=board, refs=[r for r, v in refs], value=refs[0][1],
                         code=None if code.startswith('none:') else code, note=note, alt=alt))
    for code, refs, qty, note in EXTRAS:
        rows.append(dict(board='hardware', refs=[refs], value='', code=code, note=note,
                         alt='', fixed=qty))
    order = {'front': 0, 'main': 1, 'hardware': 2}
    rows.sort(key=lambda r: (order[r['board']], r['code'] is None, nk(r['refs'][0])))
    # The same Altronics code on both boards orders once: the first row carries the order
    need = {}
    for r in rows:
        if r['code'] and 'fixed' not in r:
            need[r['code']] = need.get(r['code'], 0) + len(r['refs'])
    done, first = set(), {}
    for r in rows:
        c = r['code']
        r['qty'] = r.get('fixed') or len(r['refs'])
        if not c:
            r.update(order='', pack='', unit='', total=0.0, desc='', stock='')
            continue
        desc, pack, tiers, stock = CAT[c]
        r.update(desc=desc, pack=pack, stock=stock)
        if 'fixed' in r:
            units = r['fixed'] * pack
        elif c in done:
            r.update(order='see %s' % first[c], unit='', total=0.0)
            continue
        else:
            units = spare(c, need[c])
            done.add(c)
            first[c] = r['refs'][0]
        packs = math.ceil(units / pack)
        unit = 0
        for q, price in tiers:
            if packs >= q:
                unit = price
        r.update(order=packs, unit=unit, total=round(packs * unit, 2))
    return rows


def main():
    rows = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Board', 'References', 'Value', 'Qty fitted', 'Altronics code',
                    'Altronics description', 'Pack size', 'Order (packs)',
                    'Unit price inc GST', 'Line total inc GST',
                    'Stock (delivery / Auburn NSW) on ' + CHECKED, 'Notes',
                    'If not at Altronics'])
        for r in rows:
            w.writerow([r['board'], ' '.join(r['refs']), r['value'], r['qty'],
                        r['code'] or 'NOT STOCKED', r['desc'], r['pack'], r['order'],
                        '%.2f' % r['unit'] if r['unit'] else '',
                        '%.2f' % r['total'] if r['total'] else '', r['stock'], r['note'],
                        r['alt']])
        for what, desc, where in ELSEWHERE:
            w.writerow(['hardware', what, '', 1, 'NOT STOCKED', desc, '', '', '', '', '', '',
                        where])
        total = sum(r['total'] for r in rows)
        w.writerow([])
        w.writerow(['', '', '', '', '', 'Altronics total, inc GST, excluding postage', '',
                    '', '', '%.2f' % total, 'checked ' + CHECKED, '', ''])

    missing = [r for r in rows if not r['code'] and 'Nothing to order' not in r['note']]
    print('%-6s %-26s %-8s %4s %-7s %5s %7s  %s'
          % ('BOARD', 'REFS', 'VALUE', 'QTY', 'CODE', 'ORDER', 'TOTAL', 'STOCK'))
    for r in rows:
        refs = ' '.join(r['refs'])
        print('%-6s %-26s %-8s %4d %-7s %5s %7s  %s'
              % (r['board'][:6], refs[:26], r['value'][:8], r['qty'], r['code'] or '-',
                 r['order'], '%.2f' % r['total'] if r['total'] else '', r['stock']))
    print('\nAltronics total $%.2f inc GST (prices and stock as seen %s)' % (total, CHECKED))
    print('%d lines not stocked at Altronics: %s'
          % (len(missing), ', '.join(' '.join(r['refs']) for r in missing)))
    print('wrote', os.path.relpath(OUT, ROOT))
    if '--check' in sys.argv and any(r['note'] == 'No rule for this part.' for r in rows):
        sys.exit(1)


if __name__ == '__main__':
    main()
