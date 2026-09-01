# Tools

Python helpers for this project. No dependencies beyond the standard library — they call
`kicad-cli` for anything that needs KiCad itself.

Both KiCad paths are discovered automatically, with environment overrides if yours are
somewhere unusual:

```bash
export KICAD_CLI=/path/to/kicad-cli
export KICAD_SYMBOL_DIR=/path/to/kicad/symbols
```

## Safe to run any time

| Script | What it does |
|---|---|
| `verify_netlist.py` | Exports the netlist with `kicad-cli` and diffs it against `design.py`, net by net and pin by pin. **Run this after any significant edit.** |
| `sexp.py` | KiCad s-expression parser and symbol-library resolver. Imported by the others. |
| `design.py` | The netlist as data — the source of truth everything is checked against. |

```bash
python3 tools/verify_netlist.py
```

## Destructive — read before running

> ⚠️ **`gen_project.py` and `route_sch.py` regenerate the schematic from scratch and will
> overwrite every sheet, destroying hand-drawn layout.** They built the first version of this
> project; the sheets have been laid out by hand since. Do not run them unless you actually
> want to start the drawing again.

| Script | What it does |
|---|---|
| `gen_project.py` | Regenerates the whole seven-sheet project: placement, routing, verification. |
| `route_sch.py` | Single-sheet router, plus the symbol geometry helpers the other tools import. |
| `place.py` | Placement rules — anchors, slots, and the power-sheet grouping. |

If you do want to regenerate, commit first, and write to a scratch directory:

```bash
python3 tools/gen_project.py -d /tmp/regenerated
```

## Editing the design

`design.py` is the authoritative netlist. Change a value there **and** in the schematic, then
run `verify_netlist.py` to confirm the two still agree. If they disagree, the tool prints the
exact nets and pins involved.
