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
- The board sits **10 mm behind the panel**, held by the pot and toggle nuts. Check that
  the pot bushings are long enough for 10 mm plus the panel thickness plus a nut, or add
  spacer nuts behind the panel.
- The LEDs need 7 mm spacers (10 mm gap less the LED body) so they reach the panel holes.
- The main board's front edge is set back 24 mm from the panel to clear this board, the
  header and the ribbon plug.

## Coordinates

The panel outline and every hole are drawn on User.Drawings, with the grid origin on the
panel's top-left corner. The board editor's coordinates read the same as the panel
drawing, and `panel/make_panel.py` takes its hole positions from this board.

## Check before ordering

- **Toggle footprints are drawn from typical parts, not a datasheet.** `SW_Toggle_Mini_SPDT`
  and `SW_Toggle_Mini_DPDT` in `compressor_front.pretty` assume PC pins on a 4.7 mm pitch
  (4.8 mm between rows on the DPDT). Measure the switch you buy and correct the footprint
  if needed.
- SW3 (HPF) and SW4 (LINK) are single-pole in the schematic and use the SPDT footprint's
  centre and top pins; the bottom pin is unused.
- There are no mounting holes: the nine bushing nuts hold the board. Add standoffs if it
  flexes.
