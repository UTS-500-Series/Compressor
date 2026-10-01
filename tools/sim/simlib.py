"""Run the compressor's schematic in ngspice from the command line.

The netlist comes straight from the kicad/ sheets (kicad-cli), so it carries the same models
and test bench KiCad's simulator uses. Each run overrides the bench's .param knobs, adds
probes with plain names, and caches its result under build/sim/ keyed on the netlist.
"""
import hashlib, os, shlex, subprocess
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCH = os.path.join(ROOT, 'kicad', 'UTS Mini Mixing Desk - Compressor.kicad_sch')
BUILD = os.path.join(ROOT, 'build', 'sim')
KICAD_CLI = shlex.split(os.environ.get('KICAD_CLI', 'kicad-cli'))

# probe name -> net. Net names with + or - in them can't be used directly in ngspice's
# control language, so every run copies them onto plain-named nodes.
PROBES = {'outd': 'OUT_DIFF', 'outp': 'OUT+', 'outn': 'OUT-', 'ctrl': 'CTRL-B', 'tim': 'TIMING',
          'sta': 'STA', 'stb': 'STB', 'sigvca': 'SIG-VCA', 'outa': 'OUT-A', 'u1a': 'Net-_R4-Pad2_',
          'pad': 'PAD', 'cp': 'Net-_Q4-B_', 'cn': 'Net-_Q5-B_', 'rect': 'RATIO_CW',
          'tail': 'Net-_Q3-C_', 'inp': 'IN+', 'inn': 'IN-'}


def netlist():
    """Export the SPICE netlist once; return its path without the trailing .end."""
    os.makedirs(BUILD, exist_ok=True)
    raw = os.path.join(BUILD, 'compressor.cir')
    subprocess.run(KICAD_CLI + ['sch', 'export', 'netlist', '--format', 'spice', '-o', raw, SCH],
                   check=True, capture_output=True)
    base = os.path.join(BUILD, 'compressor_base.cir')
    lines = [l for l in open(raw).read().splitlines() if l.strip().lower() != '.end']
    open(base, 'w').write('\n'.join(lines) + '\n')
    return base


def deck(base, params, analysis, extra=''):
    lines = ['* compressor run', '.include "%s"' % base]
    lines += ['E_%s P_%s 0 %s 0 1' % (k, k, v) for k, v in PROBES.items()]
    lines += ['R_%s P_%s 0 1G' % (k, k) for k in PROBES]
    lines += [extra, '.control', 'set filetype=ascii']
    lines += ['alterparam %s = %s' % (k, v) for k, v in params.items()]
    vecs = ' '.join('v(P_%s)' % k for k in PROBES) + ' i(VPOS) i(VNEG)'
    lines += ['reset', 'save ' + vecs, analysis, 'wrdata {out} ' + vecs, '.endc', '.end']
    return '\n'.join(lines)


def run(base, params, analysis, extra=''):
    """Run one analysis; returns {probe: array} plus 't' (or frequency) and supply currents."""
    d = deck(base, params, analysis, extra)
    models = open(os.path.join(ROOT, 'kicad', 'sim', 'compressor_models.lib')).read()
    h = hashlib.md5((d + open(base).read() + models).encode()).hexdigest()[:12]
    out = os.path.join(BUILD, h + '.txt')
    if not os.path.exists(out):
        cir = os.path.join(BUILD, h + '.cir')
        open(cir, 'w').write(d.replace('{out}', out + '.tmp'))
        r = subprocess.run(['ngspice', '-b', cir], capture_output=True, text=True)
        if not os.path.exists(out + '.tmp'):
            raise RuntimeError('ngspice failed:\n' + r.stdout[-2000:] + r.stderr[-2000:])
        os.rename(out + '.tmp', out)
    a = np.loadtxt(out)
    names = list(PROBES) + ['ipos', 'ineg']
    cols = {k: a[:, 2 * i + 1] for i, k in enumerate(names)}
    cols['t'] = a[:, 0]
    return cols


def ac(base, params, sweep):
    """AC sweep of the balanced output's magnitude; returns (frequency, gain in dB)."""
    out = os.path.join(BUILD, 'ac.txt')
    d = deck(base, params, sweep, '').replace(
        'wrdata {out} ', 'let g = db(mag(v(P_outd)))\nwrdata %s g\n* ' % out)
    cir = os.path.join(BUILD, 'ac.cir')
    open(cir, 'w').write(d)
    subprocess.run(['ngspice', '-b', cir], capture_output=True, text=True, check=True)
    a = np.loadtxt(out)
    return a[:, 0], a[:, 1]


def rms(t, x, t0, t1):
    m = (t >= t0) & (t <= t1)
    return float(np.sqrt(np.trapezoid(x[m] ** 2, t[m]) / (t[m][-1] - t[m][0])))


def dbu(v):
    return 20 * np.log10(v / 0.7746)


def tone(env, freq=1000):
    """Extra bench lines: a balanced tone whose peak (differential) follows the expression
    env(time). The bench's own source is silenced with LEVEL_DBU=-300 and this one is added
    in parallel, 50 ohm per leg, so IN+ and IN- see half of each leg's voltage."""
    return '\n'.join(['BTP SRC2+ 0 V = %s * sin(2 * pi * %g * time)' % (env, freq),
                      'BTN SRC2- 0 V = -%s * sin(2 * pi * %g * time)' % (env, freq),
                      'RTP SRC2+ IN+ 50', 'RTN SRC2- IN- 50'])


def peak(dbu_level):
    return 0.7746 * np.sqrt(2) * 10 ** (dbu_level / 20)


def thd(t, x, f0=1000, n=20):
    """Harmonic distortion (2nd to 10th harmonics) over the last n cycles, in percent."""
    t1 = t[-1]; t0 = t1 - n / f0
    tu = np.linspace(t0, t1, n * 512, endpoint=False)
    X = np.abs(np.fft.rfft(np.interp(tu, t, x) * np.hanning(len(tu))))
    fund = np.sqrt(np.sum(X[n - 2:n + 3] ** 2))
    harm = np.sqrt(sum(np.sum(X[h * n - 2:h * n + 3] ** 2) for h in range(2, 11)))
    return 100 * harm / fund
