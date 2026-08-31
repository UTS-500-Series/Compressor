/* Interactive schematic viewer.
   Two views of the same sheet, sharing one selection:
     schematic  - the real KiCad drawing, pan/zoom, with a clickable box over each part
     graph      - the netlist as a bipartite graph (cytoscape.js): parts and nets are both
                  nodes, because a net joins N pins and an edge only joins 2
   Sheet data is inlined into the page, so this works from file:// as well as over http. */
(function () {
  'use strict';

  var KINDNAME = {res:'Resistor',cap:'Capacitor',dio:'Diode',tr:'Transistor',
                  ic:'IC',pot:'Potentiometer',sw:'Switch',conn:'Connector',
                  led:'LED',other:'Part'};
  var CLSNAME = {sig:'audio',ctl:'control',pwr:'supply',gnd:'ground'};

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
      if (cy) cy.elements().removeClass('sel rel dim');
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
      Object.keys(c.pins).sort().forEach(function (p) {
        var li = el('li');
        li.appendChild(el('span', 'iv-pin', 'pin ' + p));
        li.appendChild(netChip(c.pins[p]));
        ul.appendChild(li);
      });
      panel.appendChild(ul);
      if (cy) {
        cy.elements().removeClass('sel rel'); cy.elements().addClass('dim');
        var n = cy.$('#c_' + ref);
        n.removeClass('dim').addClass('sel');
        n.neighborhood().removeClass('dim').addClass('rel');
        n.neighborhood().neighborhood().removeClass('dim');
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
        cy.elements().removeClass('sel rel'); cy.elements().addClass('dim');
        var nd = cy.$('#n_' + CSS.escape(name));
        nd.removeClass('dim').addClass('sel');
        nd.neighborhood().removeClass('dim').addClass('rel');
      }
    }

    /* ---------- graph ---------- */
    var cy = null;
    function makeGraph() {
      if (cy || typeof cytoscape === 'undefined') return;
      var els = [];
      data.components.forEach(function (c) {
        els.push({data: {id: 'c_' + c.ref, label: c.ref, kind: c.kind, t: 'c'}});
      });
      data.nets.forEach(function (n) {
        els.push({data: {id: 'n_' + n.name, label: n.name, cls: n.cls, t: 'n'}});
        n.pins.forEach(function (p) {
          els.push({data: {source: 'c_' + p[0], target: 'n_' + n.name, label: p[1]}});
        });
      });
      cy = cytoscape({
        container: cyBox, elements: els, wheelSensitivity: 0.25,
        style: [
          {selector: 'node[t="c"]', style: {
            'shape': 'round-rectangle', 'label': 'data(label)', 'width': 46, 'height': 26,
            'background-color': '#4C5852', 'color': '#fff', 'font-size': 11,
            'font-family': 'IBM Plex Mono, monospace',
            'text-valign': 'center', 'text-halign': 'center', 'border-width': 0}},
          {selector: 'node[kind="ic"]',  style: {'background-color': '#1B6A6F', 'width': 54}},
          {selector: 'node[kind="tr"]',  style: {'background-color': '#A6501B'}},
          {selector: 'node[kind="pot"]', style: {'background-color': '#6B4C86'}},
          {selector: 'node[kind="conn"]',style: {'background-color': '#2F6B45', 'width': 58}},
          {selector: 'node[t="n"]', style: {
            'shape': 'ellipse', 'label': 'data(label)', 'width': 14, 'height': 14,
            'background-color': '#9AA5A0', 'font-size': 10, 'color': '#8A948F',
            'font-family': 'IBM Plex Mono, monospace',
            'text-valign': 'top', 'text-halign': 'center', 'text-margin-y': -3}},
          {selector: 'node[cls="pwr"]', style: {'background-color': '#C2445F'}},
          {selector: 'node[cls="gnd"]', style: {'background-color': '#5C6862'}},
          {selector: 'node[cls="ctl"]', style: {'background-color': '#1B6A6F'}},
          {selector: 'node[cls="sig"]', style: {'background-color': '#A6501B'}},
          {selector: 'edge', style: {
            'width': 1.2, 'line-color': '#B9C3BE', 'curve-style': 'bezier',
            'target-arrow-shape': 'none'}},
          {selector: '.dim', style: {'opacity': 0.13}},
          {selector: '.rel', style: {'opacity': 1}},
          {selector: 'node.sel', style: {'border-width': 3, 'border-color': '#57BFC2'}},
          {selector: 'edge.rel', style: {'width': 2.4, 'line-color': '#57BFC2', 'opacity': 1}}
        ],
        layout: {name: 'cose', animate: false, nodeRepulsion: 9000,
                 idealEdgeLength: 60, nestingFactor: 0.6, padding: 24}
      });
      cy.on('tap', 'node', function (e) {
        var d = e.target.data();
        if (d.t === 'c') selectComp(d.label); else selectNet(d.label);
      });
      cy.on('tap', function (e) { if (e.target === cy) clearSel(); });
    }

    /* ---------- toolbar ---------- */
    root.querySelectorAll('.iv-tab').forEach(function (b) {
      b.addEventListener('click', function () {
        root.querySelectorAll('.iv-tab').forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on');
        var g = b.dataset.view === 'graph';
        pane.classList.toggle('iv-hide', g);
        graphPane.classList.toggle('iv-hide', !g);
        if (g) { makeGraph(); setTimeout(function () { cy.resize(); cy.fit(undefined, 30); }, 30); }
      });
    });
    var zin = root.querySelector('.iv-zin'), zout = root.querySelector('.iv-zout'),
        zres = root.querySelector('.iv-zres'), find = root.querySelector('.iv-find');
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
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.iv').forEach(build);
  });
})();
