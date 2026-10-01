# UTS Mini Mixing Desk — Compressor

A 500-series compressor module for the UTS Mini Mixing Desk. Feedback topology, discrete
current-steering gain cell, balanced in and out, running on the rack's ±16 V.

Built from ordinary parts: **nine BC549 transistors and seven NE5532 op amps**, plus a
pair of LM391x bargraph drivers for the meters. No VCA chip,
no transformers, nothing hard to source.

📖 **Documentation: [uts-500-series.github.io/compressor](https://uts-500-series.github.io/compressor/)** — every section explained, with
interactive schematics you can click through, plus the routed boards and their design files.
The site's source is a separate repository, [UTS-500-Series.github.io](https://github.com/UTS-500-Series/UTS-500-Series.github.io).

---

## Status

| | |
|---|---|
| Schematic | Complete, 7 sheets |
| Components | 166 |
| Nets | 110 |
| ERC | 0 errors, 0 warnings |
| PCB layout | Main board and front board placed and routed, DRC clean, tracks not yet tidied by hand |
| Simulated | No |
| Built | No |

**Every performance figure in the documentation is calculated from the design, not measured.**
The netlist has been verified and ERC is clean, but that only proves the drawing is
self-consistent — not that the circuit behaves as predicted.

## Repository layout

```
kicad_withpcb/compressor_with_pcb/   the main board: flat schematic + routed PCB (KiCad 10)
kicad_withpcb/compressor_front/      the front board behind the panel: schematic + routed PCB
kicad/                               the original seven-sheet schematic (KiCad 9), used by the site
tools/                               design.py (the reference netlist) and the check/build scripts
panel/                               faceplate generator — mockups, a 1:1 drawing and a DXF
```

**The boards are built from `kicad_withpcb/`.** The flat schematic there drives the main
board's PCB, and the front board has its own schematic joined to it by a 30-way ribbon.
`tools/design.py` is the reference netlist. Compare the flat schematic against it after any
wiring edit: KiCad's DRC parity check only compares the PCB with the flat schematic, so it
can't see a wiring mistake in the schematic itself.

The seven-sheet `kicad/` project is the original drawing of the same circuit. It has no PCB,
but the documentation site's interactive schematics are built from it. The site lives in its
own repository, [UTS-500-Series.github.io](https://github.com/UTS-500-Series/UTS-500-Series.github.io),
because it covers the whole desk rather than this module.

## Opening it

The boards need **KiCad 10**:

- `kicad_withpcb/compressor_with_pcb/compressor_with_pcb.kicad_pro`: the main board, the
  500-series card (152.35 × 105 mm) with the edge connector.
- `kicad_withpcb/compressor_front/compressor_front.kicad_pro`: the 35 × 110 mm front board
  with the pots, toggles and meters. Its [README](kicad_withpcb/compressor_front/README.md)
  covers how it mounts, the ribbon, the bracket and what to check before ordering.

Run `sh tools/get_3d_models.sh` once after cloning. It fetches Alps' RK09K pot model, which
isn't kept in git, so the 3D viewer and STEP export show the pots.

The original schematic is `kicad/UTS Mini Mixing Desk - Compressor.kicad_pro` (**KiCad 9**). Its root sheet holds seven
sub-sheets:

| Sheet | What it covers |
|---|---|
| 1 Connector | The 500-series edge connector |
| 2 Input | Balanced receiver and the input pad |
| 3 VCA | The current-steering gain cell and recovery amplifier |
| 4 Output | Makeup gain, output drivers, bypass, aux section |
| 5 Sidechain | Detector: threshold, rectifier, ratio, attack/release |
| 6 Power | Rails, references, bias, grounding, decoupling |
| 7 Meters | Gain-reduction and output-level LED bargraphs |

Only stock KiCad symbol and footprint libraries are used, so there is nothing to install.

## How it works, in one paragraph

A compressor needs a gain it can change electrically, and a way to measure loudness. The gain
cell here keeps a **fixed 3 mA tail current** through a matched BC549 pair and varies gain by
*steering* that current between an output load and the supply rail, rather than by varying the
current itself. That costs four extra transistors and buys a distortion figure that stays flat
at every amount of gain reduction — the simpler tail-current approach distorts worst exactly
when it is compressing hardest. The detector listens to the module's own **output**, making
this a feedback compressor: the ratio emerges from loop gain rather than being dialled in, the
knee comes out soft on its own, and the circuit is forgiving of component tolerance.

The [documentation](../UTS-500-Series.github.io) covers all of this properly, section by section.

## Specifications

| | |
|---|---|
| Format | 500 series, 15-pin EDAC card edge |
| Supply | ±16 V from the rack, ~60 mA per rail typical |
| Input | Balanced, 44 kΩ differential, +4 dBu nominal |
| Output | Balanced, 100 Ω build-out per leg |
| Gain reduction | ~40 dB maximum |
| Attack | 2.7 – 50 ms |
| Release | 47 ms – 2.2 s |
| Controls | Threshold, Ratio, Attack, Release, Makeup |
| Switches | Bypass, sidechain key int/ext, sidechain HPF, stereo link |

## Front panel

[`panel/`](panel/) holds the faceplate: a mockup, a dimensioned 1:1 drawing, and a DXF of the
outline and holes for a panel shop. All three are generated from one definition by
`panel/make_panel.py`, which runs a clearance check on every build.

Panel is the standard 500-series 1.500″ × 5.250″ × 0.125″ with two countersunk mounting holes
125.43 mm apart, badged **OPN-500 / CMP-01**.

The default layout, and the one the front board is built for, is **`toggle`**: five single
Alps RK09K pots (THRESHOLD, RATIO, ATTACK, RELEASE, MAKEUP), four sub-miniature toggles
(HPF and KEY either side of THRESHOLD, LINK and BYPASS either side of RATIO), and two
7-LED meters for gain reduction and output level. That's 25 holes, and `make_panel.py`
takes their positions from the front board. The toggles are Jaycar ST0300 (SPDT) for HPF,
KEY and LINK and ST0310 (DPDT) for BYPASS, in 5.2 mm holes.

The toggle bushing is only 4.06 mm long, which leaves under 1 mm of thread for the nut
through a 3.18 mm panel. Either thin the panel to about 2 mm around those four holes or use
a thinner panel.

`make_panel.py` also keeps a `pull` layout (every switch on a pull-switch pot) and a
`concentric` layout (dual-concentric knobs and a lit BYPASS button), plus a `bone` finish
alongside the default dark anodised one. The boards are only drawn for `toggle`. See
[`panel/README.md`](panel/README.md).

## Bill of materials

`tools/bom_order.py` writes an order list from `design.py`. It doesn't yet know about the
layout-stage hardware: the Jaycar toggles (it still lists generic switches), the 30-way
ribbon with its two headers and IDC sockets, the panel bracket and M3 screws, and the DIP-8
sockets for U1–U7. The LM3914/LM3915 meter drivers are soldered straight in, because
sockets would overlap the meter LEDs.

The circuit itself is 166 components across 58 distinct line items: 73 resistors, 39 capacitors, 15 LEDs,
9 transistors, 8 potentiometers, 8 diodes, 7 op amps, 4 switches, 2 display drivers,
1 connector.

Four things are not substitutable:

- **Q1/Q2 must be a matched pair, and Q6–Q9 a matched quad**, all glued together so they stay
  at the same temperature. The steering balance is set by base-emitter voltages differing by
  tens of millivolts, and those drift ~2 mV per °C.
- **R1–R4 and R21–R24 want 0.1%.** R1–R4 set input common-mode rejection; R21–R24 set how well
  the recovery amp rejects the gain cell's step, which is audible as thump on fast attacks.
- **R61 (1k33) and R62 (23k2) want 0.1%.** They set the gain cell's resting point.
- **C15 must be film.** An electrolytic's leakage is in the same league as the release current
  at long settings and will shorten your slowest release.

One recommended deviation: fit a **TL072 or OPA2134 for U4** instead of an NE5532. Its inputs
sit on the timing capacitor, and the NE5532's ~200 nA bias current can leave the compressor
holding about a decibel of gain reduction at idle. Pin compatible, nothing else changes.

## Documentation site

The site is a **separate repository**, checked out beside this one as `../UTS-500-Series.github.io`. It covers
every module in the desk — compressor, preamp and equaliser — so it does not belong to any
one of them. It also owns its own GitHub Pages workflow.

The compressor's pages are interactive: pan and zoom the real schematic, click any part for
its value, footprint and nets, click a net to highlight everything on it, or switch to a
graph view of the netlist.

The site commits its generated data, so it builds and publishes without this repository
present. It only needs this one checked out when the schematic changes — see below.

## Tooling

Everything needed to check and rebuild the project lives in [`tools/`](tools/) — standard
library only, no packages to install. KiCad's paths are found automatically; override with
`KICAD_CLI` and `KICAD_SYMBOL_DIR` if yours are somewhere unusual.

```bash
python3 tools/verify_netlist.py      # check the schematic against design.py
```

`tools/gen_project.py` and `tools/route_sch.py` **regenerate the schematic from scratch and
will overwrite hand-drawn layout.** They built the first version; the sheets have been laid out
by hand since. See [`tools/README.md`](tools/README.md) before running either.

## How the schematic is verified

`tools/design.py` holds the netlist as data and is treated as the source of truth.
`tools/verify_netlist.py` exports the netlist from the schematic with `kicad-cli` and diffs it
against that definition **net by net and pin by pin**.

That is what catches the failure mode ERC cannot see: a wire dragged so its endpoint lands on a
neighbouring node shorts two signal nets together, and ERC reports nothing, because every pin
is still connected to *something*. Two such shorts were caught and fixed this way during layout
cleanup. Worth running after any significant edit — it takes a second and prints the exact nets
and pins involved when something is wrong.

## Regenerating the documentation

After changing a sheet, from the **docs** repository beside this one:

```bash
# 1. re-export the sheet images
kicad-cli sch export svg --no-background-color --exclude-drawing-sheet -o /tmp/svg \
  "kicad/UTS Mini Mixing Desk - Compressor.kicad_sch"
#    copy the seven sheets into ../UTS-500-Series.github.io/site/compressor/img/ as connector.svg, input.svg,
#    vca.svg, output.svg, sidechain.svg, power.svg, meters.svg

cd ../UTS-500-Series.github.io
python3 build/_data.py --module compressor   # hotspots + netlist graph, read from kicad/
python3 build/build_site.py                  # every page, every module
```

Both scripts import from `tools/`, so a fresh clone has everything it needs.

## Known gaps

- **The tracks came from an autorouter and want a hand tidy before ordering:** route IN± and
  OUT± as pairs, pull the long bottom-layer runs off the ground pour, and tighten the timing
  node around C15 and U4.
- **Measure an ST0310 before ordering boards.** Jaycar publishes no drawing for it, so the DPDT
  footprint assumes 2.54 mm lugs with the rows 4.7 mm apart.
- **Check the mechanics in a real rack:** the pots' height against the front board's 8.7 mm
  setback (a nut behind the panel may make up the difference), the panel thickness at the
  toggles, and the ribbon length (about 150 mm is an estimate).
- **The BOM script lags the board** (see above).
- Pin 11 is used as an auxiliary input, which the API 500 specification assigns to a gain-trim
  node. The aux section (U5 and its resistors) is a separable block; omit it and the module is
  fully standards-compliant.
- Nothing has been SPICE'd. Loop stability at fast attack with high ratio is unverified.

## Licence

Not yet chosen — add one before sharing publicly.
