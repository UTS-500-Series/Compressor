#!/usr/bin/env python3
"""Check the schematic against design.py, net by net and pin by pin.

This catches the failure ERC cannot see. If a wire is dragged so its endpoint lands on a
neighbouring node, two signal nets short together - and ERC reports nothing, because every
pin is still connected to *something*. Only comparing the exported netlist against the
intended one finds it.

Usage:
    python3 verify_netlist.py                     # finds the .kicad_sch next to this repo
    python3 verify_netlist.py path/to/root.kicad_sch
Exit code is 0 when the schematic matches, 1 when it does not.
"""
import os, subprocess, sys, tempfile, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexp, design
from route_sch import KC


def find_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, '..', 'kicad'))
    for f in sorted(glob.glob(os.path.join(root, '*.kicad_sch'))):
        txt = open(f).read(4000)
        if '(sheet' in txt and 'Sheetfile' in txt:      # the root sheet owns sub-sheets
            return f
    cands = glob.glob(os.path.join(root, '*.kicad_sch'))
    if cands: return cands[0]
    sys.exit('No .kicad_sch found in %s' % root)


def intended():
    want = {}
    for p in design.PARTS:
        if p[0].startswith('#'):
            continue
        for pin, net in p[6].items():
            if net in design.NO_CONNECT:
                continue
            want.setdefault(net, set()).add((p[0], pin))
    return want


def exported(sch):
    out = os.path.join(tempfile.mkdtemp(), 'check.net')
    r = subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                        '-o', out, sch], capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit('kicad-cli failed.\n%s\n\nIs kicad-cli installed? Set KICAD_CLI if it is '
                 'not on PATH.' % r.stderr[-600:])
    node, _ = sexp.parse_one(sexp.tokenize(open(out).read()))
    nets = {}
    for n in sexp.getall(sexp.get(node, 'nets'), 'net'):
        nm = str(sexp.get(n, 'name')[1])
        nm = nm.rsplit('/', 1)[-1] if nm.startswith('/') else nm    # strip sheet path
        nets[nm] = {(str(sexp.get(x, 'ref')[1]), str(sexp.get(x, 'pin')[1]))
                    for x in sexp.getall(n, 'node')}
    comps = [str(sexp.get(c, 'ref')[1])
             for c in sexp.getall(sexp.get(node, 'components'), 'comp')]
    return nets, comps


def main():
    sch = sys.argv[1] if len(sys.argv) > 1 else find_root()
    print('schematic : %s' % os.path.basename(sch))
    want = intended()
    got, comps = exported(sch)

    by_members = {frozenset(v): k for k, v in got.items()}
    bad = []
    for net, pins in sorted(want.items()):
        if frozenset(pins) in by_members:
            continue
        overlapping = {nm: mem for nm, mem in got.items() if mem & pins}
        bad.append((net, pins, overlapping))

    exp_refs = {p[0] for p in design.PARTS if not p[0].startswith('#')}
    missing = sorted(exp_refs - set(comps))
    extra = sorted(set(comps) - exp_refs)

    print('components: %d found, %d expected' % (len(comps), len(exp_refs)))
    print('nets      : %d matched, %d wrong, %d total'
          % (len(want) - len(bad), len(bad), len(want)))
    if missing: print('MISSING components:', ', '.join(missing))
    if extra:   print('UNEXPECTED components:', ', '.join(extra))

    for net, pins, over in bad:
        print('\nNET %s' % net)
        print('   should join : %s' % ', '.join('%s-%s' % p for p in sorted(pins)))
        for nm, mem in sorted(over.items()):
            wrong = mem - pins
            print('   drawn as %-24s %s' % (nm, ', '.join('%s-%s' % p for p in sorted(mem))))
            if wrong:
                print('       shorted to: %s' % ', '.join('%s-%s' % p for p in sorted(wrong)))

    ok = not bad and not missing and not extra
    print('\n%s' % ('SCHEMATIC MATCHES design.py' if ok else 'SCHEMATIC DOES NOT MATCH design.py'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
