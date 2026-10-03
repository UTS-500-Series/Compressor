#!/usr/bin/env python3
"""Simulate the two LED meters (U9 gain reduction, U10 output level) from the kicad/ schematic.

    python3 tools/sim/meters.py             # writes kicad/sim/results/meters.json and .png

Needs the same tools as run_all.py. The LM3914 model (kicad/sim/compressor_models.lib) has
the comparators and current-regulated outputs, so each LED's current is a real result.

1. A short tone sets the level trim RV8 so the top LED lights at +18 dBu out.
2. A slow ramp with no compression finds the output level at which each level LED lights.
3. A slow ramp at full compression finds the gain reduction at which each GR LED lights,
   with RV7 at GR_TRIM (top LED at about 30 dB).
4. A burst shows how both meters move in time.
"""
import json, os, sys
from multiprocessing import Pool
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import simlib as S

OUT = os.path.join(S.ROOT, 'kicad', 'sim', 'results')
GR_LEDS = ['D%d' % (20 + i) for i in range(10)]      # outputs 1-10 of U9
LVL_LEDS = ['D%d' % (30 + i) for i in range(10)]     # outputs 1-10 of U10
VECS = ['v(lvl_meter)', 'v(gr_meter)', 'v(gr_ref)', 'v(p_lvlref)'] + ['@%s[id]' % d.lower() for d in GR_LEDS + LVL_LEDS]
LVL_TOP_DBU = 18.0
# RV7 position (0-1, pin 1 to pin 3). The meter reads 20k * GR_TRIM * (-CTRL-B/10k - GR_REF/18k)
# and the top LED needs 5.05 V; CTRL-B is -7.34 V at 30 dB in run_all.py's full-compression
# curve, so 0.556 puts the top LED at about 30 dB.
GR_TRIM = 0.556
ON = 4e-3                                            # an LED counts as lit above 4 mA
BASE = None


# U10's reference net has '-' in its name, so copy it onto a plain node first
LVLREF = 'E_LVLREF P_LVLREF 0 Net-_U10-REFOUT_ 0 1\nR_LVLREF P_LVLREF 0 1G'


def run(params, analysis, extra=''):
    return S.run(BASE, params, analysis, extra + '\n' + LVLREF, VECS)


def lit(c, leds):
    """Index (1-10) of the LED carrying most current at each sample, 0 when none is lit."""
    i = np.array([c['@%s[id]' % d.lower()] for d in leds])
    k = np.argmax(i, axis=0) + 1
    return np.where(i.max(axis=0) > ON, k, 0), i


def calibrate(_=None):
    """A +10 dBu tone, no compression: how many volts the level meter gets per volt of output."""
    p = dict(LEVEL_DBU=10, THRESHOLD=1, RATIO=1, LVLTRIM=0.5)
    c = run(p, 'tran 10u 0.6 0 20u')
    t = c['t']
    lout = S.dbu(S.rms(t, c['outd'], 0.5, 0.6))
    vm = float(np.mean(c['v(lvl_meter)'][t > 0.5]))
    return dict(out_dbu=float(lout), meter_v=vm, gr_ref=float(c['v(gr_ref)'][-1]),
                lvl_ref=float(c['v(p_lvlref)'][-1]))


L0, L1, RAMP_T = -10.0, 22.0, 6.4


def level_ramp(trim):
    """Output level rising 5 dB/s with no compression; returns each LED's switch-on level."""
    p = dict(THRESHOLD=1, RATIO=1, LVLTRIM=trim, GRTRIM=GR_TRIM, LEVEL_DBU=-300)
    env = '%g * pwr(10, (%g + %g * time) / 20)' % (S.peak(0), L0, (L1 - L0) / RAMP_T)
    c = run(p, 'tran 10u %g 0 20u' % RAMP_T, S.tone(env))
    t = c['t']
    k, i = lit(c, LVL_LEDS)
    rows = []
    for a in np.arange(0.2, RAMP_T - 0.02, 0.02):
        m = (t >= a) & (t <= a + 0.02)
        rows.append([float(S.dbu(S.rms(t, c['outd'], a, a + 0.02))), int(np.round(np.median(k[m]))),
                     float(np.mean(c['v(lvl_meter)'][m])), float(np.max(i[:, m])),
                     float(-1000 * np.mean(c['ipos'][m]))])
    return dict(trim=trim, rows=rows)


GL0, GL1, GRAMP_T = -24.0, 24.0, 8.0


def gr_ramp(_=None):
    """Full compression (threshold and ratio at their ends), input rising 6 dB/s."""
    p = dict(THRESHOLD=0, RATIO=0, ATTACK=0.5, RELEASE=0.5, GRTRIM=GR_TRIM, LEVEL_DBU=-300)
    env = '%g * pwr(10, (%g + %g * time) / 20)' % (S.peak(0), GL0, (GL1 - GL0) / GRAMP_T)
    c = run(p, 'tran 10u %g 0 20u' % GRAMP_T, S.tone(env))
    t = c['t']
    k, i = lit(c, GR_LEDS)
    rows = []
    for a in np.arange(0.2, GRAMP_T - 0.02, 0.02):
        m = (t >= a) & (t <= a + 0.02)
        lin = S.dbu(S.rms(t, c['inp'] - c['inn'], a, a + 0.02))
        lout = S.dbu(S.rms(t, c['outd'], a, a + 0.02))
        rows.append([float(lin), float(lout), int(np.round(np.median(k[m]))),
                     float(np.mean(c['v(gr_meter)'][m])), float(np.mean(c['ctrl'][m]))])
    return dict(trim=GR_TRIM, rows=rows)


def burst(trim):
    """-10 dBu, +20 dBu from 0.1 s to 0.6 s, then -10 dBu, threshold at half travel."""
    p = dict(THRESHOLD=0.5, RATIO=0, ATTACK=0.5, RELEASE=0.5, LVLTRIM=trim, GRTRIM=GR_TRIM,
             LEVEL_DBU=-300)
    env = '(time > 0.1 && time < 0.6 ? %g : %g)' % (S.peak(20), S.peak(-10))
    c = run(p, 'tran 10u 2 0 20u', S.tone(env))
    t = c['t']
    kg, _ = lit(c, GR_LEDS)
    kl, _ = lit(c, LVL_LEDS)
    edges = np.arange(0.0, 2.0 - 0.002, 0.002)
    out = []
    for a in edges:
        m = (t >= a) & (t <= a + 0.002)
        out.append([float(a), int(np.max(kg[m])), int(np.max(kl[m])),
                    float(S.dbu(S.rms(t, c['outd'], a, a + 0.002)))])
    return dict(rows=out)


def thresholds(rows, x_col, k_col):
    """First x at which the lit LED reaches each index 1-10 (None if never)."""
    out = []
    for n in range(1, 11):
        hit = [r[x_col] for r in rows if r[k_col] >= n]
        out.append(round(hit[0], 1) if hit else None)
    return out


def plots(res):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ink, grid = '#222222', '#dddddd'
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': ink, 'axes.labelcolor': ink,
                         'xtick.color': ink, 'ytick.color': ink, 'axes.grid': True, 'grid.color': grid})
    fig, axs = plt.subplots(1, 3, figsize=(10.4, 3.4))
    a = np.array(res['level']['rows'])
    axs[0].step(a[:, 0], a[:, 1], where='post', color='#2f7d4f', lw=1.6)
    axs[0].set_xlabel('Output level (dBu)'); axs[0].set_ylabel('LED lit (1-10)')
    axs[0].set_title('Output level meter (U10)', loc='left')
    axs[0].set_yticks(range(0, 11)); axs[0].set_xlim(L0 + 1, L1)
    g = np.array(res['gr']['rows'])
    gr = g[:, 0] + res['gain0'] - g[:, 1]
    axs[1].step(gr, g[:, 2], where='post', color='#c2571a', lw=1.6)
    axs[1].set_xlabel('Gain reduction (dB)'); axs[1].set_title('Gain reduction meter (U9)', loc='left')
    axs[1].set_yticks(range(0, 11)); axs[1].set_xlim(0, 38)
    b = np.array(res['burst']['rows'])
    axs[2].step(b[:, 0], b[:, 1], where='post', color='#c2571a', lw=1.3, label='GR meter')
    axs[2].step(b[:, 0], b[:, 2], where='post', color='#2f7d4f', lw=1.3, label='level meter')
    axs[2].axvspan(0.1, 0.6, color='#eeeeee', zorder=0)
    axs[2].set_xlabel('Time (s)'); axs[2].set_yticks(range(0, 11))
    axs[2].set_title('+20 dBu burst, 0.1 to 0.6 s', loc='left')
    axs[2].legend(frameon=False, fontsize=7.5)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'meters.png'), dpi=150); plt.close(fig)


def main():
    global BASE
    os.makedirs(OUT, exist_ok=True)
    BASE = S.netlist()
    with Pool(4, initializer=_init, initargs=(BASE,)) as pool:
        gr_job = pool.apply_async(gr_ramp)
        cal = calibrate()
        # the meter voltage scales with the RV8 wiper's distance from AGND (pin 3): 1 - POS
        top_v = cal['lvl_ref']                            # U10's RHI is its own REFOUT
        per_v = cal['meter_v'] / 0.5 / (0.7746 * np.sqrt(2) * 10 ** (cal['out_dbu'] / 20))
        lvl_trim = float(1 - top_v / (per_v * S.peak(LVL_TOP_DBU)))
        lvl_job = pool.apply_async(level_ramp, (lvl_trim,))
        b_job = pool.apply_async(burst, (lvl_trim,))
        res = dict(calibration=cal, lvl_trim=lvl_trim, gr_trim=GR_TRIM,
                   level=lvl_job.get(), gr=gr_job.get(), burst=b_job.get())
    g = np.array(res['gr']['rows'])
    # gain with no compression, from run_all.py's AC result (the ramp starts inside the knee)
    try:
        res['gain0'] = json.load(open(os.path.join(OUT, 'results.json')))['ac']['gain_1k']
    except (OSError, KeyError):
        res['gain0'] = float(np.mean(g[:5, 1] - g[:5, 0]))
    gr = g[:, 0] + res['gain0'] - g[:, 1]
    res['level_on_dbu'] = thresholds(res['level']['rows'], 0, 1)
    res['gr_on_db'] = thresholds([[x, r[2]] for x, r in zip(gr, res['gr']['rows'])], 0, 1)
    a = np.array(res['level']['rows'])
    res['led_mA'] = round(float(np.max(a[:, 3])) * 1000, 1)
    res['supply_mA_pos_no_led'] = round(float(a[0, 4]), 1)
    res['supply_mA_pos_led'] = round(float(a[-1, 4]), 1)
    plots(res)
    json.dump(res, open(os.path.join(OUT, 'meters.json'), 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('lvl_trim', 'gr_trim', 'level_on_dbu', 'gr_on_db', 'led_mA',
                                          'supply_mA_pos_no_led', 'supply_mA_pos_led', 'calibration')},
                     indent=1))


def _init(base):
    global BASE
    BASE = base


if __name__ == '__main__':
    main()
