/* Interactive schematic viewer.
   Two views of the same sheet, sharing one selection:
     schematic  - the real KiCad drawing, pan/zoom, with a clickable box over each part
     graph      - the netlist as a bipartite graph (cytoscape.js): parts and nets are both
                  nodes, because a net joins N pins and an edge only joins 2
   Sheet data is inlined into the page, so this works from file:// as well as over http. */
(function () {
  'use strict';

  var KINDNAME = {res:'Resistor',cap:'Capacitor',dio:'Diode',zen:'Zener diode',
                  tr:'Transistor',ic:'Op amp',dip:'IC',pot:'Potentiometer',
                  sw:'Switch',conn:'Connector',led:'LED',other:'Part'};
  var CLSNAME = {sig:'audio',ctl:'control',pwr:'supply',gnd:'ground'};

  /* Pin and reference designators are numbered, not alphabetical: a plain .sort() gives
     1, 10, 11, 12, 13, 14, 15, 2, 3 ... Compare digit runs as numbers and the rest as text,
     so J1 pin 2 follows pin 1 and C9 follows C8. */
  function natCmp(a, b) {
    var ra = String(a).match(/\d+|\D+/g) || [], rb = String(b).match(/\d+|\D+/g) || [];
    for (var i = 0; i < Math.min(ra.length, rb.length); i++) {
      var x = ra[i], y = rb[i], nx = /^\d/.test(x), ny = /^\d/.test(y);
      if (nx && ny) { var d = parseInt(x, 10) - parseInt(y, 10); if (d) return d; }
      else if (x !== y) return x < y ? -1 : 1;
    }
    return ra.length - rb.length;
  }


  /* Schematic glyphs. Drawn as SVG data URIs so cytoscape nodes look like parts rather
     than boxes. Stroke colour is chosen once from the active theme. */
  function glyphSet(ink) {
    function uri(w, h, body) {
      // width/height must be explicit: without them some engines refuse to rasterise
      // an SVG data URI used as an image, and the node silently renders empty
      return 'data:image/svg+xml;utf8,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + w * 3 + '" height="' + h * 3 +
        '" viewBox="0 0 ' + w + ' ' + h + '">' +
        '<g fill="none" stroke="' + ink + '" stroke-width="1.6" stroke-linecap="round" ' +
        'stroke-linejoin="round">' + body + '</g></svg>');
    }
    return {
      res:  uri(48, 20, '<path d="M0 10h9"/><rect x="9" y="4" width="30" height="12"/><path d="M39 10h9"/>'),
      cap:  uri(48, 20, '<path d="M0 10h20M20 3v14M28 3v14M28 10h20"/>'),
      dio:  uri(48, 20, '<path d="M0 10h16M32 10h16M32 4v12"/><path d="M16 4v12l16-6z" fill="' + ink + '"/>'),
      led:  uri(48, 22, '<path d="M0 12h16M32 12h16M32 6v12"/><path d="M16 6v12l16-6z" fill="' + ink + '"/><path d="M22 5l4-4M28 5l4-4"/>'),
      zen:  uri(48, 20, '<path d="M0 10h16M32 10h16M32 4v12M32 4l-4-3M32 16l4 3"/><path d="M16 4v12l16-6z" fill="' + ink + '"/>'),
      tr:   uri(40, 40, '<circle cx="20" cy="20" r="15"/><path d="M4 20h10M14 12v16M14 17l12-8M14 23l12 8"/><path d="M22 26l5 4-6 1z" fill="' + ink + '"/>'),
      ic:   uri(44, 36, '<path d="M6 4v28l26-14z"/><path d="M0 11h6M0 25h6M32 18h8"/>'),
      pot:  uri(48, 26, '<path d="M0 16h9"/><rect x="9" y="10" width="30" height="12"/><path d="M39 16h9M24 10V2"/><path d="M20 2h8l-4 6z" fill="' + ink + '"/>'),
      sw:   uri(48, 22, '<path d="M0 16h10M38 16h10"/><circle cx="11" cy="16" r="2.2" fill="' + ink + '"/><circle cx="37" cy="16" r="2.2" fill="' + ink + '"/><path d="M11 16L35 5"/>'),
      conn: uri(34, 44, '<rect x="8" y="3" width="18" height="38" rx="2"/><path d="M0 11h8M0 22h8M0 33h8"/>'),
      dip:  uri(46, 34, '<rect x="8" y="3" width="30" height="28" rx="1"/><path d="M0 9h8M0 17h8M0 25h8M38 9h8M38 17h8M38 25h8"/><path d="M19 3a4 4 0 0 0 8 0"/>'),
      other:uri(44, 22, '<rect x="4" y="4" width="36" height="14" rx="2"/>'),
      gnd:  uri(28, 26, '<path d="M14 0v9M2 9h24M6 15h16M10 21h8"/>'),
      rail: uri(24, 26, '<path d="M12 26V6"/><path d="M4 8l8-8 8 8z" fill="' + ink + '"/>')
    };
  }

  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined) n.textContent = txt;
    return n;
  }

  function build(root) {
    var data = JSON.parse(root.querySelector('script[type="application/json"]').textContent);
    var byRef = {}, byNet = {};
    data.components.forEach(function (c) { byRef[c.ref] = c; });
    data.nets.forEach(function (n) { byNet[n.name] = n; });

    var ui = root.querySelector('.iv-body');
    var pane = el('div', 'iv-pane');
    var stage = el('div', 'iv-stage');
    var img = el('img', 'iv-img');
    img.src = 'img/' + data.sheet + '.svg';
    img.alt = data.sheet + ' schematic';
    var ov = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    ov.setAttribute('class', 'iv-ov');
    ov.setAttribute('viewBox', '0 0 ' + data.w + ' ' + data.h);
    ov.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    stage.appendChild(img); stage.appendChild(ov); pane.appendChild(stage);

    var graphPane = el('div', 'iv-pane iv-hide');
    var cyBox = el('div', 'iv-cy');
    graphPane.appendChild(cyBox);

    var panel = el('aside', 'iv-panel');
    ui.appendChild(pane); ui.appendChild(graphPane); ui.appendChild(panel);

    /* ---------- hotspots ---------- */
    var hot = {};
    data.components.forEach(function (c) {
      if (!c.box) return;
      var r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      r.setAttribute('x', c.box[0]); r.setAttribute('y', c.box[1]);
      r.setAttribute('width', c.box[2]); r.setAttribute('height', c.box[3]);
      r.setAttribute('rx', 1); r.setAttribute('class', 'iv-hot');
      r.addEventListener('click', function (e) { e.stopPropagation(); selectComp(c.ref); });
      r.addEventListener('mouseenter', function () { r.classList.add('hover'); });
      r.addEventListener('mouseleave', function () { r.classList.remove('hover'); });
      var t = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      t.textContent = c.ref + '  ' + (c.value || '');
      r.appendChild(t);
      ov.appendChild(r); hot[c.ref] = r;
    });
    ov.addEventListener('click', function () { clearSel(); });

    /* ---------- pan and zoom ---------- */
    var z = 1, tx = 0, ty = 0, drag = null;
    function apply() { stage.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + z + ')'; }
    function zoomTo(nz, cx, cy) {
      nz = Math.max(0.5, Math.min(8, nz));
      var rect = pane.getBoundingClientRect();
      var px = (cx - rect.left - tx) / z, py = (cy - rect.top - ty) / z;
      tx = cx - rect.left - px * nz; ty = cy - rect.top - py * nz; z = nz; apply();
    }
    pane.addEventListener('wheel', function (e) {
      e.preventDefault(); zoomTo(z * (e.deltaY < 0 ? 1.15 : 1 / 1.15), e.clientX, e.clientY);
    }, {passive: false});
    pane.addEventListener('pointerdown', function (e) {
      if (e.target.classList.contains('iv-hot')) return;
      drag = {x: e.clientX - tx, y: e.clientY - ty}; pane.setPointerCapture(e.pointerId);
      pane.classList.add('grabbing');
    });
    pane.addEventListener('pointermove', function (e) {
      if (!drag) return; tx = e.clientX - drag.x; ty = e.clientY - drag.y; apply();
    });
    ['pointerup', 'pointercancel'].forEach(function (ev) {
      pane.addEventListener(ev, function () { drag = null; pane.classList.remove('grabbing'); });
    });
    function reset() { z = 1; tx = 0; ty = 0; apply(); }

    /* ---------- detail panel ---------- */
    function netChip(name) {
      var n = byNet[name] || {cls: 'sig', pins: [], offsheet: 0};
      var b = el('button', 'iv-chip ' + n.cls, name);
      b.addEventListener('click', function () { selectNet(name); });
      return b;
    }
    function clearSel() {
      Object.keys(hot).forEach(function (k) { hot[k].classList.remove('sel', 'rel'); });
      if (cy) cy.elements().removeClass('sel rel dim soft trace');
      showTrace(null);
      panel.innerHTML = '';
      panel.appendChild(el('p', 'iv-hint',
        'Click a part on the schematic, or a node in the connections view. ' +
        'Scroll to zoom, drag to pan.'));
    }
    function selectComp(ref) {
      var c = byRef[ref]; if (!c) return;
      Object.keys(hot).forEach(function (k) { hot[k].classList.remove('sel', 'rel'); });
      if (hot[ref]) hot[ref].classList.add('sel');
      var nets = Object.keys(c.pins).map(function (p) { return c.pins[p]; });
      nets.forEach(function (nm) {
        (byNet[nm] ? byNet[nm].pins : []).forEach(function (pp) {
          if (pp[0] !== ref && hot[pp[0]]) hot[pp[0]].classList.add('rel');
        });
      });
      panel.innerHTML = '';
      panel.appendChild(el('h5', null, c.ref));
      panel.appendChild(el('div', 'iv-val', c.value || ''));
      var meta = el('dl', 'iv-meta');
      [['Type', KINDNAME[c.kind] || 'Part'], ['Footprint', c.fp || '—']].forEach(function (kv) {
        meta.appendChild(el('dt', null, kv[0])); meta.appendChild(el('dd', null, kv[1]));
      });
      panel.appendChild(meta);
      if (c.note) panel.appendChild(el('p', 'iv-note', c.note));
      panel.appendChild(el('h6', null, 'Connections'));
      var ul = el('ul', 'iv-pins');
      Object.keys(c.pins).sort(natCmp).forEach(function (p) {
        var li = el('li');
        li.appendChild(el('span', 'iv-pin', 'pin ' + p));
        li.appendChild(netChip(c.pins[p]));
        ul.appendChild(li);
      });
      panel.appendChild(ul);
      if (cy) {
        cy.elements().removeClass('sel rel').addClass('dim');
        var n = cy.$('#c_' + ref);
        n.removeClass('dim').addClass('sel');
        n.connectedEdges().removeClass('dim').addClass('trace')
         .connectedNodes().removeClass('dim');
      }
    }
    function selectNet(name) {
      var n = byNet[name]; if (!n) return;
      Object.keys(hot).forEach(function (k) { hot[k].classList.remove('sel', 'rel'); });
      n.pins.forEach(function (p) { if (hot[p[0]]) hot[p[0]].classList.add('rel'); });
      panel.innerHTML = '';
      panel.appendChild(el('h5', null, name));
      panel.appendChild(el('div', 'iv-val', (CLSNAME[n.cls] || 'audio') + ' net'));
      panel.appendChild(el('h6', null, 'Reaches ' + n.pins.length + ' pin' +
        (n.pins.length === 1 ? '' : 's') + ' on this sheet'));
      var ul = el('ul', 'iv-pins');
      n.pins.forEach(function (p) {
        var li = el('li');
        var b = el('button', 'iv-chip', p[0]);
        b.addEventListener('click', function () { selectComp(p[0]); });
        li.appendChild(b);
        li.appendChild(el('span', 'iv-pin', 'pin ' + p[1]));
        ul.appendChild(li);
      });
      panel.appendChild(ul);
      if (n.offsheet) panel.appendChild(el('p', 'iv-note',
        'Also reaches ' + n.offsheet + ' pin' + (n.offsheet === 1 ? '' : 's') +
        ' on other sheets.'));
      if (cy) {
        cy.elements().removeClass('sel rel').addClass('dim');
        var es = cy.edges().filter(function (e) { return e.data('net') === name; });
        es.removeClass('dim').addClass('trace').connectedNodes().removeClass('dim');
        cy.nodes().filter(function (nd) {
          return nd.data('label') === name && nd.data('t') !== 'c';
        }).removeClass('dim').addClass('sel');
      }
    }

    /* ---------- graph ----------
       Drawn the way a schematic is, not as a plain netlist dump:
         * power and ground get their own glyph per pin, exactly like a real drawing,
           instead of one hub node with thirty wires fanning out of it
         * a two-pin net is just a wire between the parts
         * a net with three or more pins gets a junction dot
       That, plus orthogonal wires and real part symbols, is most of the difference. */
    var cy = null, layoutName = null;

    /* Layered grid placement.

       Force layouts look organic and overlap constantly - nodes land on each other, labels
       collide, and wires run through parts. This places every node in its own cell on a
       grid instead, so overlap is impossible by construction rather than by luck:

         1. split the graph into connected pieces (a sheet is often several)
         2. rank each piece by breadth-first distance from its best-connected node -> column
         3. order nodes within a column by the average row of their neighbours (a couple of
            barycentre sweeps), which pulls connected things level and cuts crossings
         4. one node per cell, cells sized from the widest label actually rendered

       Column gutters are then free space, which is where the taxi wires do their vertical
       runs - so wires stay out of the parts too. */
    var layoutName = null, lastColw = 168;

    function layered(cy) {
      var adj = {}, deg = {};
      cy.nodes().forEach(function (n) { adj[n.id()] = []; deg[n.id()] = 0; });
      cy.edges().forEach(function (e) {
        var a = e.source().id(), b = e.target().id();
        if (a === b) return;
        adj[a].push(b); adj[b].push(a); deg[a]++; deg[b]++;
      });

      var seen = {}, placed = {}, rowTop = 0;
      var ids = cy.nodes().map(function (n) { return n.id(); });
      ids.sort(function (a, b) { return deg[b] - deg[a]; });

      ids.forEach(function (start) {
        if (seen[start]) return;
        // breadth-first ranks for this connected piece
        var rank = {}, q = [start], layers = [];
        seen[start] = true; rank[start] = 0;
        while (q.length) {
          var id = q.shift();
          (layers[rank[id]] = layers[rank[id]] || []).push(id);
          adj[id].forEach(function (nb) {
            if (seen[nb]) return;
            seen[nb] = true; rank[nb] = rank[id] + 1; q.push(nb);
          });
        }
        // barycentre sweeps to line connected nodes up and cut crossings
        var row = {};
        layers.forEach(function (L) { L.forEach(function (id, i) { row[id] = i; }); });
        for (var pass = 0; pass < 4; pass++) {
          var fwd = pass % 2 === 0;
          for (var li = 0; li < layers.length; li++) {
            var L = layers[fwd ? li : layers.length - 1 - li];
            L.sort(function (a, b) {
              function bary(id) {
                var ns = adj[id].filter(function (x) { return rank[x] !== undefined && rank[x] !== rank[id]; });
                if (!ns.length) return row[id];
                var t = 0; ns.forEach(function (x) { t += row[x]; });
                return t / ns.length;
              }
              return bary(a) - bary(b);
            });
            L.forEach(function (id, i) { row[id] = i; });
          }
        }
        var tall = 0;
        layers.forEach(function (L) { tall = Math.max(tall, L.length); });
        layers.forEach(function (L, col) {
          var pad = (tall - L.length) / 2;               // centre short columns
          L.forEach(function (id, i) {
            placed[id] = {col: col, row: rowTop + pad + i};
          });
        });
        rowTop += tall + 1;                              // blank row between pieces
      });
      return placed;
    }

    function applyGrid(cy, colw, rowh) {
      var g = layered(cy);
      cy.nodes().forEach(function (n) {
        var p = g[n.id()] || {col: 0, row: 0};
        n.position({x: p.col * colw, y: p.row * rowh});
      });
    }

    /* Measure what actually rendered, including labels, and report any collisions.
       Used to grow the spacing until there are none. */
    function overlaps(cy) {
      var bs = cy.nodes().map(function (n) {
        var b = n.boundingBox({includeLabels: true, includeOverlays: false});
        return {id: n.id(), x1: b.x1, y1: b.y1, x2: b.x2, y2: b.y2};
      });
      var hits = 0;
      for (var i = 0; i < bs.length; i++)
        for (var j = i + 1; j < bs.length; j++)
          if (bs[i].x1 < bs[j].x2 && bs[j].x1 < bs[i].x2 &&
              bs[i].y1 < bs[j].y2 && bs[j].y1 < bs[i].y2) hits++;
      return hits;
    }

    function fitReadable() {
      if (!cy) return;
      var box = cyBox.getBoundingClientRect();
      if (box.width < 40 || box.height < 40) {     // pane not laid out yet, try again
        setTimeout(fitReadable, 60);
        return;
      }
      cy.resize();
      cy.fit(cy.elements(), 26);
      // Show the whole sheet by default - that is the point of a layout that cannot
      // overlap. Only clamp when fitting would make it genuinely illegible.
      if (cy.zoom() < 0.26) { cy.zoom(0.26); cy.center(); }
      if (cy.zoom() > 1.6)  { cy.zoom(1.6);  cy.center(); }
    }

    function relayout(name) {
      layoutName = name || layoutName;
      if (!cy) return;
      var tight = layoutName === 'compact';
      var colw = tight ? 128 : 168, rowh = tight ? 70 : 88;
      // grow the cells until nothing collides; labels vary in width so this is measured,
      // not assumed
      for (var tries = 0; tries < 8; tries++) {
        applyGrid(cy, colw, rowh);
        if (overlaps(cy) === 0) break;
        colw = Math.round(colw * 1.14); rowh = Math.round(rowh * 1.10);
      }
      spreadTurns(cy, colw);
      lastColw = colw;
      fitReadable();
    }

    /* Wires turn in the gutters between columns, never over them.

       A horizontal taxi edge runs: out from the source, a vertical run at
       source.x + turn, then in to the target. Locking that turn to the middle of the
       gutter beside the source column keeps every vertical run in empty space, so wires
       cannot cross parts. Fanning the turn a few pixels per edge stops two wires in the
       same gutter drawing the same line twice. */
    function spreadTurns(cy, colw) {
      var lane = {};
      cy.edges().forEach(function (e) {
        var sx = e.source().position('x'), tx = e.target().position('x');
        var gutter = Math.round(sx / colw) * colw + (tx >= sx ? colw / 2 : -colw / 2);
        var key = gutter;
        lane[key] = (lane[key] || 0) + 1;
        var spread = ((lane[key] % 9) - 4) * 7;            // own track within the gutter
        e.data('turn', Math.max(12, Math.abs(gutter - sx) + spread));
      });
    }

    /* Measure wires running over parts, using the same three-segment model the taxi
       style draws. Reported by _ivDebug so the claim can be checked rather than assumed. */
    function edgeNodeHits(cy, colw) {
      var boxes = cy.nodes().map(function (n) {
        var b = n.boundingBox({includeLabels: false});
        return {id: n.id(), x1: b.x1, y1: b.y1, x2: b.x2, y2: b.y2};
      });
      function segHitsBox(ax, ay, bx, by, bo) {
        var lo, hi;
        if (ax === bx) {
          lo = Math.min(ay, by); hi = Math.max(ay, by);
          return ax > bo.x1 && ax < bo.x2 && lo < bo.y2 && hi > bo.y1;
        }
        lo = Math.min(ax, bx); hi = Math.max(ax, bx);
        return ay > bo.y1 && ay < bo.y2 && lo < bo.x2 && hi > bo.x1;
      }
      var hits = 0;
      cy.edges().forEach(function (e) {
        var s = e.source().position(), t = e.target().position();
        var turn = e.data('turn') || colw / 2;
        var vx = t.x >= s.x ? s.x + turn : s.x - turn;
        var segs = [[s.x, s.y, vx, s.y], [vx, s.y, vx, t.y], [vx, t.y, t.x, t.y]];
        boxes.forEach(function (bo) {
          if (bo.id === e.source().id() || bo.id === e.target().id()) return;
          for (var i = 0; i < segs.length; i++) {
            if (segHitsBox(segs[i][0], segs[i][1], segs[i][2], segs[i][3], bo)) { hits++; return; }
          }
        });
      });
      return hits;
    }

    function makeGraph() {
      if (cy || typeof cytoscape === 'undefined') return;
      var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (document.documentElement.dataset.theme === 'light') dark = false;
      if (document.documentElement.dataset.theme === 'dark') dark = true;
      var ink = dark ? '#DFE6E2' : '#16201D';
      var G = glyphSet(ink);
      var wire = dark ? '#7F8B86' : '#5C6862';
      // wires carry the same colour language as the rest of the site, so you can tell
      // at a glance whether you are following audio, control, a rail or a ground
      var NC = dark
        ? {sig: '#E5924F', ctl: '#57BFC2', pwr: '#DE8098', gnd: '#8B978F'}
        : {sig: '#A6501B', ctl: '#1B6A6F', pwr: '#B23A55', gnd: '#5C6862'};
      var paper = dark ? '#161D1B' : '#FFFFFF';

      var els = [], seen = {};
      data.components.forEach(function (c) {
        var g = G[c.kind] || G.other;
        els.push({data: {id: 'c_' + c.ref, label: c.ref,
                         full: c.ref + (c.value ? '\n' + c.value : ''),
                         t: 'c', kind: c.kind, img: g}});
        seen['c_' + c.ref] = true;
      });
      data.nets.forEach(function (n) {
        var pins = n.pins;
        if (n.cls === 'pwr' || n.cls === 'gnd') {
          pins.forEach(function (p, i) {
            var id = 'g_' + n.name + '_' + i;
            els.push({data: {id: id, label: n.name, t: 'g', cls: n.cls,
                             img: n.cls === 'gnd' ? G.gnd : G.rail}});
            els.push({data: {source: 'c_' + p[0], target: id, net: n.name,
                             pin: p[1], cls: n.cls, t: 'e'}});
          });
          return;
        }
        var uniq = {}; pins.forEach(function (p) { uniq[p[0]] = 1; });
        if (pins.length === 2 && Object.keys(uniq).length === 2) {
          els.push({data: {source: 'c_' + pins[0][0], target: 'c_' + pins[1][0],
                           net: n.name, label: n.name, cls: n.cls,
                           sp: pins[0][1], tp: pins[1][1], t: 'w'}});
        } else {
          var id = 'n_' + n.name;
          els.push({data: {id: id, label: n.name, t: 'n', cls: n.cls}});
          pins.forEach(function (p) {
            els.push({data: {source: 'c_' + p[0], target: id, net: n.name,
                             pin: p[1], cls: n.cls, sp: p[1], t: 'e'}});
          });
        }
      });

      cy = cytoscape({
        container: cyBox, elements: els, wheelSensitivity: 0.25,
        style: [
          {selector: 'node[t="c"]', style: {
            'shape': 'rectangle', 'background-opacity': 0,
            'background-image': 'data(img)', 'background-fit': 'contain',
            'background-image-opacity': 1, 'width': 58, 'height': 44,
            'label': 'data(full)', 'text-wrap': 'wrap', 'line-height': 1.15,
            'font-size': 11, 'font-weight': 600,
            'font-family': 'IBM Plex Mono, monospace', 'color': ink,
            'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': 3,
            'text-background-color': paper, 'text-background-opacity': 0.85,
            'text-background-padding': 2}},
          {selector: 'node[t="c"][kind="conn"]', style: {'width': 44, 'height': 58}},
          {selector: 'node[t="c"][kind="ic"]',   style: {'width': 56, 'height': 46}},
          {selector: 'node[t="g"]', style: {
            'shape': 'rectangle', 'background-opacity': 0,
            'background-image': 'data(img)', 'background-fit': 'contain',
            'background-image-opacity': 1, 'width': 28, 'height': 28,
            'label': 'data(label)', 'font-size': 9.5,
            'font-family': 'IBM Plex Mono, monospace', 'color': wire,
            'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': 1}},
          {selector: 'node[t="g"][cls="pwr"]', style: {'text-valign': 'top', 'text-margin-y': -1, 'color': NC.pwr}},
          {selector: 'node[t="n"]', style: {
            'shape': 'ellipse', 'width': 11, 'height': 11, 'background-color': ink,
            'label': 'data(label)', 'font-size': 10, 'font-weight': 600,
            'font-family': 'IBM Plex Mono, monospace', 'color': ink,
            'text-valign': 'top', 'text-halign': 'center', 'text-margin-y': -3,
            'text-background-color': paper, 'text-background-opacity': 0.85,
            'text-background-padding': 2}},
          {selector: 'node[t="n"][cls="ctl"]', style: {'background-color': NC.ctl, 'color': NC.ctl}},
          {selector: 'node[t="n"][cls="sig"]', style: {'background-color': NC.sig, 'color': NC.sig}},
          {selector: 'edge', style: {
            'width': 1.8, 'line-color': wire, 'curve-style': 'taxi',
            'taxi-direction': 'horizontal', 'taxi-turn': 'data(turn)', 'taxi-turn-min-distance': 8,
            'target-arrow-shape': 'none', 'opacity': 0.9,
            'source-label': 'data(sp)', 'source-text-offset': 26,
            'font-size': 8, 'font-family': 'IBM Plex Mono, monospace', 'color': wire,
            'source-text-margin-y': -4}},
          {selector: 'edge[cls="sig"]', style: {'line-color': NC.sig}},
          {selector: 'edge[cls="ctl"]', style: {'line-color': NC.ctl}},
          {selector: 'edge[cls="pwr"]', style: {'line-color': NC.pwr}},
          {selector: 'edge[cls="gnd"]', style: {'line-color': NC.gnd}},
          {selector: 'edge[t="w"]', style: {
            'label': 'data(label)', 'font-size': 9.5, 'font-weight': 600,
            'text-rotation': 'autorotate',
            'text-background-color': paper, 'text-background-opacity': 0.92,
            'text-background-padding': 3, 'target-label': 'data(tp)',
            'target-text-offset': 26, 'target-text-margin-y': -4}},
          {selector: 'edge[t="w"][cls="sig"]', style: {'color': NC.sig}},
          {selector: 'edge[t="w"][cls="ctl"]', style: {'color': NC.ctl}},
          {selector: '.dim', style: {'opacity': 0.10, 'text-opacity': 0.10}},
          {selector: '.soft', style: {'opacity': 0.28, 'text-opacity': 0.28}},
          {selector: '.rel', style: {'opacity': 1, 'text-opacity': 1}},
          {selector: 'node.sel', style: {
            'border-width': 2.5, 'border-color': ink, 'border-opacity': 1,
            'background-opacity': 0.08, 'background-color': ink, 'z-index': 20}},
          {selector: 'edge.trace', style: {
            'width': 4, 'opacity': 1, 'text-opacity': 1, 'z-index': 19,
            'line-style': 'solid'}},
          {selector: 'edge.sel, edge.rel', style: {'width': 3.2, 'opacity': 1, 'z-index': 18}}
        ],
        layout: {name: 'preset'}
      });
      cy.on('tap', 'node', function (e) {
        var d = e.target.data();
        if (d.t === 'c') selectComp(d.label);
        else selectNet(d.label);
      });
      cy.on('tap', 'edge', function (e) { selectNet(e.target.data('net')); });
      cy.on('tap', function (e) { if (e.target === cy) clearSel(); });

      /* Hovering traces without committing: the net under the cursor lights up and
         everything else fades back. Following one wire through a crossing is the thing
         a static picture cannot help you with, so it should not cost a click. */
      function hoverNet(name) {
        cy.batch(function () {
          cy.elements().removeClass('trace').addClass('soft');
          var es = cy.edges().filter(function (x) { return x.data('net') === name; });
          es.removeClass('soft').addClass('trace');
          es.connectedNodes().removeClass('soft');
        });
        showTrace(name);
      }
      function hoverOff() {
        cy.batch(function () { cy.elements().removeClass('soft trace'); });
        showTrace(null);
      }
      cy.on('mouseover', 'edge', function (e) { hoverNet(e.target.data('net')); });
      cy.on('mouseout', 'edge', hoverOff);
      cy.on('mouseover', 'node', function (e) {
        var d = e.target.data();
        if (d.t === 'c') {
          cy.batch(function () {
            cy.elements().removeClass('trace').addClass('soft');
            var n = cy.$('#c_' + d.label);
            n.removeClass('soft');
            n.connectedEdges().removeClass('soft').addClass('trace')
             .connectedNodes().removeClass('soft');
          });
          showTrace(d.label + ' — ' + n_netnames(d.label));
        } else { hoverNet(d.label); }
      });
      cy.on('mouseout', 'node', hoverOff);
    }

    function n_netnames(ref) {
      var c = byRef[ref]; if (!c) return '';
      var seen = {}, out = [];
      Object.keys(c.pins).forEach(function (p) {
        if (!seen[c.pins[p]]) { seen[c.pins[p]] = 1; out.push(c.pins[p]); }
      });
      return out.join(', ');
    }
    var trace = root.querySelector('.iv-trace');
    function showTrace(txt) {
      if (!trace) return;
      trace.textContent = txt || '';
      trace.classList.toggle('on', !!txt);
    }

    /* ---------- toolbar ---------- */
    root.querySelectorAll('.iv-tab').forEach(function (b) {
      b.addEventListener('click', function () {
        root.querySelectorAll('.iv-tab').forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on');
        var g = b.dataset.view === 'graph';
        pane.classList.toggle('iv-hide', g);
        graphPane.classList.toggle('iv-hide', !g);
        if (g) {
          makeGraph();
          // lay out only once the pane is on screen and has a real size
          setTimeout(function () { relayout(layoutName || 'comfortable'); }, 40);
        }
      });
    });
    var zin = root.querySelector('.iv-zin'), zout = root.querySelector('.iv-zout'),
        zres = root.querySelector('.iv-zres'), find = root.querySelector('.iv-find'),
        lay = root.querySelector('.iv-lay');
    if (lay) {
      var order = ['comfortable', 'compact'],
          names = {comfortable: 'Roomy', compact: 'Compact'};
      layoutName = 'comfortable';
      lay.textContent = names[layoutName];
      lay.title = 'Spacing between parts';
      lay.addEventListener('click', function () {
        layoutName = order[(order.indexOf(layoutName) + 1) % order.length];
        lay.textContent = names[layoutName];
        relayout(layoutName);
      });
    }
    function centre() {
      var r = pane.getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2];
    }
    zin.addEventListener('click', function () { var c = centre(); zoomTo(z * 1.3, c[0], c[1]); });
    zout.addEventListener('click', function () { var c = centre(); zoomTo(z / 1.3, c[0], c[1]); });
    zres.addEventListener('click', function () { if (cy && !graphPane.classList.contains('iv-hide')) cy.fit(undefined, 30); else reset(); });
    find.addEventListener('input', function () {
      var q = find.value.trim().toUpperCase();
      if (!q) { clearSel(); return; }
      var c = data.components.filter(function (x) { return x.ref.toUpperCase() === q; })[0];
      if (c) { selectComp(c.ref); return; }
      var n = data.nets.filter(function (x) { return x.name.toUpperCase() === q; })[0];
      if (n) selectNet(n.name);
    });

    clearSel();
    window.__ivRefit = (function (prev) {
      return function () { if (prev) prev(); if (cy) setTimeout(fitReadable, 60); };
    })(window.__ivRefit);
    root._ivDebug = function () {
      return cy ? {nodes: cy.nodes().length, edges: cy.edges().length,
                   nodeOverlaps: overlaps(cy),
                   wiresOverParts: edgeNodeHits(cy, lastColw)} : null;
    };
  }

  /* Width toggle. The stored preference is applied in the page head before paint;
     this only wires up the control and keeps the two in step. */
  function wireWidth() {
    var btn = document.getElementById('wbtn');
    if (!btn) return;
    var root = document.documentElement;
    function paint() {
      var wide = root.dataset.width === 'wide';
      btn.setAttribute('aria-pressed', wide ? 'true' : 'false');
      btn.querySelector('.wbtn-txt').textContent = wide ? 'Narrow layout' : 'Wide layout';
      btn.title = wide ? 'Back to a reading-width column' : 'Use the full window width';
      if (window.__ivRefit) window.__ivRefit();
    }
    btn.addEventListener('click', function () {
      var wide = root.dataset.width === 'wide';
      if (wide) delete root.dataset.width; else root.dataset.width = 'wide';
      try { localStorage.setItem('uts-width', wide ? 'narrow' : 'wide'); } catch (e) {}
      paint();
    });
    paint();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.iv').forEach(build);
    wireWidth();
  });
})();
