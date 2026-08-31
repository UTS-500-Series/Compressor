#!/usr/bin/env python3
"""Builds data/<sheet>.json for the interactive viewer.

Two things come out of this:
  * component boxes in sheet millimetres, read from the real .kicad_sch files, so the
    clickable overlay lines up with the exported SVG whatever the layout looks like
  * the netlist as a bipartite graph (component nodes + net nodes), which is the honest
    way to draw a netlist - a net joins N pins, not 2
"""
import json, os, re, sys
# tooling lives in ../tools, inside this repository
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))
import sexp
from route_sch import resolve_symbol, symbol_pins, place_pin

SHEETS = {'connector': 'connector.kicad_sch', 'input': 'input.kicad_sch',
          'vca': 'vca.kicad_sch', 'output': 'output.kicad_sch',
          'sidechain': 'sidechain.kicad_sch', 'power': 'power.kicad_sch'}

POWER  = {'+16V', '-16V', '-5V1', '+16V-IN', '-16V-IN', 'VBIAS', 'VREF5', 'VREFA'}
GROUND = {'AGND', 'PGND', 'CHASSIS'}
CONTROL = {'STA','STB','CTRL','CTRL-B','RECT','SC-AMP','SCBUF','SCF','SCSEL','RV3O',
           'RATW','LINKN','ATKO','D7K','RELO','S1','S2','XN','U3BO','KEY','LINK',
           'NINV3A','NINV3B','NINV4A','INV3A','INV4B','LED-A'}

def net_class(n):
    if n in GROUND: return 'gnd'
    if n in POWER: return 'pwr'
    if n in CONTROL: return 'ctl'
    return 'sig'

KIND = {'R':'res','C':'cap','D':'dio','Q':'tr','U':'ic','RV':'pot','SW':'sw','J':'conn','LED':'led'}
def kind(ref):
    m = re.match(r'^(LED|RV|SW|[A-Z]+)', ref)
    return KIND.get(m.group(1), 'other') if m else 'other'

NOTES = {
 'R1':'Sets input CMRR with R2-R4. 0.1% part.','R2':'Sets input CMRR. 0.1% part.',
 'R3':'Sets input CMRR. 0.1% part.','R4':'Difference-amp feedback. 0.1% part.',
 'R7':'Top of the input pad.','R8':'Bottom of the input pad - sets through gain. 75 ohm.',
 'RV1':'Unity-gain trim. The only audio trim in the module.',
 'R14':'Emitter degeneration for Q1.','R15':'Emitter degeneration for Q2.',
 'R16':'Collector load - turns steered current back into voltage.',
 'R17':'Collector load - turns steered current back into voltage.',
 'R18':'Sets the ~3 mA tail current.',
 'R21':'0.1% - pairs with R23 for thump rejection.','R22':'0.1% - pairs with R24.',
 'R23':'0.1% recovery-amp feedback.','R24':'0.1% recovery-amp reference leg.',
 'R45':'Series resistor into the stereo-link bus.',
 'R48':'0 ohm star-ground link. Fit exactly one.',
 'R61':'0.1% - sets the steering rest offset.','R62':'0.1% - sets the steering rest offset.',
 'R68':'Scales the control voltage down to the ~250 mV the steering pair needs.',
 'R74':'Matches the release network so U4B bias current cancels.',
 'Q1':'Signal transconductor. Matched pair with Q2, thermally bonded.',
 'Q2':'Signal transconductor. Matched pair with Q1, thermally bonded.',
 'Q3':'Constant tail current source - about 3 mA, fixed.',
 'Q4':'Emitter follower buffering collector CP.','Q5':'Emitter follower buffering collector CN.',
 'Q6':'Steering - dump side. Matched quad Q6-Q9.','Q7':'Steering - signal side. Matched quad Q6-Q9.',
 'Q8':'Steering - dump side. Matched quad Q6-Q9.','Q9':'Steering - signal side. Matched quad Q6-Q9.',
 'C1':'Input DC block, bipolar.','C2':'Input DC block, bipolar.',
 'C9':'Recovery-amp coupling.','C10':'Recovery-amp coupling.',
 'C14':'Sidechain high-pass, 72 Hz with R38.',
 'C15':'Timing capacitor - its voltage IS the control signal. Film, low leakage.',
 'D5':'Precision rectifier diode, inside U3B feedback loop.',
 'D6':'Precision rectifier diode, inside U3B feedback loop.',
 'D7':'Separates attack from release - charge in, no discharge back.',
 'D8':'Reverse-polarity clamp, cathode up.','D9':'Reverse-polarity clamp, cathode up.',
 'D10':'5.1 V zener - the reference the tail current source hangs off.',
 'U1':'A: input receiver. B: recovery amplifier.',
 'U2':'A: makeup gain. B: output inverter.',
 'U3':'A: sidechain amp. B: rectifier first half.',
 'U4':'A: rectifier summer. B: control buffer. Fit a TL072 here instead.',
 'U5':'A: aux key receiver. B: aux output buffer.',
 'U6':'A: STA reference buffer. B: sidechain input buffer.',
 'RV2':'MAKEUP - 0 to +21 dB.','RV3':'THRESHOLD - wired as a rheostat.',
 'RV4':'RATIO.','RV5':'ATTACK - 2.7 to 50 ms.','RV6':'RELEASE - 47 ms to 2.2 s.',
 'SW1':'Hard bypass - routes the rack straight through.',
 'SW2':'Detector source: this channel, or the aux key input.',
 'SW3':'Shorts out the 72 Hz sidechain filter.','SW4':'Stereo link to pin 6.',
 'LED1':'Gain-reduction indicator. Brightness tracks compression.',
 'J1':'500-series 15-pin card edge.',
}

def boxes(path):
    root, _ = sexp.parse_one(sexp.tokenize(open(path).read()))
    out = {}
    for sym in sexp.getall(root, 'symbol'):
        lib = sexp.get(sym, 'lib_id')
        if not lib: continue
        ref = val = None
        for pr in sexp.getall(sym, 'property'):
            if str(pr[1]) == 'Reference': ref = str(pr[2])
            if str(pr[1]) == 'Value': val = str(pr[2])
        if not ref or ref.startswith('#'): continue
        at = sexp.get(sym, 'at'); X, Y, rot = float(at[1]), float(at[2]), int(float(at[3]))
        unit = int(sexp.get(sym, 'unit')[1])
        geo = symbol_pins(resolve_symbol(*str(lib[1]).split(':')))
        src = geo.get(unit, {}) or geo.get(1, {})
        pts = [place_pin(v[0], v[1], X, Y, rot) for v in src.values()] or [(X, Y)]
        xs = [p[0] for p in pts] + [X]; ys = [p[1] for p in pts] + [Y]
        pad = 1.6
        b = [min(xs)-pad, min(ys)-pad, max(xs)-min(xs)+2*pad, max(ys)-min(ys)+2*pad]
        if ref in out:                      # multi-unit part: union the boxes
            o = out[ref]['box']
            x0, y0 = min(o[0], b[0]), min(o[1], b[1])
            x1, y1 = max(o[0]+o[2], b[0]+b[2]), max(o[1]+o[3], b[1]+b[3])
            out[ref]['box'] = [x0, y0, x1-x0, y1-y0]
        else:
            out[ref] = {'ref': ref, 'value': val, 'box': [round(v, 2) for v in b]}
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.join(here, '..')
    import design

    # component -> sheet, and its pin/net map, from the authoritative netlist
    BLOCK2SHEET = {
        'CONNECTOR': 'connector', 'SH1 INPUT RECEIVER AND PAD': 'input',
        'SH2 STEERING VCA AND RECOVERY AMP': 'vca',
        'SH3 MAKEUP, OUTPUT DRIVERS AND AUX': 'output',
        'SH4 SIDECHAIN DETECTOR': 'sidechain',
        'SH5 POWER, REFERENCES AND METER': 'power',
        'SH5 SUPPLY DECOUPLING': 'power'}
    # Key by (ref, sheet): an NE5532 has unit A on one sheet, unit B on another and its
    # supply pins on a third. Merging them would list nets that are not on the sheet you
    # are looking at, so each sheet only ever sees the pins actually drawn on it.
    comp = {}
    for p in design.PARTS:
        ref, val, fp, blk, pinmap = p[0], p[3], p[4], p[5], p[6]
        if ref.startswith('#'): continue
        sheet = BLOCK2SHEET[blk]
        c = comp.setdefault((ref, sheet), {'ref': ref, 'value': val, 'fp': fp,
                                           'sheet': sheet, 'pins': {}})
        c['pins'].update(pinmap)

    # the full netlist, across all sheets
    nets = {}
    for c in comp.values():
        for pn, n in c['pins'].items():
            nets.setdefault(n, []).append([c['ref'], pn])

    total = 0
    for sheet, fname in SHEETS.items():
        bx = boxes(os.path.join(proj, fname))
        svg = open(os.path.join(here, 'img', sheet + '.svg')).read(4000)
        vb = re.search(r'viewBox="([\d.\s]+)"', svg).group(1).split()
        mine = {r: c for (r, sh), c in comp.items() if sh == sheet}
        comps = []
        for r, c in sorted(mine.items()):
            comps.append({
                'ref': r, 'value': c['value'], 'fp': c['fp'].split(':')[-1],
                'kind': kind(r), 'note': NOTES.get(r, ''),
                'box': bx.get(r, {}).get('box'),
                'pins': c['pins'],
            })
        onsheet = {(c['ref'], pn) for c in mine.values() for pn in c['pins']}
        used = sorted({n for c in mine.values() for n in c['pins'].values()})
        netlist = []
        for n in used:
            here_pins = [p for p in nets[n] if tuple(p) in onsheet]
            netlist.append({'name': n, 'cls': net_class(n), 'pins': here_pins,
                            'offsheet': len(nets[n]) - len(here_pins)})
        data = {'sheet': sheet, 'w': float(vb[2]), 'h': float(vb[3]),
                'components': comps, 'nets': netlist}
        out = os.path.join(here, 'data', sheet + '.json')
        open(out, 'w').write(json.dumps(data, separators=(',', ':')))
        missing = [c['ref'] for c in comps if not c['box']]
        total += len(comps)
        print('%-10s %3d parts %3d nets %6.1f KB%s'
              % (sheet, len(comps), len(netlist), os.path.getsize(out)/1024,
                 '   NO BOX: ' + ','.join(missing) if missing else ''))
    print('total %d components' % total)


if __name__ == '__main__':
    main()
