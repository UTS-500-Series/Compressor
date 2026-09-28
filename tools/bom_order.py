#!/usr/bin/env python3
"""Builds a DigiKey-uploadable parts list from design.py.

    python3 tools/bom_order.py            > digikey-upload.csv
    python3 tools/bom_order.py --table    # readable version

Quantities come from the netlist, so this cannot drift from the schematic the way a
hand-kept spreadsheet does. Manufacturer part numbers are a different matter: design.py
records a value, a tolerance and a footprint, which is not enough to name a part. Where a
generic type number IS the orderable part (1N4148, NE5532P, LM3914N) it is filled in;
everywhere else the column is deliberately blank, because guessing a resistor series or a
capacitor dielectric on someone's behalf is how you end up with 200 V film caps that do not
fit the board.

ORDER quantity carries prototype margin - you will lose parts, and a second postage charge
costs more than a hundred resistors.
"""
import sys, os, re, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design

# Parts held to 0.1% because a ratio, not a value, is what matters. From the design notes:
# input/recovery balance, the thump-rejection pair, and the steering rest offset.
TIGHT = {'R1','R2','R3','R4','R23','R24','R80','R81','R82','R83',   # 22k CMRR network
         'R21','R22',                                              # 3k3 thump rejection
         'R61','R62'}                                              # steering rest offset

# value -> (dielectric / type, voltage) for the capacitors
CAPSPEC = {'100p': ('C0G/NP0', '50 V'), '1n': ('C0G/NP0', '50 V'), '10n': ('X7R', '50 V'),
           '100n': ('X7R', '50 V'), '220n': ('film', '63 V'), '2u2': ('film', '63 V'),
           '10u': ('film', '63 V'), '22u': ('bipolar electrolytic', '50 V'),
           '47u': ('electrolytic', '25 V'), '100u': ('electrolytic', '25 V')}

PKG = {'R_Axial_DIN0207': 'axial 0207, 10.16 mm pitch',
       'C_Disc_D5.0mm': 'disc, 5 mm pitch', 'C_Rect_L7.0mm': 'box film, 5 mm pitch',
       'CP_Radial_D6.3mm': 'radial 6.3 mm, 2.5 mm pitch',
       'D_DO-35': 'DO-35', 'D_DO-41': 'DO-41', 'LED_D3.0mm': '3 mm', 'LED_D2.0mm': '2 mm',
       'TO-92': 'TO-92', 'DIP-8': 'DIP-8', 'DIP-18': 'DIP-18',
       'Potentiometer_Alps_RK09K': 'Alps RK09K, 9 mm vertical',
       'Potentiometer_Bourns_3296W': 'Bourns 3296W, multiturn'}

# Verified at DigiKey AU on 2026-09-02 by looking the part up, not from memory.
#
# Resistors: Yageo MFR-25FBF52, 0.25 W 1% axial metal film - 648 values stocked, and the
# suffix is just the value in the same notation design.py already uses (100R, 1K33, 23K2).
# Confirmed against -10K, -1K33 and -100R, which covers the plain, decimal and ohms forms.
# NOTE the series is 1%: see TIGHT below for the four positions that ask for 0.1%.
RES_SERIES = 'MFR-25FBF52-%s'

# Only where the generic type number is itself the orderable part.
MPN = {
'NE5532': 'NE5532P', 'LM3914': 'LM3914N-1/NOPB', 'LM3915': 'LM3915N-1/NOPB',
       'BC549C': 'BC549C', '1N4148': '1N4148', '1N4004': '1N4004',
       'BZX79-C5V1': 'BZX79-C5V1',
       # Vishay Monolythic 1C20, 5.08 mm pitch - fits the 5 mm footprint. 2,983 in stock,
       # $0.71. The AVX SR275C104KAR is cheaper-looking but is 7.62 mm pitch and will not.
       '100n': '1C20X7R104K050B'}

NOTE = {
 'LM3914': 'CHECKED 2026-09-02, DigiKey AU: OBSOLETE, 0 stock. So is every other dot/bar '
           'driver they list - all 13, TI and Rohm alike. No drop-in exists; source it '
           'elsewhere or rework the meter sheet around comparators.',
 'LM3915': 'CHECKED 2026-09-02, DigiKey AU: OBSOLETE, 0 stock. So is every other dot/bar '
           'driver they list - all 13, TI and Rohm alike. No drop-in exists; source it '
           'elsewhere or rework the meter sheet around comparators.',
 'NE5532': 'CHECKED 2026-09-02, DigiKey AU: Texas Instruments, 8-DIP, $1.18 AUD.',
 'BC549C': 'Buy loose and sort: Q1/Q2 need a matched pair and Q6-Q9 a matched quad, '
           'all from one batch. 100 gives a usable spread to sort from.',
 '10u':    'C15 is the timing capacitor. Film, low leakage - an electrolytic here makes '
           'the release time drift.',
 '22u':    'Non-polarised / bipolar. These sit in the input path with no DC across them.',
 '1k33':   '0.1%. Sets the steering rest offset with R62 - do not substitute.',
 '23k2':   '0.1%. Sets the steering rest offset with R61 - do not substitute.',
 '75R':    'Sets the pad depth with R7 and RV1.',
 '0R':     'Yageo MFR-25 has no 0R. This is the PGND-to-AGND star link, so a wire link through the two pads is the right part - do not order anything.',
 '100n':   'Vishay 1C20, 5.08 mm pitch. Checked 2026-09-02: 2,983 in stock, $0.71. The AVX SR275C104KAR looks cheaper but is 7.62 mm pitch and will not fit the footprint.',
 '2k7':    'Sets meter LED current, 12.5/R. Both drivers use one each.',
 '8k2':    'R7 sets the pad; R90/R92 set meter full scale at 1.25*(1+R/2k7).',
}


def pkg_of(fp):
    for k, v in PKG.items():
        if k in fp:
            return v
    return fp.split(':')[-1] if fp else ''


def search_url(cat, val, desc):
    """A DigiKey search for the lines with no part number yet.

    Better than a blank cell and better than a guess: one click lands on the filtered
    results for that exact value, package and rating, and you pick the part. Choosing a
    capacitor dielectric or a switch bushing on someone else's behalf is not a thing to
    do from a description."""
    import urllib.parse
    terms = {'Capacitor':  val.replace('u', 'uF').replace('n', 'nF').replace('p', 'pF'),
             'Resistor':   val, 'LED': val, 'Potentiometer': val + ' potentiometer',
             'Switch':     val + ' toggle switch panel mount',
             'Connector':  '15 position card edge connector 0.156',
             'Diode': val, 'Zener': val, 'Transistor': val, 'IC': val}.get(cat, val)
    extra = {'Capacitor': ' through hole radial', 'LED': ' through hole',
             'Potentiometer': ' 9mm vertical'}.get(cat, '')
    return 'https://www.digikey.com.au/en/products/result?keywords=' + \
           urllib.parse.quote(str(terms) + extra)


def margin(cat, qty):
    """Prototype order quantity."""
    if cat == 'Transistor':               return 100          # matching needs a population
    if cat in ('Resistor', 'Capacitor'):  return max(10, qty + 5)
    if cat in ('Diode', 'Zener', 'LED'):  return max(5, qty + 3)
    return qty + 1                                            # ICs, pots, switches, connector


def rows():
    CAT = {'R': 'Resistor', 'C': 'Capacitor', 'C_Polarized': 'Capacitor', 'D': 'Diode',
           'D_Zener': 'Zener', 'LED': 'LED', 'BC549': 'Transistor', 'NE5532': 'IC',
           'LM3914N': 'IC', 'R_Potentiometer': 'Potentiometer', 'Conn_01x15': 'Connector'}
    seen = {}
    for p in design.PARTS:
        if p[0].startswith('#'):
            continue
        seen.setdefault(p[0], (p[2], p[3], p[4]))          # sym, value, footprint
    groups = collections.defaultdict(list)
    for ref, (sym, val, fp) in seen.items():
        cat = CAT.get(sym) or ('Switch' if ref.startswith('SW') else sym)
        if sym == 'LED' and ref != 'LED1':
            val = '2 mm meter'
        if cat == 'LED' and ref == 'LED1':
            val = '3 mm indicator'
        if cat == 'Switch':
            # the value names the panel function; the symbol is what you actually order
            val = {'SW_DPDT_x2': 'DPDT', 'SW_SPDT': 'SPDT', 'SW_SPST': 'SPST'}.get(sym, sym)
        groups[(cat, val, pkg_of(fp))].append(ref)

    def nk(s):
        return [(1, int(t)) if t.isdigit() else (0, t) for t in re.findall(r'\d+|\D+', str(s))]

    out = []
    for (cat, val, pkg), refs in sorted(groups.items(), key=lambda kv: (nk(kv[0][0]), nk(kv[0][1]))):
        refs = sorted(refs, key=nk)
        tol = ''
        if cat == 'Resistor':
            tol = '0.1%' if any(r in TIGHT for r in refs) else '1%'
            desc = 'Resistor %s %s, 0.25 W metal film, %s' % (val, tol, pkg)
        elif cat == 'Capacitor':
            d, v = CAPSPEC.get(val, ('', ''))
            desc = 'Capacitor %s %s %s, %s' % (val, d, v, pkg)
        elif cat == 'Potentiometer':
            law = 'multiturn trimmer' if '3296' in pkg else 'linear'
            desc = 'Potentiometer %s %s, %s' % (val, law, pkg)
        elif cat == 'Connector':
            desc = '15-pin 0.156 in card edge, 500-series backplane (e.g. EDAC 306-015-520-102)'
        elif cat == 'Switch':
            desc = 'Switch %s, panel mount, mini toggle' % val
        else:
            desc = '%s %s, %s' % (cat, val, pkg)
        mpn = MPN.get(val, '')
        if cat == 'Resistor' and val != '0R':
            mpn = RES_SERIES % val.upper()
        note = NOTE.get(val, '')
        if tol == '0.1%':
            # The listed series is 1%. For the CMRR network and the 3k3 pair what matters is
            # that the parts MATCH, not that they are accurate: buy 1% and sort with a meter
            # and you will beat 0.1% absolute. R61/R62 are the exception - the rest offset
            # depends on their actual values, so those two want real 0.1% parts.
            hint = ('R61/R62 set the steering rest offset by absolute value - order these '
                    'two as 0.1%, the listed 1% part will not do.'
                    if any(r in ('R61', 'R62') for r in refs) else
                    'Matching matters here, not absolute value. Order extra 1% and sort '
                    'them with a meter - that beats 0.1% absolute for a ratio.')
            note = (note + ' ' if note else '') + hint
        out.append(dict(cat=cat, value=val, qty=len(refs), order=margin(cat, len(refs)),
                        mpn=mpn, refs=' '.join(refs), desc=desc, note=note,
                        search='' if mpn else search_url(cat, val, desc)))
    return out


EXTRAS = [
    (9,  '', 'U1-U9', 'DIP socket, 8-pin (x7) and 18-pin (x2) - see note', 9,
     'Not in the netlist. Socket everything on a prototype: U4 is documented as swappable '
     'for a TL072 or OPA2134, and the LM391x drivers are the parts most likely to be wrong '
     'first time. Order 7 x DIP-8 and 2 x DIP-18.'),
    (6,  '', 'RV2-RV6', 'Knob for 6 mm shaft, to suit Alps RK09K', 6,
     'Not in the netlist. Five panel pots plus a spare. RV1, RV7 and RV8 are board trimmers '
     'and take no knob.'),
    (1,  '', 'panel', 'Faceplate, 38.10 x 133.35 x 3.18 mm aluminium', 1,
     'Not in the netlist. panel/faceplate.dxf is the 1:1 cutting file.'),
]


if __name__ == '__main__':
    rs = rows()
    if '--table' in sys.argv:
        print('%-14s %-12s %4s %6s  %-16s %s' % ('CATEGORY', 'VALUE', 'REQ', 'ORDER', 'MPN', 'REFS'))
        print('-' * 108)
        for r in rs:
            print('%-14s %-12s %4d %6d  %-16s %s'
                  % (r['cat'], r['value'], r['qty'], r['order'], r['mpn'] or '-', r['refs'][:44]))
        print('-' * 108)
        print('%d line items, %d parts on the board, %d to order'
              % (len(rs), sum(r['qty'] for r in rs), sum(r['order'] for r in rs)))
        print('%d lines still need a manufacturer part number chosen'
              % sum(1 for r in rs if not r['mpn']))
    else:
        w = csv.writer(sys.stdout)
        w.writerow(['Quantity', 'Manufacturer Part Number', 'Customer Reference',
                    'Description', 'Required on board', 'Notes',
                    'DigiKey search (lines with no part number)'])
        for r in rs:
            w.writerow([r['order'], r['mpn'], r['refs'], r['desc'], r['qty'], r['note'],
                        r['search']])
        for q, mpn, ref, desc, req, note in EXTRAS:
            w.writerow([q, mpn, ref, desc, req, note, ''])
