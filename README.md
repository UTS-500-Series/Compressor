# UTS Mini Mixing Desk — Compressor

A 500-series compressor module for the UTS Mini Mixing Desk. Feedback topology, discrete
current-steering gain cell, balanced in and out, running on the rack's ±16 V.

Built from ordinary parts: **nine BC549 transistors and seven NE5532 op amps**, plus a
pair of LM391x bargraph drivers for the meters. No VCA chip,
no transformers, nothing hard to source.

📖 **Documentation: [`docs/`](docs/)** — every section explained, with
interactive schematics you can click through. Once GitHub Pages is enabled, replace this
line with the published URL.

---

## Status

| | |
|---|---|
| Schematic | Complete, 7 sheets |
| Components | 166 |
| Nets | 110 |
| ERC | 0 errors, 0 warnings |
| PCB layout | Not started |
| Simulated | No |
| Built | No |

**Every performance figure in the documentation is calculated from the design, not measured.**
The netlist has been verified and ERC is clean, but that only proves the drawing is
self-consistent — not that the circuit behaves as predicted.

## Repository layout

```
kicad/     the KiCad 9 project — .kicad_pro plus one .kicad_sch per sheet
tools/     design.py (the authoritative netlist) and the generate/route/verify scripts
panel/     faceplate generator — mockups, a 1:1 drawing and a DXF, from one definition
docs/      the documentation site, published to GitHub Pages
```

Everything in `kicad/`, `panel/` and `docs/` is **generated from or checked against**
`tools/design.py`. That is the one file to treat as source; the rest can be rebuilt.

## Opening it

Open `kicad/UTS Mini Mixing Desk - Compressor.kicad_pro` in **KiCad 9**. The root sheet holds seven
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

The [documentation](docs/) covers all of this properly, section by section.

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

The default layout is five separate knobs with every switch function on a **pull-switch pot** —
THRESHOLD pulls for the sidechain HPF, RATIO for key int/ext, MAKEUP for bypass — plus two
7-segment LED meters for gain reduction and output level. LINK is an internal jumper. No
toggles, no button, 21 holes.

`make_panel.py` also carries a `toggle` layout (the same five knobs, but with HPF and KEY
flanking THRESHOLD and LINK and BYPASS flanking RATIO — 25 holes, every function one positive
movement) and a `concentric` layout (dual-concentric knobs, a lit BYPASS button, HPF/KEY
toggles), plus a `bone` finish alongside the default dark anodised one. Six combinations, all
from one definition — see [`panel/README.md`](panel/README.md).

## Bill of materials

166 components across 58 distinct line items: 73 resistors, 39 capacitors, 15 LEDs,
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

`docs/` is a static site with a page per section. The schematics in it are
interactive — pan and zoom, click any part for its value, footprint and nets, click a net to
highlight everything on it, or switch to a graph view of the netlist. There is a search box
for jumping to a designator or net name.

Publishing to GitHub Pages:

1. **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main`. `.github/workflows/pages.yml` publishes `docs/`.

The folder is called `docs/` because that is one of the two sources GitHub's simple Pages
UI offers, so **Source: Deploy from a branch → main → /docs** works too, and the workflow
can be deleted if you prefer that. It is kept because it redeploys on every push with no
further setup.

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

After changing a sheet:

```bash
# 1. re-export the sheet images
kicad-cli sch export svg --no-background-color -o /tmp/svg \
  "kicad/UTS Mini Mixing Desk - Compressor.kicad_sch"
#    copy the seven sheets into docs/img/ as connector.svg, input.svg, vca.svg,
#    output.svg, sidechain.svg, power.svg, meters.svg

cd docs
python3 _data.py     # component hotspots + netlist graph, read from the .kicad_sch files
python3 _build.py    # the ten HTML pages
```

Both scripts import from `tools/`, so a fresh clone has everything it needs.

## Known gaps

- No PCB layout has been attempted. `J1` is a generic `Conn_01x15`, so a real card-edge
  footprint is still needed.
- The panel is a 2D drawing only — depth clearance between knobs and the PCB has not been
  checked, and panel hardware is assumed rather than specified.
- **The panel needs parts and circuitry the schematic does not have yet:** two 7-segment LED
  meters (14 LEDs) need a comparator ladder or display driver, and the default panel layout
  assumes pull-switch pots rather than the discrete `SW1`–`SW4` in `design.py` (the
  `concentric` layout additionally needs dual-concentric pots and a latching pushbutton).
- The switches have no footprints assigned — pick parts to suit the panel.
- Pin 11 is used as an auxiliary input, which the API 500 specification assigns to a gain-trim
  node. The aux section (U5 and its resistors) is a separable block; omit it and the module is
  fully standards-compliant.
- Nothing has been SPICE'd. Loop stability at fast attack with high ratio is unverified.

## Licence

Not yet chosen — add one before sharing publicly.
