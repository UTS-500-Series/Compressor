# Documentation site

Static HTML explaining every section of the compressor schematic. Open `index.html`, or
browse the published site — no build step needed to view it.

## Interactive schematics

Each section page carries a live viewer rather than a flat image:

- **Schematic** — the real KiCad drawing, exported from the project in the parent folder.
  Scroll to zoom, drag to pan. Every part has an invisible hotspot over it: click one and the
  panel shows its value, footprint, a short note on what it does, and every net it touches.
  Clicking a net highlights every other part on it.
- **Connections** — the same sheet drawn as a schematic-style graph with
  [cytoscape.js](https://js.cytoscape.org/): real part symbols, orthogonal wires and grid
  paper. Three things make it read like a drawing rather than a netlist dump:
  power and ground get **their own glyph on every pin**, exactly as a real schematic does,
  rather than one hub node with thirty wires fanning out; a **two-pin net is just a wire**
  between the parts, labelled with its name; and a net with **three or more pins gets a
  junction dot**. Drag parts about, click anything to trace it.
- **Tracing** — hover any wire or part and its whole net lights up while everything else
  fades back, with the net name shown in the strip below. Following one connection through a
  crossing is the thing a static picture cannot help with, so it does not cost a click.
  Clicking makes the same highlight stick and fills the detail panel.
- **Colour** — wires carry the same colour language as the rest of the site: amber for audio,
  teal for control, wine for supply rails, grey for ground. There is a legend under the graph.
- **Labels** — every part shows its designator and value, every wire its net name, and each
  wire end the pin number it lands on.
- **Nothing overlaps** — parts are placed on a layered grid rather than by a force
  simulation, so collisions are impossible by construction rather than by luck. Wires turn in
  the gutters between columns, which keeps every vertical run in empty space. The `Roomy` /
  `Compact` button changes the spacing; both are checked.

### How the no-overlap guarantee works

A force layout looks organic and overlaps constantly — nodes land on each other, labels
collide, wires run through parts. This lays out deterministically instead:

1. split the graph into connected pieces (a sheet is often several)
2. rank each piece by breadth-first distance from its best-connected node → column
3. order nodes within a column by the average row of their neighbours, a couple of barycentre
   sweeps, which pulls connected things level and cuts crossings
4. one node per cell, with cells sized from the widest label **as actually rendered** — the
   spacing grows and re-places until a measurement says nothing collides

Wires then turn in the gutter beside their source column, fanned a few pixels apart so two
wires never draw the same vertical line. Because gutters are empty by construction, wires
cannot cross parts.

Measured on every sheet, both spacings — node overlaps **0**, wires over parts **0**:

| Sheet | Nodes | Wires |
|---|---|---|
| Connector | 16 | 15 |
| Input | 26 | 27 |
| VCA | 56 | 60 |
| Output | 37 | 43 |
| Sidechain | 54 | 66 |
| Power | 128 | 88 |

The check is in the page, not just in this file: `document.querySelector('.iv')._ivDebug()`
returns the live counts from the browser console.

> Wires still **cross** each other — that is unavoidable in any graph that is not planar, and
> no amount of layout work removes it. What is guaranteed is that nothing is *hidden*: no part
> sits on another, no label is obscured, and no wire disappears behind a component. Hover any
> wire to trace it through a crossing.
- **Search** — type a designator (`R14`) or a net (`VBIAS`) to jump to it in either view.

## Wide layout

The sidebar carries a **Wide layout** toggle. Pages sit at a reading width by default; the
toggle widens them to **1240 px** so schematics, graphs and tables have room. It is a wider cap,
not an uncapped page — on a large monitor unbounded prose runs to unreadable line lengths.
Change `--wide-max` at the top of `style.css` to taste. The choice is
remembered in `localStorage` and applied in the page `<head>` before first paint, so it does
not flash narrow on load, and the schematic viewer re-fits itself when the column changes width
underneath it.

It only lifts the cap — it never changes padding. On a narrow window the cap was not binding
anyway, so adding padding there would make the toggle actively worse. The control hides itself
below 900 px for the same reason.

The plain SVG is still one click away under each viewer, for printing or for reading at full
size.

## Files

| Path | What it is |
|---|---|
| `*.html` | The nine pages. Plain HTML — edit directly if you like. |
| `style.css` | All styling, light and dark. |
| `viewer.js` | The interactive viewer: hotspots, pan/zoom, schematic-style graph. No framework. |
| `vendor/cytoscape.min.js` | Vendored so the site works offline and does not depend on a CDN. |
| `img/*.svg` | Sheet exports from KiCad. |
| `data/*.json` | Per-sheet component boxes and netlist, generated from the project. |
| `_build.py` | Regenerates the eight pages. |
| `_data.py` | Regenerates `data/*.json` from the schematics and `design.py`. |

## After changing the schematic

```bash
# 1. re-export the sheet images
kicad-cli sch export svg --no-background-color -o /tmp/svg "../UTS Mini Mixing Desk - Compressor.kicad_sch"
#    then copy the six sheets into img/ as connector.svg, input.svg, vca.svg,
#    output.svg, sidechain.svg, power.svg

# 2. rebuild the hotspots and graph data, then the pages
python3 _data.py
python3 _build.py
```

`_data.py` reads component positions straight out of the `.kicad_sch` files, so the clickable
overlay follows your layout wherever you move things. It imports the helpers in
[`../tools`](../tools), which are part of this repository — nothing outside it is needed.

`_build.py` inlines each sheet's JSON into its page, which is why the viewer also works when
you open the files directly from disk rather than over http.

It also copies the faceplate artwork out of `../panel/` into `img/` on every run, so the front
panel page always shows whatever layout and finish you last generated. Re-run `_build.py`
after `make_panel.py` and the site follows.

## Publishing

`documentation/` is not one of the two folders GitHub's simple Pages UI offers (`/` and
`/docs`), so the included workflow publishes it instead:

1. **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main`. `.github/workflows/pages.yml` does the rest.

Or rename this folder to `docs/` and pick "Deploy from a branch → /docs". Nothing inside the
site depends on the folder name. `.nojekyll` is present so Pages serves the files as-is.
