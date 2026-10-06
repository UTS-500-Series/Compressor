#!/bin/sh
# Rebuild the printable faceplate: hole data from make_panel.py, then the STLs.
# Needs OpenSCAD (2021.01 or later) and python3. Takes a few minutes.
set -e
cd "$(dirname "$0")"
python3 ../make_panel.py > /dev/null

for part in panel legend fit_test fit_legend; do
    name=$(echo "$part" | sed 's/_/-/')
    case $part in
        panel)  out=faceplate.stl ;;
        legend) out=faceplate-legend.stl ;;
        *)      out=faceplate-$name.stl ;;
    esac
    echo "rendering $out"
    openscad -q -o "$out" -D "part=\"$part\"" faceplate.scad
    # OpenSCAD writes ASCII STL; binary is a fifth of the size and every slicer reads it
    python3 - "$out" <<'EOF'
import struct, sys
path = sys.argv[1]
text = open(path).read()
if not text.lstrip().startswith('solid'):
    sys.exit()
tris, vs = [], []
for line in text.splitlines():
    w = line.split()
    if w[:1] == ['vertex']:
        vs.append(tuple(map(float, w[1:4])))
        if len(vs) == 3:
            tris.append(vs)
            vs = []
with open(path, 'wb') as f:
    f.write(b'faceplate'.ljust(80, b' '))
    f.write(struct.pack('<I', len(tris)))
    for a, b, c in tris:
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        m = sum(x * x for x in n) ** 0.5 or 1.0
        f.write(struct.pack('<12fH', *(x / m for x in n), *a, *b, *c, 0))
EOF
done
python3 make_3mf.py
