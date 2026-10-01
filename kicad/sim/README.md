# Simulating the compressor

The seven-sheet schematic in `kicad/` simulates in KiCad's own simulator (ngspice). Every part
has a SPICE model, and the root sheet carries a small test bench: the rack's ±16 V, a balanced
1 kHz source, a 20 k balanced load, and one line of knob settings.

## Running it in KiCad

1. Open `kicad/UTS Mini Mixing Desk - Compressor.kicad_pro` in KiCad 10 (the sheets are saved in its format).
2. **Inspect → Simulator**, then **New Analysis Tab** and pick **Transient**. Something like
   step `10u`, stop `0.6` and max step `20u` works (in a `.tran` line: `.tran 10u 0.6 0 20u`).
   For the frequency response, pick **AC** instead, decade sweep from 10 Hz to 100 kHz.
3. Run it, then probe nets in the schematic. The useful ones:

| Net | What it shows |
|---|---|
| `OUT_DIFF` | The balanced output, OUT+ minus OUT- (a test-bench probe) |
| `OUT-A` | The makeup amp's output, the hot leg before the build-out resistor |
| `CTRL-B` | The control voltage: 0 V at rest, going negative as it compresses |
| `STB`, `STA` | The steering pair. STB minus STA is what sets the gain |
| `TIMING` | The attack/release capacitor C15 |
| `SIG-VCA` | After the gain cell and recovery amp |

The AC source is 1 V differential, so an AC run reads gain directly.

## Changing the settings

The knobs are `.param` lines in the text block at the bottom of the root sheet. Edit the text
and run again.

| Param | Part | 0 means | 1 means |
|---|---|---|---|
| `LEVEL_DBU` | source | input level in dBu, differential | |
| `FREQ` | source | tone frequency in Hz | |
| `THRESHOLD` | RV3 | 0 Ω: detector gain 5, lowest threshold | 1 MΩ: highest threshold |
| `RATIO` | RV4 | wiper at the rectifier: hardest | wiper at ground: no compression |
| `ATTACK` | RV5 | 0 Ω: fastest | 4k7: slowest |
| `RELEASE` | RV6 | 0 Ω: fastest | 220 k: slowest |
| `MAKEUP` | RV2 | 0 dB | +21 dB |
| `TRIM` | RV1 | unity trim | |
| `GRTRIM`, `LVLTRIM` | RV7, RV8 | meter trims | |
| `BYPASS`, `KEY` | SW1, SW2 | in, internal key | bypassed, external key |
| `HPF_DEFEAT`, `LINK` | SW3, SW4 | sidechain HPF in, link open | HPF shorted out, link closed |

Pot positions are where the wiper sits between pin 1 (0) and pin 3 (1), so they are not
necessarily the knob's clockwise direction. See the note on pot direction in the results.

## The models

All in `compressor_models.lib`, which says where each one comes from:

- **BC549C**: Philips' model.
- **1N4148, 1N4004**: vendor models. **BZX79C5V1** and the **LEDs**: generic models.
- **NE5532**: a behavioural model written for this design. TI's 1989 macromodel was tried
  first, but ngspice aborts on its output current limiter when the meter's peak detector
  swings. The behavioural one has the real part's gain, bandwidth, slew rate, input bias,
  swing and current limit, but no noise and no distortion of its own until it clips.
- **LM3914N** (both meter drivers): a stand-in for the reference and input only. The LEDs
  never light in simulation.
- **Pots and switches**: ideal, set by the parameters above.

`tools/add_sim_models.py` writes the `Sim.*` fields onto the sheets. Run it again if the
sheets are regenerated, or if you add a part that needs a model. The `.options rshunt=1e9`
line on the bench matters: without it ngspice stalls once the compressor is working hard.

## Running it without the KiCad GUI

`tools/sim/` has the scripts that produced the results below. They export the netlist with
`kicad-cli sch export netlist --format spice` and run ngspice in batch mode:

```
python3 tools/sim/run_all.py      # needs kicad-cli, ngspice, numpy, matplotlib
```

## Results

Run on 1 October 2026 with kicad-cli 10.0.6 and ngspice 42, from the sheets as they are on
`main`. Levels are balanced (differential) dBu, at 1 kHz, makeup at 0, attack and release
at half travel unless it says otherwise. `results/results.json` has every number.

![Compression curves](results/compression.png)

**It works as a compressor.** The knee is soft, and with RATIO at the hard end the slope
above the knee is about 5:1. The most reduction it reaches is about 22 dB, at +22 dBu in;
above that the input stage clips before the detector can ask for more. Distortion stays low
while it compresses, which is the whole point of the steering cell:

| Condition | Out | Gain reduction | THD |
|---|---|---|---|
| +4 dBu in, not compressing | +9.8 dBu | 0 | 0.027% |
| +8 dBu in, threshold lowest | +3.3 dBu | 10.5 dB | 0.021% |
| +16 dBu in, threshold lowest | +4.9 dBu | 16.9 dB | 0.033% |
| +16 / +20 / +22 dBu in, not compressing | | 0 | 0.12% / 0.24% / 0.41% |
| +24 dBu in, not compressing | | 0 | 7.2%, the input stage clipping |

The op amp model has no distortion of its own below clipping, so these figures are the
gain cell's. Real NE5532s add a little.

### Where it differs from the documentation

1. **The module has 6 dB of gain, balanced in to balanced out.** +4 dBu in gives +9.8 dBu
   out. Each output leg carries the full signal, so the balanced output is twice the input,
   and RV1 only covers +4.9 to +6.8 dB, so it can't trim to unity. Bypass is 0 dB, so the
   level jumps 6 dB when you press BYPASS. Halving the recovery amp's gain (R23 and R24 22k
   to 11k) and doubling the threshold amp's (R36 100k to 200k) fixes both: the simulated trim
   range becomes +0.8 to -1.1 dB, and the detector sees the same level as now, so the
   thresholds don't move.
2. **The bass rolls off early: -3 dB at 22 Hz (-3.4 dB at 20 Hz).** C9 and C10 (2u2) feed
   the recovery amp's 3k3 inputs, which is a 22 Hz high-pass. 22 µF electrolytics there
   (positive towards Q4/Q5) give -0.1 dB at 20 Hz in the same simulation.
3. **The threshold runs from about -9 dBu to above +20 dBu, not -20 to +14 dBu** (taking
   the threshold as where 1 dB of reduction starts). Most of it happens in the first quarter of RV3's travel: 0 to 0.25
   covers -9 to +14 dBu. A smaller RV3 or a log taper would spread it out.
4. **At rest STB sits 94 mV above STA, not 150 mV.** R68 and R69 load VREF5 down to 3.60 V
   (the power page says 5.49 V); STA is 3.41 V and STB 3.50 V. The cell is still within
   0.3 dB of full gain, so this only changes the bring-up numbers.
5. **CTRL-B reaches about -4.5 V at the most reduction, not -10 V.** The gain-reduction
   meter's top segments may need RV7 set with that in mind.
6. **Attack and release run faster than the RC values suggest**, because the detector
   overdrives C15. Measured as the time to 63% of the change in gain, with a +16 dB burst at
   the lowest threshold:

| Setting | Attack | Release |
|---|---|---|
| ATTACK fastest / slowest | 1 ms / 14 ms | |
| RELEASE fastest / slowest | | 20 ms / 0.44 s |

   The release pot also changes how much it compresses: at the fastest setting RV6 and R47
   load the detector, so +22 dBu gets 17 dB of reduction instead of 22 dB.

7. **Supply current is about 72 mA on +16 V and 61 mA on -16 V** at rest (README says about
   60 mA). That includes 6 mA for each LM3914 but not the lit meter LEDs, which add several
   mA each.

![Attack and release](results/attack_release.png)

![Frequency response](results/frequency.png)

### One thing to check by hand: pot direction

On the usual convention, pin 3 is the clockwise end of a pot. If that holds for the RK09K,
THRESHOLD and RATIO turn the opposite way to the panel guide: clockwise would raise the
threshold and soften the ratio, where the guide says clockwise means more compression.
On the same convention MAKEUP, ATTACK and RELEASE turn the expected way (clockwise adds gain
or slows the time). Check Alps' drawing before the panel legends are printed.
