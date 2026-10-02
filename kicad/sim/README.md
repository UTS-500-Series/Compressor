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
| `THRESHOLD` | RV3 | 0 Ω: lowest threshold, about −20 dBu | 100 kΩ (audio taper): about +20 dBu |
| `RATIO` | RV4 | wiper at the rectifier: hardest | wiper at ground: no compression |
| `ATTACK` | RV5 | 0 Ω: fastest | 4k7: slowest |
| `RELEASE` | RV6 | 0 Ω: fastest | 500 k: slowest |
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
- **Pots and switches**: ideal, set by the parameters above. A pot whose value ends in A
  (RV3, 100kA) has an audio taper: 10% of its resistance at half travel.

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

Run on 2 October 2026 with kicad-cli 10.0.6 and ngspice 42, from the sheets as they are on this
branch. Levels are balanced (differential) dBu, at 1 kHz, makeup at 0, attack and release at
half travel unless it says otherwise. `results/results.json` has every number.

![Compression curves](results/compression.png)

**It works as a compressor, and now meets most of its design targets.** The first simulation
(1 October, values as they were on `main`) found the module had 6 dB of gain, an early bass
roll-off, a threshold that did all its work in the first quarter of RV3, and attack and release
much faster than the RC values suggest. Thirteen part values changed to fix that; no connections
moved, so the board layouts keep their routing.

| Part | Was | Now | Why |
|---|---|---|---|
| R21, R22 | 3k3 | 6k8 | Halves the recovery amp's gain: the module is unity and BYPASS matches |
| C9, C10 | 2u2 | 4u7 | With the larger R21/R22, the bass corner drops from 22 Hz to about 5 Hz |
| R36 | 100k | 82k | With R35 and RV3, sets the detector gain range |
| RV3 | 1M linear | 100kA | Spreads the threshold evenly over the knob; RK09K stops at 100k |
| R35 | 20k | 1k | Sets the lowest threshold at −20 dBu |
| R38, C14 | 10k, 220n | 1k, 2u2 | Holds the sidechain high-pass between 80 and 160 Hz over the threshold knob; with R38 at 10k the small R35 pushed it to 400 Hz at low thresholds |
| R60 | 47k | 24k | Restores the 150 mV resting steer (VREF5 now 5.77 V, close to the 5.49 V on the power page) |
| C22 | 47u | 4u7 | Stops the steering overshooting by up to 20 dB on a fast attack (below) |
| R47 | 4k7 | 15k | Fastest release near 47 ms; the release pot loads the detector less |
| RV6 | 220k | 500k | Slowest release towards 2.2 s. RK09K stops at 100k (0.4 s), so this one is a different 9 mm pot |

| | Before | Now | Target |
|---|---|---|---|
| Gain at 1 kHz, balanced in to out | +5.8 dB | −0.1 dB | 0 dB |
| RV1 trim range | +4.9 to +6.8 dB | +0.9 to −1.0 dB | covers 0 dB |
| −3 dB points | 22 Hz, 60 kHz | 5.6 Hz, 60 kHz | 20 Hz to 20 kHz |
| Threshold (1 dB of reduction) | −9 to above +20 dBu | −20 to +20 dBu | −20 to +14 dBu |
| Threshold at RV3 0, ¼, ½, ¾, 1 | −9, +14, above +20 by ½ | −20, −10, 0, +10, +20 | an even spread |
| Most reduction (+22 dBu in) | 22 dB | 35 dB | about 40 dB |
| Attack, fastest to slowest | 1 to 14 ms | 2 to 34 ms | 2.7 to 50 ms |
| Release, fastest to slowest | 20 ms to 0.44 s | 50 ms to 1.8 s | 47 ms to 2.2 s |
| Resting steer, VREF5 | 94 mV, 3.60 V | 151 mV, 5.77 V | 150 mV, 5.49 V |
| CTRL-B at most reduction | −4.5 V | −8.0 V | −10 V |
| Supply at rest, +16 / −16 V | 72 / 61 mA | 72 / 61 mA | about 60 mA |

Distortion stays low while it compresses, which is the whole point of the steering cell:

| Condition | Out | Gain reduction | THD |
|---|---|---|---|
| +4 dBu in, not compressing | +3.9 dBu | 0 | 0.008% |
| +4 dBu in, makeup at full | +24.7 dBu | 0 | 0.010% |
| +8 dBu in, threshold at ¼ | −5.7 dBu | 13.6 dB | 0.020% |
| +8 dBu in, threshold lowest | −15.0 dBu | 22.9 dB | 0.032% |
| +16 dBu in, threshold lowest | −14.2 dBu | 30.1 dB | 0.038% |
| +16 / +20 / +22 dBu in, not compressing | | 0 | 0.033% / 0.057% / 0.078% |
| +24 dBu in, not compressing | | 0 | 6.1%, the input stage clipping |

The op amp model has no distortion of its own below clipping, so these figures are the gain
cell's. Real NE5532s add a little.

### What still misses

1. **Most gain reduction is 35 dB, not 40 dB.** The input stage clips at about +23 dBu on
   ±16 V, so 40 dB would need a threshold near −30 dBu. Better to restate the target.
2. **The slowest attack is 34 ms and the slowest release 1.8 s**, against 50 ms and 2.2 s.
   The next stock pot values overshoot the other way (RV6 at 1M simulated 3.4 s), so these
   were left as the closest fit.
3. **Times depend on level.** They are the time to 63% of the change in gain for a −10 to
   +20 dBu burst at half threshold (about 0 dBu), so about 20 dB over. Harder hits are faster.
4. **The ratio rises with level.** With RATIO at the hard end the knee is soft: about 4:1 just
   above the threshold, steeper (6:1 to 11:1) by 20 dB over.
5. **CTRL-B reaches −8.0 V at the most reduction, not −10 V.** Set the gain-reduction meter's
   RV7 against a measured CTRL-B.
6. **Supply current is about 72 / 61 mA at rest** (README says about 60 mA). That includes
   6 mA for each LM3914 but not the lit meter LEDs, which add several mA each.
7. **C22 (fixed).** C22 filters the reference for STA only. When CTRL-B pulled the shared
   reference node down, STA lagged STB by about 60 ms, so the gain kept falling after the
   control voltage had settled: up to 20 dB of overshoot on a fast attack. At 4u7 it is about
   1 dB.

![Attack and release](results/attack_release.png)

![Frequency response](results/frequency.png)

### To check by hand before ordering

- **Pot direction.** On the usual convention pin 3 is the clockwise end of a pot. If that holds
  for the RK09K, THRESHOLD and RATIO turn the opposite way to the panel guide: clockwise would
  raise the threshold and soften the ratio. Swapping their outer pins fixes it, and RV3 then
  needs a reverse-log (C) taper. MAKEUP, ATTACK and RELEASE turn the expected way.
- **Parts.** RV6 needs a 500k 9 mm pot with an M7 bushing; Alpha's 9 mm vertical pots come in
  B500K with an M7 × 0.75 bushing, but check their pins against the RK09K footprint. Bourns'
  PTV09A-6 has an M9 bushing, which would need a bigger panel hole. C9/C10 (4.7 µF), C14 (2.2 µF)
  and C15 (10 µF) are film parts drawn on a 7 × 2.5 mm, 5 mm-pitch outline; real ones at those
  values are thicker, so check the space around them.
