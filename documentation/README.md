# Documentation site

Static HTML explaining every section of the compressor schematic. Open `index.html`, or
browse the published site — no build step needed to view it.

## Interactive schematics

Each section page carries a live viewer rather than a flat image:

- **Schematic** — the real KiCad drawing, exported from the project in the parent folder.
  Scroll to zoom, drag to pan. Every part has an invisible hotspot over it: click one and the
  panel shows its value, footprint, a short note on what it does, and every net it touches.
  Clicking a net highlights every other part on it.
- **Connections** — the same sheet as a node graph, drawn with
  [cytoscape.js](https://js.cytoscape.org/). Components *and* nets are both nodes, because a
  net joins any number of pins and an edge only joins two. Drag nodes about, click to trace.
- **Search** — type a designator (`R14`) or a net (`VBIAS`) to jump to it in either view.

The plain SVG is still one click away under each viewer, for printing or for reading at full
size.

## Files

| Path | What it is |
|---|---|
| `*.html` | The eight pages. Plain HTML — edit directly if you like. |
| `style.css` | All styling, light and dark. |
| `viewer.js` | The interactive viewer. No framework, ~330 lines. |
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
overlay follows your layout wherever you move things.

`_build.py` inlines each sheet's JSON into its page, which is why the viewer also works when
you open the files directly from disk rather than over http.

## Publishing

`documentation/` is not one of the two folders GitHub's simple Pages UI offers (`/` and
`/docs`), so the included workflow publishes it instead:

1. **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main`. `.github/workflows/pages.yml` does the rest.

Or rename this folder to `docs/` and pick "Deploy from a branch → /docs". Nothing inside the
site depends on the folder name. `.nojekyll` is present so Pages serves the files as-is.
