#!/bin/sh
# Plot the Gerbers and drill files for both boards into each board's Gerbs/ folder and
# zip them for the fab. Run it after every board change, so the zip never lags the board.
# Needs KiCad 10's kicad-cli (set KICAD_CLI if it is not on PATH).
set -e
KC=${KICAD_CLI:-kicad-cli}   # on a Mac: /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
cd "$(dirname "$0")/../kicad_withpcb"
LAYERS=F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts
for b in compressor_with_pcb compressor_front; do
    out=$b/Gerbs
    rm -rf "$out"; mkdir -p "$out"
    "$KC" pcb export gerbers --layers "$LAYERS" --no-protel-ext --subtract-soldermask \
        -o "$out/" "$b/$b.kicad_pcb"
    "$KC" pcb export drill --format excellon --excellon-units mm --excellon-separate-th \
        -o "$out/" "$b/$b.kicad_pcb"
    (cd "$out" && zip -q "../$b-gerbers.zip" *.gbr *.drl *.gbrjob && mv "../$b-gerbers.zip" .)
    echo "$out/$b-gerbers.zip"
done
