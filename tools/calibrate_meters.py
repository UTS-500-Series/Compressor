#!/usr/bin/env python3
"""Sets the two meter trimpots, RV8 (level) and RV7 (gain reduction), with an audio interface.

    python3 -m venv ~/meter-venv && source ~/meter-venv/bin/activate
    python3 -m pip install numpy sounddevice
    python3 tools/calibrate_meters.py --list                  # find your interface
    python3 tools/calibrate_meters.py --device "Scarlett" --out 1 --in 1

The script plays a sine from one interface output and measures one input, so it needs a
balanced line out, an input with its gain fixed for the whole session, a loopback cable and
a multimeter with an AC volts range. The loopback can be TRS to TRS into a line input, or TRS
to XLR into the XLR side of a combo input (gain at minimum, phantom power off). A mic input
clips sooner than a line input, so the script checks the headroom and, if it's short, sets
the level meter at a lower LED instead. It walks you through four steps:

  1. Output level. It plays a tone and you read the AC volts across the output's hot and cold
     (tip and ring) with the meter. That ties the interface's dBFS to dBu. If you already know
     your interface's output level at 0 dBFS from its spec sheet, you can type that instead.
  2. Input level. With the loopback cable from that output to that input, it learns the input's
     dBu at 0 dBFS. Don't touch the input gain after this.
  3. Level meter (RV8). Module in circuit, controls neutral. The script holds the module's output
     at the level where one LED should just light and you turn RV8 until it does.
  4. Gain-reduction meter (RV7). It holds the input steady, measures the output with no
     compression, then shows the live gain reduction while you turn THRESHOLD down to the
     target. Then you turn RV7 until the target LED just lights.

Both meters run in dot mode, so "just lights" means the target LED takes over from the one
below it. After each trim the script can sweep the meter so you can check every LED against
the simulated scale.

The targets are the simulated thresholds in kicad/sim/README.md ("The meters"). The level
meter is linear in volts, so setting one LED sets them all. The gain-reduction scale follows
the gain cell's curve, so checking the other LEDs afterwards is worth doing.

The tone defaults to 1 kHz. Cheap multimeters often read AC accurately only up to a few
hundred hertz, so if yours is one, run with --freq 400; the module is flat either way.

Calibration values are saved to meter_cal.json next to this script, so a second run can skip
steps 1 and 2 (as long as the input gain hasn't moved).
"""
import argparse, json, math, os, sys, threading, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CAL_FILE = os.path.join(HERE, 'meter_cal.json')

# Simulated thresholds, kicad/sim/README.md "The meters": (reference, LED colour, lights at).
LEVEL_LEDS = [  # dBu at the module output. LED 1 is the bottom of the level column.
    ('D30', 'green', -1.8), ('D31', 'green', 4.1), ('D32', 'green', 7.5),
    ('D33', 'green', 10.1), ('D34', 'green', 12.0), ('D35', 'orange', 13.6),
    ('D36', 'orange', 14.8), ('D37', 'orange', 16.0), ('D38', 'red', 17.1),
    ('D39', 'red', 18.0),
]
GR_LEDS = [  # dB of gain reduction. LED 1 is the top of the gain-reduction column.
    ('D20', 'orange', 1.8), ('D21', 'orange', 3.1), ('D22', 'orange', 4.7),
    ('D23', 'orange', 6.8), ('D24', 'orange', 9.6), ('D25', 'orange', 12.9),
    ('D26', 'orange', 16.7), ('D27', 'orange', 21.1), ('D28', 'orange', 25.7),
    ('D29', 'orange', 30.4),
]
LEVEL_TRIM_LED = 5   # D34, the top green LED: +12.0 dBu. Lower if the input can't take it.
GR_TRIM_LED = 7      # D26, 7th from the top: 16.7 dB, reachable from a +8 dBu input
HEADROOM = 3.0       # dB kept below the interface input's clip point

DBU_REF = 0.7746     # volts rms at 0 dBu
MAX_DRIVE = -0.5     # never drive the interface output above this, in dBFS


def dbu_to_v(dbu):
    return DBU_REF * 10 ** (dbu / 20)


def v_to_dbu(v):
    return 20 * math.log10(v / DBU_REF)


class Audio:
    """One sine out, one channel in. Levels are dBFS of a sine's peak (0 dBFS = full scale)."""

    def __init__(self, device, out_ch, in_ch, rate, freq, window=0.25):
        import sounddevice as sd
        self.freq, self.rate = freq, rate
        self.out_ch, self.in_ch = out_ch - 1, in_ch - 1
        self.n_window = int(round(round(window * freq) * rate / freq))  # about whole cycles
        self.buf = np.zeros(self.n_window * 2, dtype=np.float32)
        self.lock = threading.Lock()
        self.amp, self.target_amp, self.phase = 0.0, 0.0, 0.0
        info = sd.query_devices(device)
        n_out = max(self.out_ch + 1, 1)
        n_in = info['max_input_channels']   # open every input so a wrong --in can be spotted
        if n_out > info['max_output_channels'] or self.in_ch + 1 > n_in:
            sys.exit(f"{info['name']} has {info['max_output_channels']} outputs and "
                     f"{info['max_input_channels']} inputs; pick channels within those.")
        self.peaks = np.zeros(n_in)
        self.stream = sd.Stream(device=device, samplerate=rate, channels=(n_in, n_out),
                                dtype='float32', callback=self._cb)
        self.stream.start()

    def _cb(self, indata, outdata, frames, t, status):
        step = 2 * math.pi * self.freq / self.rate
        ph = self.phase + step * np.arange(frames)
        # Ramp the level over one block so changes don't click.
        amp = np.linspace(self.amp, self.target_amp, frames, dtype=np.float32)
        outdata[:] = 0
        outdata[:, self.out_ch] = amp * np.sin(ph)
        self.amp = self.target_amp
        self.phase = (self.phase + step * frames) % (2 * math.pi)
        with self.lock:
            self.peaks = np.maximum(self.peaks, np.abs(indata).max(axis=0))
            x = indata[:, self.in_ch]
            n = len(x)
            self.buf = np.concatenate([self.buf[n:], x]) if n < len(self.buf) else x[-len(self.buf):]

    def set_dbfs(self, dbfs):
        self.target_amp = 0.0 if dbfs is None else 10 ** (min(dbfs, MAX_DRIVE) / 20)

    def read_dbfs(self):
        """Level of the tone's fundamental at the input, so hum and hiss don't count."""
        with self.lock:
            x = self.buf[-self.n_window:].astype(np.float64)
        t = np.arange(len(x)) / self.rate
        a = 2 * abs(np.mean(x * np.exp(-2j * math.pi * self.freq * t)))
        return 20 * math.log10(max(a, 1e-9))

    def close(self):
        self.set_dbfs(None)
        time.sleep(0.1)
        self.stream.stop()
        self.stream.close()


def settle(audio, seconds=0.6):
    time.sleep(seconds)
    return audio.read_dbfs()


def average(audio, seconds=2.0):
    vals = []
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(0.25)
        vals.append(audio.read_dbfs())
    return float(np.median(vals))


def ask(prompt, default=None):
    s = input(prompt).strip()
    return s if s else default


def ask_float(prompt):
    while True:
        s = input(prompt).strip().replace(',', '.')
        try:
            return float(s)
        except ValueError:
            print('  Please type a number.')


def wait_enter(prompt='Press Enter to carry on. '):
    input(prompt)


class EnterCollector:
    """Records measure() each time the user presses Enter, in the background. q stops it."""

    def __init__(self, measure, n_max):
        self.measure, self.n_max = measure, n_max
        self.hits, self.stopped, self.ended = [], threading.Event(), threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            s = sys.stdin.readline()
            if self.ended.is_set() or s == '' or s.strip().lower() == 'q':
                self.stopped.set()
                return
            self.hits.append(self.measure())
            if len(self.hits) >= self.n_max:
                self.stopped.set()
                return

    def finish(self):
        """Stop listening. If the thread is still waiting on the keyboard, let it go cleanly."""
        self.ended.set()
        if self.thread.is_alive():
            print('\n  Press Enter to finish.')
            self.thread.join()


def live(audio, show, until):
    """Print a live status line until the user presses Enter. show() returns the text."""
    done = threading.Event()

    def waiter():
        input()
        done.set()

    threading.Thread(target=waiter, daemon=True).start()
    while not done.is_set():
        sys.stdout.write('\r  ' + show() + '      ')
        sys.stdout.flush()
        time.sleep(0.2)
    print()
    return until()


# ---------------------------------------------------------------- steps

def step_output(audio, cal):
    print('\nSTEP 1: interface output level')
    print('  Unplug everything from the output. Set the output (monitor) volume to where you\n'
          '  will leave it for the whole session, ideally full.')
    known = ask('  Do you know the output level at 0 dBFS from the spec sheet? '
                'Type it in dBu, or press Enter to measure: ')
    if known:
        cal['out_dbu_at_0'] = float(known.replace(',', '.'))
        print(f"  Using {cal['out_dbu_at_0']:+.1f} dBu at 0 dBFS.")
        return
    drive = -10.0
    audio.set_dbfs(drive)
    print(f'  Playing {audio.freq:g} Hz at {drive:g} dBFS.')
    print('  Put the meter on AC volts across the output\'s tip and ring (hot and cold).')
    v = ask_float('  What does it read, in volts? ')
    audio.set_dbfs(None)
    cal['out_dbu_at_0'] = v_to_dbu(v) - drive
    print(f"  That's {v_to_dbu(v):+.1f} dBu, so the output is {cal['out_dbu_at_0']:+.1f} dBu "
          'at 0 dBFS.')


def step_input(audio, cal):
    print('\nSTEP 2: interface input level')
    print('  Patch the loopback cable from that output to that input. A line input is best; the\n'
          '  XLR side of a combo input works too. Phantom power OFF, input gain at minimum, and\n'
          '  leave the gain there for the whole session.')
    wait_enter()
    drive = -20.0
    with audio.lock:
        audio.peaks[:] = 0
    audio.set_dbfs(drive)
    got = average(audio)
    audio.set_dbfs(None)
    if got < -80:
        no_signal(audio)
    out_dbu = cal['out_dbu_at_0'] + drive
    cal['in_dbu_at_0'] = out_dbu - got
    print(f'  Sent {out_dbu:+.1f} dBu, read {got:.1f} dBFS, so the input clips at about '
          f"{cal['in_dbu_at_0']:+.1f} dBu.")


def no_signal(audio):
    """Say why the loopback tone didn't arrive, from the peaks seen on every input."""
    peaks = audio.peaks.copy()
    print('  Nothing came back on input', audio.in_ch + 1)
    print('  Peak seen on each input:', '  '.join(
        f'{i + 1}: {20 * math.log10(p) if p > 0 else -math.inf:.0f} dBFS' for i, p in enumerate(peaks)))
    best = int(np.argmax(peaks))
    if not peaks.any():
        sys.exit('  Every input is exact digital silence, which on a Mac means the terminal isn\'t\n'
                 '  allowed to use the microphone. Open System Settings > Privacy & Security >\n'
                 '  Microphone, turn on Terminal (or whichever app you run this from), then quit\n'
                 '  that app completely and run the script again.')
    if best != audio.in_ch and peaks[best] > 10 ** (-60 / 20):
        sys.exit(f'  The tone is arriving on input {best + 1}. Run again with --in {best + 1}.')
    sys.exit('  Check the cable, the channel numbers and the input gain.')


def out_dbu(audio, cal):
    return audio.read_dbfs() + cal['in_dbu_at_0']


def hold_output(audio, cal, target, drive):
    """Nudge the drive until the module's output sits at target dBu. Returns the drive."""
    for _ in range(40):
        err = target - out_dbu(audio, cal)
        if abs(err) < 0.05:
            break
        new = drive + max(-6.0, min(6.0, err))
        if new > MAX_DRIVE:
            return None
        drive = new
        audio.set_dbfs(drive)
        time.sleep(0.5)
    return drive


def connect_module():
    print('  Patch the interface output to the module input and the module output to the\n'
          '  interface input. Set BYPASS off, THRESHOLD fully clockwise (no compression),\n'
          '  MAKEUP at minimum, HPF, KEY and LINK off.')
    wait_enter()


def sweep_level(audio, cal, gain, start, stop):
    """Raise the output slowly; the user presses Enter each time the next LED takes over."""
    print(f'  Sweeping the output from {start:+.0f} to {stop:+.0f} dBu. Press Enter each time a\n'
          '  new LED takes over, starting from the bottom one. Type q and Enter to stop early.')
    keys = EnterCollector(lambda: out_dbu(audio, cal), len(LEVEL_LEDS))
    drive = start - cal['out_dbu_at_0'] - gain   # gain: module input to output, in dB
    level = start
    while level <= stop and not keys.stopped.is_set():
        if drive > MAX_DRIVE:
            print(f'\n  The interface output ran out at about {level:+.1f} dBu.')
            break
        audio.set_dbfs(drive)
        time.sleep(0.35)
        sys.stdout.write(f'\r  now {out_dbu(audio, cal):+6.2f} dBu   ')
        sys.stdout.flush()
        drive += 0.1
        level += 0.1
    keys.finish()
    print()
    return keys.hits


def report(hits, leds, unit, signed=True):
    f = '+' if signed else ''
    print(f"\n  {'LED':<5}{'ref':<6}{'colour':<8}{'target':>9}{'measured':>10}{'diff':>7}")
    for i, (ref, colour, target) in enumerate(leds):
        got = hits[i] if i < len(hits) else None
        if got is None:
            print(f'  {i + 1:<5}{ref:<6}{colour:<8}{target:>{f}8.1f}{"":>10}')
        else:
            print(f'  {i + 1:<5}{ref:<6}{colour:<8}{target:>{f}8.1f}{got:>{f}9.1f}{got - target:>+7.1f}')
    print(f'  ({unit})')


def step_level_meter(audio, cal, led=None):
    print(f'\nSTEP 3: level meter (RV8)')
    room = cal['in_dbu_at_0'] - HEADROOM
    if led is None:
        fits = [i + 1 for i, l in enumerate(LEVEL_LEDS[:LEVEL_TRIM_LED]) if l[2] <= room]
        if not fits:
            sys.exit(f"  The interface input clips at {cal['in_dbu_at_0']:+.1f} dBu, too low to set "
                     'this meter. Use a line input, or turn the input gain down and redo step 2.')
        led = fits[-1]
        if led != LEVEL_TRIM_LED:
            print(f"  The input clips at {cal['in_dbu_at_0']:+.1f} dBu, so setting the meter at LED "
                  f'{led} ({LEVEL_LEDS[led - 1][2]:+.1f} dBu) instead of LED {LEVEL_TRIM_LED}. The '
                  'meter is\n  linear, so this sets the whole scale; it is just a little less precise.')
    ref, colour, target = LEVEL_LEDS[led - 1]
    if target > room:
        sys.exit(f"  The interface input clips at {cal['in_dbu_at_0']:+.1f} dBu, too close to "
                 f'the {target:+.1f} dBu LED {led} needs. Pick a lower --level-led.')
    connect_module()
    drive = target - cal['out_dbu_at_0'] - 3   # start a little low, then close in
    audio.set_dbfs(drive)
    time.sleep(0.8)
    drive = hold_output(audio, cal, target, drive)
    if drive is None:
        audio.set_dbfs(None)
        sys.exit(f'  The interface can\'t reach {target:+.1f} dBu through the module at unity.\n'
                 '  Turn MAKEUP up a little and run this step again.')
    print(f'  The module output is holding at {target:+.1f} dBu.')
    print(f'  Turn RV8 until LED {led} from the bottom of the level column ({ref}, {colour}) just\n'
          '  takes over from the one below it. Go past it, then come back slowly and stop the\n'
          '  moment it lights. Press Enter when it does.')
    live(audio, lambda: f'module out {out_dbu(audio, cal):+6.2f} dBu (holding {target:+.1f})',
         lambda: None)
    if (ask('  Sweep the whole meter to check it? [Y/n] ', 'y') or 'y').lower().startswith('y'):
        top = min(LEVEL_LEDS[-1][2] + 1.0, cal['in_dbu_at_0'] - 1.0)
        if top < LEVEL_LEDS[-1][2]:
            print(f'  The sweep stops at {top:+.1f} dBu to keep the interface input from clipping.')
        gain = target - (drive + cal['out_dbu_at_0'])
        hits = sweep_level(audio, cal, gain, LEVEL_LEDS[0][2] - 3, top)
        report(hits, LEVEL_LEDS, 'dBu at the module output')
    audio.set_dbfs(None)


def step_gr_meter(audio, cal, in_dbu, led=GR_TRIM_LED):
    ref, colour, target = GR_LEDS[led - 1]
    print(f'\nSTEP 4: gain-reduction meter (RV7)')
    print('  Same patching as step 3. THRESHOLD fully clockwise, RATIO fully clockwise\n'
          '  (hardest), ATTACK and RELEASE fast, MAKEUP where it is. Don\'t touch MAKEUP\n'
          '  from here on.')
    wait_enter()
    drive = in_dbu - cal['out_dbu_at_0']
    if drive > MAX_DRIVE:
        drive = MAX_DRIVE
        in_dbu = cal['out_dbu_at_0'] + drive
        print(f'  The interface tops out at {in_dbu:+.1f} dBu, so using that as the input.')
    if in_dbu > cal['in_dbu_at_0'] - HEADROOM:
        # The uncompressed output comes back at about the input level, so keep it below the clip.
        in_dbu = cal['in_dbu_at_0'] - HEADROOM
        drive = in_dbu - cal['out_dbu_at_0']
        print(f'  Using {in_dbu:+.1f} dBu as the input so the uncompressed output doesn\'t clip the\n'
              '  interface input.')
    audio.set_dbfs(drive)
    time.sleep(1.0)
    ref_out = cal['in_dbu_at_0'] + average(audio, 3.0)
    print(f'  Input {in_dbu:+.1f} dBu, output with no compression {ref_out:+.1f} dBu.')

    def gr():
        return ref_out - out_dbu(audio, cal)

    print(f'  Turn THRESHOLD down until the gain reduction reads {target:.1f} dB, then press Enter.\n'
          '  If THRESHOLD fully down can\'t get there, press Ctrl-C and run again with\n'
          f'  --only gr --gr-led {led - 1} (a lower LED).')
    live(audio, lambda: f'gain reduction {gr():5.1f} dB (want {target:.1f})', lambda: None)
    print(f'  Now turn RV7 until LED {led} from the top of the gain-reduction column\n'
          f'  ({ref}) just takes over from the one above it. Go past it, then come back slowly\n'
          '  and stop the moment it lights. Leave THRESHOLD alone. Press Enter when it does.')
    live(audio, lambda: f'gain reduction {gr():5.1f} dB (want {target:.1f})', lambda: None)
    if (ask('  Check the other LEDs? [Y/n] ', 'y') or 'y').lower().startswith('y'):
        print('  Turn THRESHOLD back fully clockwise, then turn it down slowly. Press Enter each\n'
              '  time a new LED takes over, starting from the top one. Type q and Enter to stop.')
        keys = EnterCollector(gr, len(GR_LEDS))
        while not keys.stopped.is_set():
            sys.stdout.write(f'\r  gain reduction {gr():5.1f} dB   ')
            sys.stdout.flush()
            time.sleep(0.2)
        keys.finish()
        print()
        hits = keys.hits
        report(hits, GR_LEDS, 'dB of gain reduction', signed=False)
        print('  The top LEDs may need more input than the interface can give; that\'s fine.')
    audio.set_dbfs(None)


def main():
    p = argparse.ArgumentParser(description='Set the Compressor meter trims RV7 and RV8.')
    p.add_argument('--list', action='store_true', help='list audio devices and exit')
    p.add_argument('--device', help='interface name (part of it is enough) or number')
    p.add_argument('--out', type=int, default=1, help='output channel, from 1 (default 1)')
    p.add_argument('--in', dest='inp', type=int, default=1, help='input channel, from 1 (default 1)')
    p.add_argument('--freq', type=float, default=1000.0, help='tone frequency in Hz (default 1000)')
    p.add_argument('--rate', type=int, default=48000, help='sample rate (default 48000)')
    p.add_argument('--gr-input', type=float, default=8.0,
                   help='module input level for the gain-reduction step, dBu (default +8)')
    p.add_argument('--only', choices=['level', 'gr'], help='run just one meter step')
    p.add_argument('--level-led', type=int, choices=range(1, 11), metavar='1-10',
                   help=f'level LED to set RV8 at (default {LEVEL_TRIM_LED}, lower if the input is short)')
    p.add_argument('--gr-led', type=int, choices=range(1, 11), metavar='1-10', default=GR_TRIM_LED,
                   help=f'gain-reduction LED to set RV7 at (default {GR_TRIM_LED})')
    a = p.parse_args()

    try:
        import sounddevice as sd
    except ImportError:
        sys.exit('This needs numpy and sounddevice. Make a venv first (see the top of this file),\n'
                 'then: python3 -m pip install numpy sounddevice')
    if a.list or a.device is None:
        print(sd.query_devices())
        if a.device is None and not a.list:
            print('\nRun again with --device "<name>" and, if needed, --out and --in.')
        return
    device = int(a.device) if a.device.isdigit() else a.device

    cal = {}
    if os.path.exists(CAL_FILE):
        with open(CAL_FILE) as f:
            saved = json.load(f)
        same = saved.get('device') == a.device and saved.get('out') == a.out and saved.get('in') == a.inp
        if same and (ask(f"Use the saved interface levels (out {saved['out_dbu_at_0']:+.1f}, in "
                          f"{saved['in_dbu_at_0']:+.1f} dBu at 0 dBFS)? [Y/n] ", 'y') or 'y').lower().startswith('y'):
            cal = saved

    audio = Audio(device, a.out, a.inp, a.rate, a.freq)
    try:
        if 'in_dbu_at_0' not in cal:
            step_output(audio, cal)
            step_input(audio, cal)
            cal.update(device=a.device, out=a.out, **{'in': a.inp})
            with open(CAL_FILE, 'w') as f:
                json.dump(cal, f, indent=1)
            print(f'  Saved to {CAL_FILE}.')
        if a.only in (None, 'level'):
            step_level_meter(audio, cal, a.level_led)
        if a.only in (None, 'gr'):
            step_gr_meter(audio, cal, a.gr_input, a.gr_led)
        print('\nDone. Both meters are set.' if a.only is None else '\nDone.')
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        audio.close()


if __name__ == '__main__':
    main()
