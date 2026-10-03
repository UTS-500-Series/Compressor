#!/usr/bin/env python3
"""Give every part on the kicad/ sheets a SPICE model, so KiCad's simulator can run the design.

Writes Sim.* fields onto the symbol instances (models in kicad/sim/compressor_models.lib)
and marks the two connectors excluded from simulation. Safe to run again: it replaces the
Sim.* fields it finds. The pots and switches take their settings from .param names
(THRESHOLD, RATIO, ...) that kicad/sim/bench.cir defines, so the knobs live in one place.

    python3 tools/add_sim_models.py
"""
import glob, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, '..', 'kicad')
LIB = 'sim/compressor_models.lib'

# pot reference -> the .param that sets its wiper position (0 = pin 1 end, 1 = pin 3 end)
POT_PARAM = {'RV1': 'TRIM', 'RV2': 'MAKEUP', 'RV3': 'THRESHOLD', 'RV4': 'RATIO',
             'RV5': 'ATTACK', 'RV6': 'RELEASE', 'RV7': 'GRTRIM', 'RV8': 'LVLTRIM'}
# RV4 is wired with its outer pins swapped so clockwise means a harder ratio; this keeps
# RATIO=0 as the hardest setting in the bench and the sim scripts.
POT_REVERSED = {'RV4'}
SWITCH = {'SW1': ('SW_DPDT', 'POS={BYPASS}'), 'SW2': ('SW_SPDT', 'POS={KEY}'),
          'SW3': ('SW_SPST', 'ON={HPF_DEFEAT}'), 'SW4': ('SW_SPST', 'ON={LINK}')}
SEQ = lambda n: ' '.join('%d=%d' % (i, i) for i in range(1, n + 1))


def ohms(v):
    """'4k7' -> '4700', '1M' -> '1000000' (SPICE would read 1M as a milliohm)."""
    m = re.fullmatch(r'(\d+)([RkKM]?)(\d*)', v)
    mult = {'': 1, 'R': 1, 'k': 1e3, 'K': 1e3, 'M': 1e6}[m.group(2)]
    return '%g' % (float(m.group(1) + '.' + (m.group(3) or '0')) * mult)


def fields(lib_id, ref, value):
    """The Sim.* fields for one part, or None to leave it alone, or 'exclude'."""
    if lib_id.startswith('Connector_Generic:'):
        return 'exclude'
    if lib_id == 'Transistor_BJT:BC549':
        return [('Sim.Library', LIB), ('Sim.Name', 'BC549C'), ('Sim.Device', 'NPN'),
                ('Sim.Pins', '1=C 2=B 3=E')]
    if lib_id == 'Amplifier_Operational:NE5532':
        return [('Sim.Library', LIB), ('Sim.Name', 'NE5532_DUAL'), ('Sim.Device', 'SUBCKT'),
                ('Sim.Pins', SEQ(8))]
    if lib_id == 'Driver_LED:LM3914N':
        return [('Sim.Library', LIB), ('Sim.Name', 'LM3914N'), ('Sim.Device', 'SUBCKT'),
                ('Sim.Pins', SEQ(18))]
    if lib_id in ('Device:D', 'Device:D_Zener', 'Device:LED'):
        name = {'Device:D_Zener': 'BZX79C5V1', 'Device:LED': 'LED_GREEN'}.get(lib_id, value)
        return [('Sim.Library', LIB), ('Sim.Name', name), ('Sim.Device', 'D'),
                ('Sim.Pins', '1=K 2=A')]
    if lib_id == 'Device:R_Potentiometer':
        # a trailing A in the value ("250kA") is an audio (log) taper
        taper = ' TAPER=1' if value.endswith('A') else ''
        return [('Sim.Library', LIB), ('Sim.Name', 'POT'), ('Sim.Device', 'SUBCKT'),
                ('Sim.Pins', SEQ(3)),
                ('Sim.Params', 'R=%s POS={%s%s}%s' % (ohms(value.rstrip('A')),
                                                      '1-' if ref in POT_REVERSED else '',
                                                      POT_PARAM[ref], taper))]
    if ref in SWITCH:
        name, params = SWITCH[ref]
        return [('Sim.Library', LIB), ('Sim.Name', name), ('Sim.Device', 'SUBCKT'),
                ('Sim.Pins', SEQ({'SW_DPDT': 6, 'SW_SPDT': 3, 'SW_SPST': 2}[name])),
                ('Sim.Params', params)]
    return None


def prop(name, val, at):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s)\n\t\t\t(show_name no)\n'
            '\t\t\t(do_not_autoplace no)\n\t\t\t(hide yes)\n\t\t\t(effects\n\t\t\t\t(font\n'
            '\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n') % (name, val, at)


def fix(block):
    lib_id = re.search(r'\(lib_id "([^"]+)"\)', block).group(1)
    ref = re.search(r'\(property "Reference" "([^"]+)"', block).group(1)
    value = re.search(r'\(property "Value" "([^"]*)"', block).group(1)
    if ref.startswith('#'):
        return block
    f = fields(lib_id, ref, value)
    if f is None:
        return block
    block = re.sub(r'\t\t\(property "Sim\.[^"]+" .*?\n\t\t\)\n', '', block, flags=re.S)
    if f == 'exclude':
        return block.replace('(exclude_from_sim no)', '(exclude_from_sim yes)')
    at = re.search(r'\n\t\t\(at ([^)]+)\)', block).group(1)
    new = ''.join(prop(k, v, at) for k, v in f)
    i = block.index('\n\t\t(pin ') + 1
    return block[:i] + new + block[i:]


def main():
    for path in sorted(glob.glob(os.path.join(SHEETS, '*.kicad_sch'))):
        t = open(path).read()
        out = re.sub(r'\n\t\(symbol\n\t\t\(lib_id .*?\n\t\)(?=\n)', lambda m: fix(m.group(0)), t,
                     flags=re.S)
        if out != t:
            open(path, 'w').write(out)
            print('updated', os.path.basename(path))


if __name__ == '__main__':
    main()
