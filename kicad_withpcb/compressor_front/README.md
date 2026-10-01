# Compressor front board

A 35 × 110 mm board that sits flat behind the faceplate and carries everything on the
panel: the five pots, the four toggles, and both LED meters with their LM3914 / LM3915
drivers. It joins the main board with a 30-way ribbon from J1 here to J2 on the main board,
pin for pin, with the same net names in both schematics.

The parts are the ones drawn in the main schematic. They stay drawn there (excluded from
that board and its BOM) so the circuit still reads as one piece.

## How it sits

- The front of the board faces the panel. Pots, toggles, LEDs, the driver ICs and their
  small parts all go on the front.
- J1 (a plain 2×15 pin header) and C38 (47 µF, too tall for the front) go on the back.
- The toggles are Jaycar ST0300 (SPDT) and ST0310 (DPDT) sub-miniature switches. Their body
  is 8.64 mm deep with 2.8 mm solder lugs, so the board sits **about 8.7 mm behind the panel**
  with the switch bodies resting on it and the lugs through the board.
- At that gap the RK09K pots likely stand a little short of the panel. Check the pot's body
  height against 8.7 mm and make up the difference with a nut behind the panel, which may
  need the longer bushing version of the pot.
- The LEDs need spacers of about 6 mm (8.7 mm gap less the LED body) to reach the panel.
- The toggles' bushing is only 4.06 mm long: see `panel/README.md` on panel thickness.
- The main board's front edge is set back 24 mm from the panel to clear this board, the
  header and the ribbon plug.

## Joining the boards

The boards are joined only by the ribbon; each one is fixed to the faceplate on its own.

- **Ribbon:** 30-way, 2.54 mm pitch, with an IDC socket crimped on each end. Main board
  J2 is a shrouded box header; J1 here is a plain pin header, so it isn't keyed. Put the
  red stripe on pin 1 at both ends (pin 1 is marked on the back silkscreen).
- **Length:** about 150 mm, folded once between the boards. J2 sits roughly 30 mm behind
  the panel and about 35 mm higher than J1, and the sideways distance depends on where the
  main board sits in your rack, so lay the boards out and check before crimping.
- **Front board to panel:** the nuts on the five pot and four toggle bushings.
- **Main board to panel:** an L-bracket from the back of the panel to H1 and H2, the two
  M3 holes by the main board's front edge (85 mm apart). The front edge is 24 mm behind
  the panel, so the bracket leg along the board needs to reach that far: 25 × 25 mm
  aluminium angle, or a short angle with standoffs. H2 is plated and tied to CHASSIS
  (J1 pin 1), so the bracket also grounds the panel as the faceplate guide asks. Mask
  the anodise where the bracket touches the panel.

## Coordinates

The panel outline and every hole are drawn on User.Drawings, with the grid origin on the
panel's top-left corner. The board editor's coordinates read the same as the panel
drawing, and `panel/make_panel.py` takes its hole positions from this board.

## 3D models

Every part has a 3D model, so the 3D viewer and a STEP export (for the Fusion 360 assembly)
show both boards complete.

- Most come from KiCad's own library.
- The pots use Alps' official RK09K1130 model. It's the maker's file, so it isn't kept in
  git: run `sh tools/get_3d_models.sh` once to fetch it into `3dmodels/`. The pots use a
  project copy of the stock RK09K footprint that points at it.
- The toggles use simple models built to the Jaycar datasheet by
  `tools/make_toggle_models.py` (case, bushing, lever and lugs).
- The main board's edge fingers are copper, not a part, so J1 there has no model.

## Check before ordering

- **The SPDT footprint follows the ST0300 datasheet** (lugs on 2.54 mm, slotted holes for the
  0.76 × 1.52 mm lugs). Jaycar publishes no drawing for the ST0310, so the DPDT footprint
  assumes the same lug pitch with the two rows 4.7 mm apart and a 9.4 mm wide body. Measure
  one before ordering boards.
- SW3 (HPF) and SW4 (LINK) are single-pole in the schematic and use the SPDT footprint's
  centre and top pins; the bottom pin is unused.
- There are no mounting holes: the nine bushing nuts hold the board. Add standoffs if it
  flexes.
