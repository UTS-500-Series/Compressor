# Compressor front board

A 35 × 110 mm board that sits flat behind the faceplate and carries everything on the
panel: the five pots, the four toggles, and both LED meters with their two LM3914
drivers. It joins the main board with a 30-way ribbon from J1 here to J2 on the main board,
pin for pin, with the same net names in both schematics.

The parts are the ones drawn in the main schematic. They stay drawn there (excluded from
that board and its BOM) so the circuit still reads as one piece.

## How it sits

- The front of the board faces the panel. Pots, toggles, LEDs, the driver ICs and their
  small parts all go on the front.
- J1 (a plain 2×15 pin header) and C38 (47 µF, too tall for the front) go on the back.
- The toggles are Salecom mini toggles from Altronics: S1350 (DPDT) for BYPASS, S1315 (SPDT)
  for KEY, HPF and LINK. Their body stands 10.4 mm off the board and the Altronics 9 mm pots
  stand 10.6 mm, so the board sits **about 10.6 mm behind the panel**, with the pot bodies
  against the back of the panel and the toggles 0.2 mm short of it.
- Alps RK09K pots, if you use them instead, are shorter: make up the difference with a nut
  behind the panel, which may need the longer bushing version.
- The LEDs need spacers to reach the panel: about 7.8 mm for the 2 mm flat-tops drawn here
  (10.6 mm gap less the 2.8 mm LED), or about 5.3 mm for 3 mm flangeless LEDs.
- The pots' 5 mm bushing leaves under 2 mm of thread through a 3.18 mm panel: see
  `panel/README.md` on panel thickness. The toggles' 8.9 mm bushing is plenty.
- The pins of all four toggles come through the back by about 0.8 mm.
- The main board's front edge is set back 24 mm from the panel to clear this board, the
  header and the ribbon plug. The board's back face is now about 12.2 mm behind the panel,
  so check the plug on J1 still clears it, especially with single-way sockets (taller than
  an IDC plug).

## Joining the boards

The boards are joined only by the ribbon; each one is fixed to the faceplate on its own.

- **Ribbon:** 30-way, 2.54 mm pitch, with an IDC socket crimped on each end. Main board
  J2 is a shrouded box header; J1 here is a plain pin header, so it isn't keyed. Put the
  red stripe on pin 1 at both ends (pin 1 is marked on the back silkscreen).
  Altronics has no 30-way IDC parts, so `bom/altronics.csv` lists a plain 2×15 header for
  J2 as well and a 150 mm socket-to-socket strip of single-way leads (P1023) for the ribbon.
  It works, but nothing keys it: keep lead 1 on pin 1 at both ends. For a proper IDC ribbon,
  buy the box header, two sockets and cable from element14.
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
- The toggles use simple models built to the Altronics drawings by
  `tools/make_toggle_models.py` (case, bushing, lever and pins).
- The main board's edge fingers are copper, not a part, so J1 there has no model.

## Check before ordering

- **The toggle footprints follow the drawings on Altronics' S1315 and S1350 pages:** pins on
  4.70 mm, 1.3 mm holes, the DPDT's two rows 4.83 mm apart. The S1332 (centre off) has the
  same drawing as the S1315, so it drops into any SPDT position. Check one switch against the
  footprint before ordering boards.
- The toggles sit at x = 7.15 and 30.95 mm (panel coordinates), 0.25 mm in from the old
  sub-miniature positions, so the S1350's 11.4 mm body stays on the board. The pot footprint's
  courtyard was trimmed to its pads so it doesn't overlap the S1350's.
- **The Altronics 9 mm pots (R19xx)** have the RK09K's pin and lug pattern (lugs 8.6 mm apart,
  pins 7.0 mm behind them), so they use the same footprint. Their drawing doesn't place the
  shaft relative to the lugs; the RK09K's is 0.5 mm beyond them. Check before cutting the panel.
- SW3 (HPF) and SW4 (LINK) are single-pole in the schematic and use the SPDT footprint's
  top and centre pins; the bottom pin is unused.
- There are no mounting holes: the nine bushing nuts hold the board. Add standoffs if it
  flexes.
