# Front panel — OPN-500 / CMP-01

Faceplate mockup and machining data for the compressor module.

![Faceplate](faceplate-mockup.svg)

| File | What it is |
|---|---|
| `faceplate-mockup.svg` | How it looks — whichever finish you built last. |
| `faceplate-mockup-bone.svg` | The other finish, written every run so you can compare. |
| `faceplate-drawing.svg` | 1:1 technical drawing, dimensioned, for checking before you cut. |
| `faceplate.dxf` | Outline and holes only, for a panel shop or CNC. |
| `make_panel.py` | Generates all of it from one definition. |

Everything comes out of `make_panel.py`, so the picture and the machining data cannot drift
apart. Change a control position once and re-run:

```bash
python3 make_panel.py                          # toggle layout, anodised (default)
python3 make_panel.py --layout pull            # five knobs, every switch a pull
python3 make_panel.py --layout concentric      # concentric knobs, button, toggles
python3 make_panel.py --style bone             # light flat-graphic finish
python3 make_panel.py --layout toggle --style bone
```

## Layouts

The layout changes **what hardware is on the panel**, so the hole pattern, the drawing and the
DXF all change with it.

**`pull`** — five separate knobs. Every switch function is a pull on a pot, so
there are no toggles and no button at all: THRESHOLD pulls for the sidechain HPF, RATIO for
key int/ext, MAKEUP for bypass. LINK is an internal jumper. **21 holes.** The simplest panel
to build and the cheapest to populate, at the cost of a slow, uncertain bypass action.

*A note on the shared row:* ATTACK and RELEASE sit side by side on every layout, so they get a
smaller legend and no printed numerals — two full scales would print their endpoints on top of
each other in the gap between the knobs.

**`toggle`** *(default, and the one the front board is built for)* — the same five knobs, but every switch gets its own toggle rather than hiding on
a pull. They flank the two knobs they belong to: HPF and KEY either side of THRESHOLD, LINK and
BYPASS either side of RATIO. **25 holes.** Four more holes and four more parts than `pull`, and
in exchange every function is one positive movement — nothing is hidden, and bypass is instant.
The most parts of the three layouts, and the easiest to use.

**`concentric`** — two dual-concentric knobs (THRESHOLD/RATIO, ATTACK/RELEASE) free the space
for a latching illuminated BYPASS button and HPF / KEY toggles; LINK moves to the pull on
MAKEUP. **22 holes.** Better ergonomics, but concentric pots are dearer, harder to source, and
their inner shafts cannot carry a printed scale.

## Finishes

**`anodised`** *(default)* — dark panel, knurled knobs, teal accents. Reads as studio hardware.
The recessed meter window and the DYNAMICS / OUTPUT section rules appear on the concentric
layout only; the pull layout is plainer because it has no room for them.

**`bone`** — light panel, flat graphic treatment, printed dot scales with 0–10 numerals, thin
metal bat toggles, sage and terracotta. Closer to a plugin UI than a rack unit.

Every run writes the chosen combination as `faceplate-mockup.svg` and the other finish as
`faceplate-mockup-<name>.svg`, so comparing costs nothing.

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

For the `toggle` layout, which is what the front board (`kicad_withpcb/compressor_front`)
carries. That board is the master: these positions are copied from it, so change the board
first and then the numbers in `make_panel.py`.

Origin is the **top-left corner** of the panel, x right, y down. All in millimetres.

| Ref | Function | X (mm) | Y (mm) | Hole Ø | Hardware |
|---|---|---|---|---|---|
| `RV3` | THRESHOLD | 19.05 | 52.00 | 7.2 | 9 mm pot (Alps RK09K), M7 bushing |
| `RV4` | RATIO | 19.05 | 72.50 | 7.2 | 9 mm pot |
| `RV5` | ATTACK | 10.00 | 91.00 | 7.2 | 9 mm pot |
| `RV6` | RELEASE | 25.10 | 91.00 | 7.2 | 9 mm pot |
| `RV2` | MAKEUP | 19.05 | 111.00 | 7.2 | 9 mm pot |
| `SW3` | HPF | 6.90 | 52.00 | 5.2 | sub-miniature toggle, SPDT (Jaycar ST0300) |
| `SW2` | KEY | 31.20 | 52.00 | 5.2 | sub-miniature toggle, SPDT (Jaycar ST0300) |
| `SW4` | LINK | 6.90 | 72.50 | 5.2 | sub-miniature toggle, SPDT (Jaycar ST0300) |
| `SW1` | BYPASS | 31.20 | 72.50 | 5.2 | sub-miniature toggle, DPDT (Jaycar ST0310) |
| `D20`–`D26` | GR meter, 7 seg | 14.10 | 14.0 to 35.0, 3.5 pitch | 2.2 | 2 mm flat-top LED |
| `D30`–`D36` | LVL meter, 7 seg | 24.00 | 14.0 to 35.0, 3.5 pitch | 2.2 | 2 mm flat-top LED |
| — | mounting | 19.05 | 3.96 | 3.18 | c'sink 82° to Ø5.72 |
| — | mounting | 19.05 | 129.39 | 3.18 | c'sink 82° to Ø5.72 |

The toggles' 10-48 bushing is only 4.06 mm long, which leaves under 1 mm of thread for the
nut through a 3.18 mm panel. Either thin the panel to about 2 mm around those four holes
(a counterbore from the back), or use a 1.6 to 2 mm panel.

ATTACK and RELEASE sit 1.5 mm left of symmetric so the ribbon header on the back of the
front board clears the RELEASE pot. The meter columns are 9.9 mm apart rather than 10.9 so
the LM3914 and LM3915 fit either side of them.

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

**On keeping every round.** The panel went through several iterations and only the most recent
reached git, so two earlier versions had to be rebuilt from scratch to get them back. Hence
`--layout` and `--style`: four combinations now regenerate from one definition and none can be
lost by choosing another. Commit after a round you like.

## Before you have it made

- **Hardware is assumed, not specified.** Hole sizes suit a 9 mm pot bushing, a mini toggle
  and a 3 mm LED bezel. Check them against the parts you actually buy — bushing diameters
  vary between manufacturers and a 0.5 mm error is the difference between a push fit and a
  rattle.
- **Depth clearance is not modelled.** This is a 2D drawing. Confirm that knobs, switch bodies
  and the LED clear the PCB and the neighbouring module before committing.
- **The countersink is on the front face**, so the screw sits flush with the panel.
- Silkscreen colours in the mockup are indicative. Ask your finisher what they can hold.
