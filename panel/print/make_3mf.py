#!/usr/bin/env python3
"""Combine the panel and legend STLs into one 3MF for multicolour printing.

Each 3MF holds one object made of two parts, the panel and the legend, already in
place, with the panel on filament 1 and the legend on filament 2. The part table is
PrusaSlicer's (Metadata/Slic3r_PE_model.config), which Bambu Studio and OrcaSlicer read
as well. The triangles carry display colours too, dark panel and light legend.

    python3 make_3mf.py        (build.sh runs it after exporting the STLs)
"""
import os, struct, zipfile

PAIRS = [
    ('faceplate-multicolor.3mf', 'faceplate.stl', 'faceplate-legend.stl'),
    ('faceplate-fit-test-multicolor.3mf', 'faceplate-fit-test.stl', 'faceplate-fit-legend.stl'),
]
PANEL_COLOUR, LEGEND_COLOUR = '#2A2F33FF', '#F2EFE7FF'


def read_stl(path):
    """Indexed (vertices, triangles) from a binary or ASCII STL."""
    data = open(path, 'rb').read()
    tris = []
    n = struct.unpack('<I', data[80:84])[0] if len(data) >= 84 else 0
    if len(data) == 84 + 50 * n:
        for i in range(n):
            v = struct.unpack('<9f', data[84 + 50 * i + 12:84 + 50 * i + 48])
            tris.append((v[0:3], v[3:6], v[6:9]))
    else:
        tri = []
        for line in data.decode().splitlines():
            w = line.split()
            if w[:1] == ['vertex']:
                tri.append(tuple(map(float, w[1:4])))
                if len(tri) == 3:
                    tris.append(tuple(tri))
                    tri = []
    index, verts, faces = {}, [], []
    for tri in tris:
        f = []
        for v in tri:
            k = tuple(round(c, 5) for c in v)
            if k not in index:
                index[k] = len(verts)
                verts.append(k)
            f.append(index[k])
        if len(set(f)) == 3:
            faces.append(f)
    return verts, faces


def model(panel, legend, name):
    """One mesh object holding both parts; the legend's triangles get the second
    colour. Slicers learn where one part ends from Slic3r_PE_model.config."""
    (pv, pf), (lv, lf) = panel, legend
    off = len(pv)
    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<model unit="millimeter" xml:lang="en-US" '
         'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
         'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">',
         ' <metadata name="slic3rpe:Version3mf">1</metadata>',
         ' <metadata name="Title">%s</metadata>' % name,
         ' <metadata name="Designer">UTS 500 Series</metadata>',
         ' <metadata name="LicenseTerms">CERN-OHL-S-2.0</metadata>',
         ' <resources>',
         '  <basematerials id="1">',
         '   <base name="Panel" displaycolor="%s"/>' % PANEL_COLOUR,
         '   <base name="Legend" displaycolor="%s"/>' % LEGEND_COLOUR,
         '  </basematerials>',
         '  <object id="2" name="%s" type="model" pid="1" pindex="0">' % name,
         '   <mesh>', '    <vertices>']
    o += ['     <vertex x="%.5f" y="%.5f" z="%.5f"/>' % v for v in pv + lv]
    o += ['    </vertices>', '    <triangles>']
    o += ['     <triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in pf]
    o += ['     <triangle v1="%d" v2="%d" v3="%d" pid="1" p1="1"/>'
          % tuple(i + off for i in f) for f in lf]
    o += ['    </triangles>', '   </mesh>', '  </object>', ' </resources>',
          ' <build>', '  <item objectid="2"/>', ' </build>', '</model>', '']
    return '\n'.join(o)


def parts_config(name, n_panel, n_legend):
    """PrusaSlicer's part table, which Bambu Studio and OrcaSlicer also read: the
    triangle range of each part and the filament it prints with."""
    def volume(first, last, part, extruder):
        return '\n'.join([
            '  <volume firstid="%d" lastid="%d">' % (first, last),
            '   <metadata type="volume" key="name" value="%s"/>' % part,
            '   <metadata type="volume" key="volume_type" value="ModelPart"/>',
            '   <metadata type="volume" key="extruder" value="%d"/>' % extruder,
            '   <metadata type="volume" key="matrix" '
            'value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>',
            '  </volume>'])
    return '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>', '<config>',
        ' <object id="2" instances_count="1">',
        '  <metadata type="object" key="name" value="%s"/>' % name,
        '  <metadata type="object" key="extruder" value="1"/>',
        volume(0, n_panel - 1, 'Panel', 1),
        volume(n_panel, n_panel + n_legend - 1, 'Legend', 2),
        ' </object>', '</config>', ''])


CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
'''
RELS = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
'''


def write_3mf(out, panel_stl, legend_stl):
    name = os.path.splitext(os.path.basename(out))[0]
    panel, legend = read_stl(panel_stl), read_stl(legend_stl)
    xml = model(panel, legend, name)
    cfg = parts_config(name, len(panel[1]), len(legend[1]))
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        # fixed timestamps, so rebuilding unchanged STLs gives an identical file
        for arc, text in (('[Content_Types].xml', CONTENT_TYPES), ('_rels/.rels', RELS),
                          ('3D/3dmodel.model', xml),
                          ('Metadata/Slic3r_PE_model.config', cfg)):
            z.writestr(zipfile.ZipInfo(arc, (2026, 1, 1, 0, 0, 0)), text,
                       zipfile.ZIP_DEFLATED)


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    for out, panel, legend in PAIRS:
        write_3mf(out, panel, legend)
        print('wrote %-36s %6.1f KB' % (out, os.path.getsize(out) / 1024))
