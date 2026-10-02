#!/usr/bin/env python3
"""Characterise the compressor in ngspice, straight from the kicad/ schematic.

    python3 tools/sim/run_all.py            # writes kicad/sim/results/

Needs kicad-cli (KiCad 9 or 10), ngspice, numpy and matplotlib. KICAD_CLI can name a wrapper,
for example a Docker image: KICAD_CLI="docker run --rm -v $PWD:$PWD -w $PWD kicad/kicad:10.0 kicad-cli".
Runs are cached in build/sim/, so a second run only redoes what changed. The full set takes
about an hour on four cores.

Levels are differential dBu throughout. Pot positions are 0 to 1 from pin 1 to pin 3, as in
kicad/sim/README.md.
"""
import json, os, sys
from multiprocessing import Pool
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import simlib as S

OUT = os.path.join(S.ROOT, 'kicad', 'sim', 'results')
BASE = None
TYPICAL = dict(ATTACK=0.5, RELEASE=0.5)


def run(params, analysis, extra=''):
    return S.run(BASE, params, analysis, extra)


# ---------------------------------------------------------------- DC and AC
def op_point():
    c = run({}, 'tran 10u 20m 0 20u')
    last = lambda k: float(c[k][-1])
    return dict(STA=last('sta'), STB=last('stb'), steer_mV=1000 * (last('stb') - last('sta')),
                CTRL_B=last('ctrl'), TAIL=last('tail'), collector_loads=last('cp'),
                supply_mA_pos=-1000 * float(c['ipos'][-1]), supply_mA_neg=1000 * float(c['ineg'][-1]))


def ac_response():
    f, g = S.ac(BASE, {}, 'ac dec 40 2 200k')
    g1k = float(np.interp(1000, f, g))
    lo = float(f[np.argmax(g > g1k - 3)])
    hi = float(f[len(g) - 1 - np.argmax(g[::-1] > g1k - 3)])
    return dict(f=f.tolist(), gain=g.tolist(), gain_1k=g1k, f_lo=lo, f_hi=hi,
                at_20=float(np.interp(20, f, g)) - g1k, at_20k=float(np.interp(20e3, f, g)) - g1k)


# ---------------------------------------------------------------- compression curves
L0, L1, RAMP_T = -24.0, 24.0, 8.0
CURVES = [dict(THRESHOLD=t, RATIO=0) for t in (0, 0.25, 0.5, 0.75, 1)] + \
         [dict(THRESHOLD=0.25, RATIO=0.5), dict(THRESHOLD=0, RATIO=0, RELEASE=0)]


def ramp(p):
    """A 1 kHz tone rising slowly from -24 to +24 dBu. Rising, the detector follows on its
    attack time, so each moment is close to the static curve."""
    p = dict(TYPICAL, **p, LEVEL_DBU=-300)
    env = '%g * pwr(10, (%g + %g * time) / 20)' % (S.peak(0), L0, (L1 - L0) / RAMP_T)
    c = run(p, 'tran 10u %g 0 20u' % RAMP_T, S.tone(env))
    t, rows = c['t'], []
    for a in np.arange(0.2, RAMP_T - 0.02, 0.05):
        lin = S.dbu(S.rms(t, c['inp'] - c['inn'], a, a + 0.02))
        lout = S.dbu(S.rms(t, c['outd'], a, a + 0.02))
        m = (t >= a) & (t <= a + 0.02)
        rows.append([float(lin), float(lout), float(np.mean(c['ctrl'][m]))])
    return dict(params=p, rows=rows)


# ---------------------------------------------------------------- attack and release
LO, HI, T1, T2, BURST_THRESHOLD = -10, 20, 0.1, 0.6, 0.5
BURSTS = [('fastest attack', dict(ATTACK=0, RELEASE=0.5), 1.0),
          ('slowest attack', dict(ATTACK=1, RELEASE=0.5), 1.0),
          ('fastest release', dict(ATTACK=0.5, RELEASE=0), 1.2),
          ('slowest release', dict(ATTACK=0.5, RELEASE=1), 8.0)]


def burst(case):
    """-10 dBu, then +20 dBu from 0.1 s to 0.6 s, then -10 dBu again, with the threshold at
    half travel (about 0 dBu); gain measured per cycle."""
    name, p, tend = case
    p = dict(p, THRESHOLD=BURST_THRESHOLD, RATIO=0, LEVEL_DBU=-300)
    env = '(time > %g && time < %g ? %g : %g)' % (T1, T2, S.peak(HI), S.peak(LO))
    c = run(p, 'tran 10u %g 0 20u' % tend, S.tone(env))
    t = c['t']
    edges = np.arange(0.0, tend - 0.001, 0.001)
    gain = [20 * np.log10(S.rms(t, c['outd'], a, a + 0.001) / S.rms(t, c['inp'] - c['inn'], a, a + 0.001))
            for a in edges]
    return dict(name=name, params=p, t=edges.tolist(), gain=gain)


def times(b):
    """Attack: time from the step until 63% of the final reduction. Release: time from the
    step down until 63% of the reduction has gone. Reduction is relative to the gain
    before the burst."""
    t, g = np.array(b['t']), np.array(b['gain'])
    g0 = np.mean(g[(t > 0.05) & (t < 0.095)])
    gr = g0 - g
    on = (t > T1) & (t < T2)
    final = np.mean(gr[(t > T2 - 0.05) & (t < T2)])
    att = float(t[on][np.argmax(gr[on] >= 0.63 * final)] - T1)
    off = t > T2
    start = gr[off][0]
    rel = float(t[off][np.argmax(gr[off] <= 0.37 * start)] - T2) if np.any(gr[off] <= 0.37 * start) else None
    return dict(reduction_dB=float(final), attack_s=att, release_s=rel, peak_reduction_dB=float(np.max(gr[on])))


# ---------------------------------------------------------------- distortion and headroom
THD_CASES = [('no compression, +4 dBu', dict(LEVEL_DBU=4, THRESHOLD=1, RATIO=1)),
             ('bypassed, +4 dBu', dict(LEVEL_DBU=4, BYPASS=1)),
             ('makeup full, +4 dBu', dict(LEVEL_DBU=4, THRESHOLD=1, RATIO=1, MAKEUP=1))] + \
            [('no compression, %+d dBu' % l, dict(LEVEL_DBU=l, THRESHOLD=1, RATIO=1)) for l in (16, 20, 22, 24)] + \
            [('compressing, threshold %g, %+d dBu' % (th, l), dict(TYPICAL, LEVEL_DBU=l, THRESHOLD=th, RATIO=0))
             for th, l in ((0.25, 8), (0, 8), (0, 16))]


def distortion(case):
    name, p = case
    c = run(p, 'tran 10u 1.2 0 5u')
    t = c['t']
    lin = S.dbu(S.rms(t, c['inp'] - c['inn'], 1.1, 1.2))
    lout = S.dbu(S.rms(t, c['outd'], 1.1, 1.2))
    return dict(name=name, params=p, in_dbu=float(lin), out_dbu=float(lout), thd_out=S.thd(t, c['outd']),
                thd_input_stage=S.thd(t, c['u1a']), ctrl=float(np.mean(c['ctrl'][t > 1.1])))


# ---------------------------------------------------------------- plots
def plots(res):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ink, grid = '#222222', '#dddddd'
    colours = ['#1f5fa8', '#3f8fd1', '#7fb4e3', '#b9d6f0', '#c2571a', '#e39a5c', '#666666']
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': ink, 'axes.labelcolor': ink,
                         'xtick.color': ink, 'ytick.color': ink, 'axes.grid': True, 'grid.color': grid})

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    g0 = res['ac']['gain_1k']
    for i, r in enumerate(res['curves']):
        a = np.array(r['rows']); p = r['params']
        lab = 'threshold %g, ratio %g' % (p['THRESHOLD'], p['RATIO'])
        if p['RELEASE'] == 0:
            lab += ', fastest release'
        ax.plot(a[:, 0], a[:, 1], color=colours[i], lw=1.6, label=lab)
    x = np.array([L0, L1])
    ax.plot(x, x + g0, color=ink, lw=0.8, ls='--', label='no compression')
    ax.set_xlabel('Input level (dBu, balanced)'); ax.set_ylabel('Output level (dBu, balanced)')
    ax.set_title('Static compression curves, 1 kHz, makeup at 0', loc='left')
    ax.legend(frameon=False, fontsize=7.5)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'compression.png'), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ac = res['ac']
    ax.semilogx(ac['f'], np.array(ac['gain']) - g0, color=colours[0], lw=1.6)
    ax.set_xlim(5, 200e3); ax.set_ylim(-12, 2)
    ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('Gain re 1 kHz (dB)')
    ax.set_title('Frequency response, no compression', loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'frequency.png'), dpi=150); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.4), sharey=True)
    for i, b in enumerate(res['bursts']):
        t, g = np.array(b['t']), np.array(b['gain'])
        g0 = np.mean(g[(t > 0.05) & (t < 0.095)])
        ax = axs[0] if 'attack' in b['name'] else axs[1]
        ax.plot(t, g - g0, color=colours[[0, 2, 4, 5][i]], lw=1.4, label=b['name'])
    axs[0].set_xlim(0.05, 0.7); axs[1].set_xlim(0.05, 8)
    axs[0].set_ylabel('Gain change (dB)')
    for ax in axs:
        ax.set_xlabel('Time (s)'); ax.legend(frameon=False, fontsize=7.5)
    axs[0].set_title('%+d dBu, %+d dBu burst 0.1 to 0.6 s, %+d dBu' % (LO, HI, LO), loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'attack_release.png'), dpi=150); plt.close(fig)


def main():
    global BASE
    os.makedirs(OUT, exist_ok=True)
    BASE = S.netlist()
    res = dict(op=op_point(), ac=ac_response())
    with Pool(4, initializer=_init, initargs=(BASE,)) as pool:
        res['curves'] = pool.map(ramp, CURVES)
        res['bursts'] = pool.map(burst, BURSTS)
        res['distortion'] = pool.map(distortion, THD_CASES)
    res['timing'] = {b['name']: times(b) for b in res['bursts']}
    plots(res)
    keep = {k: v for k, v in res.items() if k not in ('bursts',)}
    keep['ac'] = {k: v for k, v in res['ac'].items() if k not in ('f', 'gain')}
    json.dump(keep, open(os.path.join(OUT, 'results.json'), 'w'), indent=1)
    print(json.dumps({k: keep[k] for k in ('op', 'ac', 'timing', 'distortion')}, indent=1))


def _init(base):
    global BASE
    BASE = base


if __name__ == '__main__':
    main()
