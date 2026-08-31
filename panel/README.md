# Front panel — OPN-500 / CMP-01

Faceplate mockup and machining data for the compressor module.

![Faceplate](faceplate-mockup.svg)

| File | What it is |
|---|---|
| `faceplate-mockup.svg` | How it looks — anodised finish, knobs, silkscreen. This is the mockup. |
| `faceplate-drawing.svg` | 1:1 technical drawing, dimensioned, for checking before you cut. |
| `faceplate.dxf` | Outline and holes only, for a panel shop or CNC. |
| `make_panel.py` | Generates all three from one definition. |

Everything comes out of `make_panel.py`, so the picture and the machining data cannot drift
apart. Change a control position once and re-run:

```bash
python3 make_panel.py
```

## Panel dimensions

From the API 500 mechanical specification, not guessed:

| | Imperial | Metric |
|---|---|---|
| Width | 1.500″ | 38.10 mm |
| Height | 5.250″ | 133.35 mm |
| Thickness | 0.125″ | 3.18 mm |
| Mounting hole pitch | 4.938″ | 125.43 mm |
| Mounting hole Ø | 0.125″ | 3.18 mm |
| Countersink | 82° to 0.225″ | 82° to 5.72 mm |

Both mounting holes sit on the vertical centreline at x = 19.05 mm, which puts them
3.96 mm from each end.

## Drill schedule

Origin is the **top-left corner** of the panel, x right, y down. All in millimetres.

| Ref | Function | X (mm) | Y (mm) | Hole Ø | Hardware |
|---|---|---|---|---|---|
| `RV3` / `RV4` | THRESHOLD (outer) + RATIO (inner) | 19.05 | 56.00 | 9.5 | dual-concentric pot, 3/8″ bushing |
| `RV5` / `RV6` | ATTACK (outer) + RELEASE (inner) | 19.05 | 79.00 | 9.5 | dual-concentric pot, 3/8″ bushing |
| `RV2` | MAKEUP + pull link | 19.05 | 105.00 | 7.0 | 9 mm pull-switch pot |
| `SW1` | BYPASS | 9.50 | 122.00 | 8.0 | latching pushbutton, illuminated |
| `SW3` | HPF | 6.00 | 105.00 | 6.0 | mini toggle |
| `SW2` | KEY | 32.00 | 105.00 | 6.0 | mini toggle |
| `D201`–`D207` | GR meter, 7 seg | 13.60 | 14.0 to 35.0, 3.5 pitch | 2.2 | 2 mm LED |
| `D301`–`D307` | LVL meter, 7 seg | 24.50 | 14.0 to 35.0, 3.5 pitch | 2.2 | 2 mm LED |
| — | mounting | 19.05 | 3.96 | 3.18 | c'sink 82° to Ø5.72 |
| — | mounting | 19.05 | 129.39 | 3.18 | c'sink 82° to Ø5.72 |

## Layout notes

**Dual-concentric knobs carry the four paired controls.** THRESHOLD over RATIO, ATTACK over
RELEASE — the outer ring is dark and knurled, the inner cap amber, so which one you have hold
of is obvious. This is what buys the room for two meters, a button and two toggles on a
38 mm panel; four separate knobs would eat 40 mm of height on their own.

The trade is cost and sourcing: dual-concentric pots are dearer and harder to find than two
singles, and you generally **cannot get a pull switch on one**, which is why the switch
functions live elsewhere.

**Control map**

| Position | Outer / primary | Inner / secondary |
|---|---|---|
| Upper concentric | THRESHOLD | RATIO |
| Lower concentric | ATTACK | RELEASE |
| Single knob | MAKEUP | pull for LINK |
| Button | BYPASS (latching, lit) | — |
| Toggles | HPF, KEY | — |

**`BYPASS` is a latching pushbutton** legended on its own face. The bottom screw owns the
centreline down there and there is no room for a legend beside it; putting the word on the cap
is what a real panel does anyway. It is illuminated, so bypass state is visible across a room.

**`LINK` is a pull on MAKEUP.** It is set once per stereo pair and then left, which makes it
the right function to hide behind a pull rather than give a switch to.

**Two 7-segment meters.** `GR` fills downward from the top as the compressor clamps; `LVL`
fills upward, green through amber to red. Fourteen 2 mm LEDs on a 3.5 mm pitch, in a recessed
window. Driving them needs a comparator ladder or a display driver — **that circuitry is not
in the schematic yet.**

**Finish and design language.** Bone-coloured panel, flat graphic treatment, sage and
terracotta — closer to a modern plugin UI than to vintage studio hardware, and deliberately
unlike the black anodised modules it will sit between in the rack.

The specifics:

- **Dot scales with numerals.** Each knob has a printed 270° dot scale reading **0–10**,
  numbered at the ends and quarters. Nothing is printed at 12 o'clock: on a panel this tight
  the top of one knob's scale lands in the label of the control above it, every time. MAKEUP
  gets its endpoints only, since the two toggles flank it.
- **The inner shafts are unnumbered.** There is nowhere to print a scale for the inner of a
  concentric pair, so RATIO and RELEASE have none. That is a real cost of concentrics, not an
  oversight.
- **0–10, not units.** Threshold and ratio interact in a feedback compressor, so a calibrated
  dB scale would be a promise the circuit cannot keep. Attack and release *are* predictable
  (2.7–50 ms and 47 ms–2.2 s, both roughly linear on the pot) if you would rather print those.
- **Flat knobs.** Solid charcoal discs with a single bright pointer, no knurling and no
  metallic gradient. Concentric inners are cream with a terracotta pointer, so which ring you
  have hold of is unmistakable.
- **A dark inset for the meters.** LEDs need something to read against, and the contrast block
  gives the panel its structure.
- **Colour carries meaning.** Sage for anything to do with the sidechain and the signal path,
  terracotta for anything to do with gain — the same logic as the schematic documentation.
- **Thin metal bat toggles** on hex bushing nuts for HPF and KEY, not plastic paddles — the
  one place the panel is allowed to look like hardware rather than software.
- **One flourish only**: three concentric arcs tucked into the bottom corner. The DYNAMICS and
  OUTPUT section rules that used to sit between the knobs are gone: the numbered scales need
  that room, and a legend you read beats a divider you do not.

Everything here is ordinary two-colour silkscreen on anodised or powder-coated aluminium. The
arc scales are printed graduations, not illuminated — a panel cannot show a value the way a
plugin can, so the knob pointer against the printed scale does that job.

## Before you have it made

- **Hardware is assumed, not specified.** Hole sizes suit a 9 mm pot bushing, a mini toggle
  and a 3 mm LED bezel. Check them against the parts you actually buy — bushing diameters
  vary between manufacturers and a 0.5 mm error is the difference between a push fit and a
  rattle.
- **Depth clearance is not modelled.** This is a 2D drawing. Confirm that knobs, switch bodies
  and the LED clear the PCB and the neighbouring module before committing.
- **The countersink is on the front face**, so the screw sits flush with the panel.
- Silkscreen colours in the mockup are indicative. Ask your finisher what they can hold.
