# 3D-printed faceplate

A faceplate you can print on an ordinary FDM printer, for anyone without a laser cutter,
CNC or panel shop. Same holes and legends as the `toggle` layout in [`../`](../README.md),
so it fits the front board as drawn.

<img src="faceplate-print.png" width="180" alt="Printed faceplate, front">

| File | What it is |
|---|---|
| `faceplate-multicolor.3mf` | Panel and legend as one object with two parts, for a two-colour print in Bambu Studio or OrcaSlicer. |
| `faceplate-multicolor-prusaslicer.3mf` | The same for PrusaSlicer, which keeps its part table in a different file. |
| `faceplate-fit-test-multicolor.3mf`, `-prusaslicer.3mf` | The same pair for the fit test. |
| `faceplate.step` | The faceplate as a solid for CAD (Fusion, FreeCAD, SolidWorks, Onshape), with the legend as a second body. See [In CAD](#in-cad). |
| `faceplate-blank.step` | The same faceplate with no legend: every hole and pot well, a plain front. |
| `faceplate-legend.dxf` | The legend and ticks as outlines, one layer per label, for laying out your own legend on the blank. |
| `faceplate.stl` | The faceplate, already flipped face down for printing. |
| `faceplate-legend.stl` | The engraved legend and pot ticks as their own body, for a second colour. |
| `faceplate-fit-test.stl` | A 27 mm strip across THRESHOLD, HPF, KEY and the bottom of both meters. |
| `faceplate-fit-legend.stl` | The fit test's legend. |
| `faceplate.scad` | The model. Every print setting is a parameter at the top. |
| `panel_data.scad` | Hole positions and legend text, written by `make_panel.py`. Don't edit it. |
| `build.sh` | Re-runs `make_panel.py`, exports all four STLs (a few minutes), builds the 3MFs and, if CadQuery is installed, the STEP. |
| `make_3mf.py` | Combines each panel and legend STL into the two 3MFs. |
| `make_step.py` | Builds the two STEPs and the legend DXF from the same two `.scad` files. |

## What's different from the metal panel

- **Thickness:** 3.2 mm, the same as the 1/8″ metal panel, so the rack screws and everything
  behind the panel sit exactly where the front board expects. The back is flat.
- **Pot wells:** each pot hole has a 12.5 mm counterbore on the front, 1.2 mm deep. That leaves
  2.0 mm of plastic under the nut, which gives the 9 mm pots' short bushing about 3 mm of
  thread for the washer and nut (the metal panel needed thinning here for the same reason).
  The 11 mm knobs sit over the wells.
- **Fit allowance:** pot, toggle and screw holes print 0.2 mm larger than drawn
  (`hole_comp`), because FDM holes come out undersize. The meter holes stay 2.2 mm: the LEDs
  sit behind the panel, so those holes only let the light out, and keeping them small keeps
  0.8 mm of plastic between neighbours.
- **Width and height:** 37.8 × 132.6 mm rather than the nominal 38.10 × 133.35, so it slides in
  beside the next module. The front edge has a 0.4 mm chamfer so first-layer squish doesn't
  flare it.
- **Legend:** engraved 0.4 mm into the front, 30% larger than on the mockup (the mockup's
  1.4 to 1.7 mm capitals are too fine for a 0.4 mm nozzle). Each pot gets three ticks: start,
  middle and end of travel.

## Printing it

1. **Print the fit test first.** It's a short print. Check that a pot and a toggle drop
   through their holes, the pot nut sits inside its well, and the LEDs line up behind the
   meter holes. If a hole is tight or loose, change `hole_comp` in `faceplate.scad` and run
   `./build.sh` (or open the file in OpenSCAD and use the Customizer).
2. **Material:** PETG in black or dark grey. A light colour lets each meter LED glow through
   the thin walls on either side of its hole. PETG over PLA because a rack runs warm and
   PLA slowly gives way under a tightened nut.
3. **Settings:** 0.4 mm nozzle, 0.2 mm layers, 4 walls, 100% infill, no supports. Print it as
   exported, face down. A textured PEI sheet gives the front a nice finish.
4. **Two colours (optional):** in Bambu Studio or OrcaSlicer, import `faceplate-multicolor.3mf`
   (File, Import, or Cmd/Ctrl+I); in PrusaSlicer use `faceplate-multicolor-prusaslicer.3mf`.
   It loads as one object with two parts already lined up: the panel on filament 1 and the
   legend on filament 2. Pick a dark filament for 1 and a light one for 2. The file carries no
   print settings, so opening it as a project in Bambu Studio says it is loading geometry
   only; that's expected. Both colours share the first two layers, so it needs a multicolour
   unit (AMS, MMU) or a second nozzle, but it only swaps on those two layers.
   With one colour, print `faceplate.stl` and fill the engraving afterwards with paint or a
   white wax crayon rubbed in and wiped off.

## In CAD

`faceplate.step` is the same faceplate as a real solid model: true cylinders, cones and
fillets rather than a mesh, so you can measure it, add features, or line it up with the
boards' STEP exports. It is in millimetres, front face up, with x to the right and y up. The
origin is the bottom-left corner of the nominal 38.10 × 133.35 mm panel, so the printed
outline starts at (0.15, 0.375); the back face is at z = 0 and the front at z = 3.2.

It holds two components, coloured as the two-colour print:

- **panel**, dark grey, with the legend and ticks engraved 0.4 mm into the front.
- **legend**, off-white, the inlay that fills the engraving, one small body per letter and
  tick. Hide or delete it if you only want the panel.

In Fusion, use File, Open, Open from my computer and pick `faceplate.step`.

### Your own legend

`faceplate-blank.step` is the panel with no legend, and `faceplate-legend.dxf` is the
legend as closed outlines (lines and curves, not text), in the same coordinates as both
STEPs. Each label is on its own layer (`GR`, `LVL`, `THRESHOLD`, ...), and so are each
pot's ticks (`TICKS-THRESHOLD`, ...). `OUTLINE`, `HOLES` and `POT-WELLS` are there to line
things up and aren't meant to be cut.

In Fusion: open the blank, then Insert, Insert DXF, and pick the front face as the plane. If
the dialog offers a single-sketch option, turn it off so each layer comes in as its own
sketch, which makes a label easy to select and move. Move or delete labels
(for example, take `GR` and `LVL` above the meters), then Extrude the outlines into the
face by -0.4 mm with Cut for an engraved legend. For a second colour, extrude the same
profiles again as a New Body, which gives you the inlay.

`make_step.py` builds all three with CadQuery from `faceplate.scad` and `panel_data.scad`, so it
follows any change to `hole_comp`, the legend settings or the hole positions:
`pip install cadquery uharfbuzz`, then `python3 make_step.py` (about ten seconds). It lays out
the legend the way OpenSCAD 2021 does, using the font's own curves; checked against the
STLs, 99% of their vertices sit within 0.007 mm of the STEP's edges and all of them within
0.11 mm.

## Fitting it

- Snap the small anti-rotation tab off the front of each pot, as you would for a metal
  panel, or it holds the pot off the back of the panel.
- Tighten the nuts gently. Plastic creeps, and the nuts only need to hold the board.
- A plastic panel doesn't ground the pot and toggle bushings the way an anodised panel tied
  to CHASSIS does. If touching a knob adds hum, run a wire from a solder tag under one toggle's
  nut to the main board's CHASSIS (H2).
