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

## Coordinates

The panel outline and every hole are drawn on User.Drawings, with the grid origin on the
panel's top-left corner. The board editor's coordinates read the same as the panel
drawing, and `panel/make_panel.py` takes its hole positions from this board.

## Check before ordering

- **The SPDT footprint follows the ST0300 datasheet** (lugs on 2.54 mm, slotted holes for the
  0.76 × 1.52 mm lugs). Jaycar publishes no drawing for the ST0310, so the DPDT footprint
  assumes the same lug pitch with the two rows 4.7 mm apart and a 9.4 mm wide body. Measure
  one before ordering boards.
- SW3 (HPF) and SW4 (LINK) are single-pole in the schematic and use the SPDT footprint's
  centre and top pins; the bottom pin is unused.
- There are no mounting holes: the nine bushing nuts hold the board. Add standoffs if it
  flexes.
