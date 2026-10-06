#!/usr/bin/env python3
"""Combine the panel and legend STLs into 3MFs for multicolour printing.

Each 3MF holds one object made of two parts, the panel and the legend, already in
place, with the panel on filament 1 and the legend on filament 2. Slicers keep their
part tables in different files, so there are two flavours:

    faceplate-multicolor.3mf               Bambu Studio and OrcaSlicer
                                           (Metadata/model_settings.config)
    faceplate-multicolor-prusaslicer.3mf   PrusaSlicer (Metadata/Slic3r_PE_model.config)

and the same pair for the fit test.

    python3 make_3mf.py        (build.sh runs it after exporting the STLs)
"""
import os, struct, uuid, zipfile

PAIRS = [
    ('faceplate', 'faceplate.stl', 'faceplate-legend.stl'),
    ('faceplate-fit-test', 'faceplate-fit-test.stl', 'faceplate-fit-legend.stl'),
]
PANEL_COLOUR, LEGEND_COLOUR = '#2A2F33FF', '#F2EFE7FF'
# where the panel's centre lands on the build plate: inside every Bambu bed, A1 mini too
PLATE_CENTRE = (90.0, 90.0)

CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
BBS = 'http://schemas.bambulab.com/package/2021'
MODEL_REL = 'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel'
IDENTITY = '1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'


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


def mesh_xml(verts, faces, extra='', off=0):
    o = ['    <mesh>', '     <vertices>']
    o += ['      <vertex x="%.5f" y="%.5f" z="%.5f"/>' % v for v in verts]
    o += ['     </vertices>', '     <triangles>']
    o += ['      <triangle v1="%d" v2="%d" v3="%d"%s/>' % (f[0] + off, f[1] + off, f[2] + off,
                                                          extra) for f in faces]
    o += ['     </triangles>', '    </mesh>']
    return '\n'.join(o)


def bbox_centre(*meshes):
    xs = [v[0] for m in meshes for v in m[0]]
    ys = [v[1] for m in meshes for v in m[0]]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'uts500/compressor/' + '/'.join(parts)))


# ------------------------------------------------------------------ Bambu / Orca
def bambu_files(name, panel, legend):
    """Bambu Studio's own project layout: the parts are separate mesh objects in
    3D/Objects/, joined by a components object, with their names and filaments in
    Metadata/model_settings.config."""
    cx, cy = bbox_centre(panel, legend)
    move = '1 0 0 0 1 0 0 0 1 %.4f %.4f 0' % (PLATE_CENTRE[0] - cx, PLATE_CENTRE[1] - cy)
    parts = [(1, 'Panel', 1, panel), (2, 'Legend', 2, legend)]
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="millimeter" xml:lang="en-US" xmlns="%s" xmlns:BambuStudio="%s" '
            'xmlns:p="%s" requiredextensions="p">\n' % (CORE, BBS, PROD))
    sub = [head, ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n', ' <resources>\n']
    for pid, pname, ext, (v, f) in parts:
        sub.append('  <object id="%d" p:UUID="%s" type="model">\n%s\n  </object>\n'
                   % (pid, uid(name, pname), mesh_xml(v, f)))
    sub.append(' </resources>\n <build/>\n</model>\n')
    main = [head,
            ' <metadata name="Application">BambuStudio-01.10.00.00</metadata>\n',
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n',
            ' <metadata name="Title">%s</metadata>\n' % name,
            ' <metadata name="Designer">UTS 500 Series</metadata>\n',
            ' <metadata name="LicenseTerms">CERN-OHL-S-2.0</metadata>\n',
            ' <resources>\n',
            '  <object id="3" p:UUID="%s" type="model">\n   <components>\n' % uid(name)]
    for pid, pname, ext, mesh in parts:
        main.append('    <component p:path="/3D/Objects/object_1.model" objectid="%d" '
                    'p:UUID="%s" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
                    % (pid, uid(name, pname, 'component')))
    main += ['   </components>\n  </object>\n </resources>\n',
             ' <build p:UUID="%s">\n' % uid(name, 'build'),
             '  <item objectid="3" p:UUID="%s" transform="%s" printable="1"/>\n'
             % (uid(name, 'item'), move),
             ' </build>\n</model>\n']
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <object id="3">\n',
           '    <metadata key="name" value="%s"/>\n' % name,
           '    <metadata key="extruder" value="1"/>\n']
    for pid, pname, ext, mesh in parts:
        cfg += ['    <part id="%d" subtype="normal_part">\n' % pid,
                '      <metadata key="name" value="%s"/>\n' % pname,
                '      <metadata key="matrix" value="%s"/>\n' % IDENTITY,
                '      <metadata key="extruder" value="%d"/>\n' % ext,
                '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" '
                'facets_reversed="0" backwards_edges="0"/>\n',
                '    </part>\n']
    cfg += ['  </object>\n',
            '  <plate>\n',
            '    <metadata key="plater_id" value="1"/>\n',
            '    <metadata key="plater_name" value=""/>\n',
            '    <metadata key="locked" value="false"/>\n',
            '    <model_instance>\n',
            '      <metadata key="object_id" value="3"/>\n',
            '      <metadata key="instance_id" value="0"/>\n',
            '      <metadata key="identify_id" value="1"/>\n',
            '    </model_instance>\n',
            '  </plate>\n',
            '  <assemble>\n',
            '   <assemble_item object_id="3" instance_id="0" transform="%s" offset="0 0 0"/>\n'
            % move,
            '  </assemble>\n</config>\n']
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="%s"/>\n'
            '</Relationships>\n' % MODEL_REL)
    return [('3D/3dmodel.model', ''.join(main)),
            ('3D/Objects/object_1.model', ''.join(sub)),
            ('3D/_rels/3dmodel.model.rels', rels),
            ('Metadata/model_settings.config', ''.join(cfg))]


# ------------------------------------------------------------------ PrusaSlicer
def prusa_files(name, panel, legend):
    """PrusaSlicer's layout: one mesh object holding both parts, split into parts by
    triangle range in Metadata/Slic3r_PE_model.config. The legend's triangles also
    carry the second display colour."""
    (pv, pf), (lv, lf) = panel, legend
    model = '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" xmlns="%s" '
        'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">' % CORE,
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
        mesh_xml(pv + lv, [], ''),
        '  </object>',
        ' </resources>',
        ' <build>', '  <item objectid="2"/>', ' </build>', '</model>', ''])
    # the triangles go in after the shared vertex list
    tris = '\n'.join(['      <triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in pf] +
                     ['      <triangle v1="%d" v2="%d" v3="%d" pid="1" p1="1"/>'
                      % tuple(i + len(pv) for i in f) for f in lf])
    model = model.replace('     <triangles>\n     </triangles>',
                          '     <triangles>\n%s\n     </triangles>' % tris)

    def volume(first, last, part, extruder):
        return '\n'.join([
            '  <volume firstid="%d" lastid="%d">' % (first, last),
            '   <metadata type="volume" key="name" value="%s"/>' % part,
            '   <metadata type="volume" key="volume_type" value="ModelPart"/>',
            '   <metadata type="volume" key="extruder" value="%d"/>' % extruder,
            '   <metadata type="volume" key="matrix" value="%s"/>' % IDENTITY,
            '  </volume>'])
    cfg = '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>', '<config>',
        ' <object id="2" instances_count="1">',
        '  <metadata type="object" key="name" value="%s"/>' % name,
        '  <metadata type="object" key="extruder" value="1"/>',
        volume(0, len(pf) - 1, 'Panel', 1),
        volume(len(pf), len(pf) + len(lf) - 1, 'Legend', 2),
        ' </object>', '</config>', ''])
    return [('3D/3dmodel.model', model), ('Metadata/Slic3r_PE_model.config', cfg)]


# ------------------------------------------------------------------ package
CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
'''
RELS = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="%s"/>
</Relationships>
''' % MODEL_REL


def write_3mf(out, files):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        # fixed timestamps, so rebuilding unchanged STLs gives an identical file
        for arc, text in [('[Content_Types].xml', CONTENT_TYPES), ('_rels/.rels', RELS)] + files:
            z.writestr(zipfile.ZipInfo(arc, (2026, 1, 1, 0, 0, 0)), text,
                       zipfile.ZIP_DEFLATED)
    print('wrote %-44s %6.1f KB' % (out, os.path.getsize(out) / 1024))


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    for name, panel_stl, legend_stl in PAIRS:
        panel, legend = read_stl(panel_stl), read_stl(legend_stl)
        write_3mf(name + '-multicolor.3mf', bambu_files(name, panel, legend))
        write_3mf(name + '-multicolor-prusaslicer.3mf', prusa_files(name, panel, legend))
