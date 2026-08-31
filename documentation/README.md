# Documentation site

Static HTML explaining every section of the compressor schematic. No build step is
required to view it — open `index.html`, or browse the published site.

## Publishing

`documentation/` is not one of the two folders GitHub's simple Pages UI offers
(`/` and `/docs`), so the included workflow publishes it instead:

1. **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main`. `.github/workflows/pages.yml` does the rest.

If you would rather avoid the workflow, rename this folder to `docs/` and pick
"Deploy from a branch → /docs" in that same settings page. Nothing inside the site
depends on the folder name.

## Editing

Every page is plain HTML with one shared `style.css` — edit them directly if you like.

`_build.py` regenerates all eight pages from a single source so the nav, header and
footer stay consistent. If you edit the HTML by hand, either stop using the script or
fold your changes back into it, otherwise the next run overwrites them.

```bash
python3 _build.py
```

## Figures

`img/*.svg` are exported straight from the KiCad project in the parent folder, so they
show the real schematic. To refresh them after editing a sheet:

```bash
kicad-cli sch export svg --no-background-color -o /tmp/svg "../UTS Mini Mixing Desk - Compressor.kicad_sch"
```

then copy the six sheet SVGs into `img/` as `connector.svg`, `input.svg`, `vca.svg`,
`output.svg`, `sidechain.svg`, `power.svg`.

`.nojekyll` is present so GitHub Pages serves the files as-is.
