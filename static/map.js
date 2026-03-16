/**
 * map.js — Leaflet.js map controller for LogistiPath.
 */

const MapController = (() => {
  // ── Internals ────────────────────────────────────────────────────────────
  let _map = null;
  let _nodeMarkers  = {};      // node_id → Leaflet marker
  let _edgeLines    = [];      // all edge polylines
  let _pathLines    = [];      // highlighted optimal route polylines
  let _shipMarker   = null;    // animated shipment marker
  let _animFrame    = null;    // requestAnimationFrame ID
  let _animRunning  = false;

  // Mode colours (edge colours)
  const MODE_COLOR = { air: '#00d4ff', sea: '#3b82f6', rail: '#f59e0b', road: '#6b7280' };
  const MODE_DASH  = { air: '6,5',     sea: null,      rail: '10,4',    road: '4,4' };
  const MODE_ICON  = { air: '✈', sea: '🚢', rail: '🚂', road: '🚛' };

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    _map = L.map('map', {
      center: [20, 15],
      zoom: 2,
      zoomControl: true,
      minZoom: 2,
      maxZoom: 8,
      worldCopyJump: true,
    });

    // Dark tile layer (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(_map);

    return _map;
  }

  // ── Render graph ─────────────────────────────────────────────────────────
  function renderGraph(graphData) {
    // Draw edges first (below markers)
    const edgeGroup = L.layerGroup().addTo(_map);

    graphData.edges.forEach(e => {
      const from = graphData.nodes.find(n => n.id === e.from);
      const to   = graphData.nodes.find(n => n.id === e.to);
      if (!from || !to) return;

      const color   = MODE_COLOR[e.mode] || '#ffffff';
      const dashArr = MODE_DASH[e.mode]  || null;
      const line = L.polyline(
        [[from.lat, from.lon], [to.lat, to.lon]],
        { color, weight: 1, opacity: 0.22, dashArray: dashArr }
      );
      line.addTo(edgeGroup);
      _edgeLines.push(line);
    });

    // Draw node markers
    graphData.nodes.forEach(node => {
      const isPort = node.type === 'port';
      const color  = isPort ? '#00d4ff' : '#8b5cf6';
      const icon = L.divIcon({
        className: '',
        html: `
          <div style="
            width:14px; height:14px;
            border-radius:50%;
            background:${color}33;
            border:2px solid ${color};
            box-shadow:0 0 8px ${color}88;
            cursor:pointer;
          "></div>`,
        iconSize:   [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([node.lat, node.lon], { icon });
      marker.bindPopup(_nodePopup(node), { maxWidth: 220 });
      marker.on('click', () => marker.openPopup());
      marker.addTo(_map);
      _nodeMarkers[node.id] = marker;
    });
  }

  function _nodePopup(node) {
    return `
      <div style="font-family:'Outfit',sans-serif;padding:4px;">
        <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:4px;">${node.name}</div>
        <div style="font-size:11px;color:#94a3b8;">
          <span style="background:rgba(255,255,255,0.07);padding:2px 7px;border-radius:10px;margin-right:4px;">${node.type.toUpperCase()}</span>
          ${node.country_name}
        </div>
        <div style="font-size:10px;color:#475569;margin-top:6px;font-family:'JetBrains Mono',monospace;">
          ${node.lat.toFixed(2)}°, ${node.lon.toFixed(2)}°
        </div>
      </div>`;
  }

  // ── Highlight optimal path ───────────────────────────────────────────────
  function highlightPath(segments) {
    // Clear previous highlight
    _pathLines.forEach(l => _map.removeLayer(l));
    _pathLines = [];

    segments.forEach((seg, i) => {
      const color = MODE_COLOR[seg.mode] || '#00d4ff';

      // Glowing outer line
      const glow = L.polyline(
        [[seg.from_lat, seg.from_lon], [seg.to_lat, seg.to_lon]],
        { color, weight: 7, opacity: 0.18 }
      ).addTo(_map);
      _pathLines.push(glow);

      // Solid inner line
      const line = L.polyline(
        [[seg.from_lat, seg.from_lon], [seg.to_lat, seg.to_lon]],
        { color: '#00d4ff', weight: 3, opacity: 0.9,
          dashArray: seg.mode === 'air' ? '10,6' : null }
      ).addTo(_map);
      _pathLines.push(line);
    });

    // Pulse source & destination markers
    if (segments.length > 0) {
      _pulseMarker(segments[0].from, '#00d4ff');
      _pulseMarker(segments[segments.length - 1].to, '#f59e0b');
    }
  }

  function _pulseMarker(nodeId, color) {
    const m = _nodeMarkers[nodeId];
    if (!m) return;
    const icon = L.divIcon({
      className: '',
      html: `
        <div style="position:relative;">
          <div style="
            width:18px;height:18px;border-radius:50%;
            background:${color}44;border:2.5px solid ${color};
            box-shadow:0 0 16px ${color};
          "></div>
          <div style="
            position:absolute;top:-4px;left:-4px;
            width:26px;height:26px;border-radius:50%;
            border:2px solid ${color};opacity:0.4;
            animation:none;
          "></div>
        </div>`,
      iconSize:   [18, 18],
      iconAnchor: [9, 9],
    });
    m.setIcon(icon);
  }

  // ── Animate shipment ─────────────────────────────────────────────────────
  function animateShipment(segments, onComplete) {
    if (_animRunning) stopAnimation();

    // Determine dominant mode for icon
    const modes = segments.map(s => s.mode);
    const dominant = ['air','sea','rail','road'].find(m => modes.includes(m)) || 'air';
    const emoji    = MODE_ICON[dominant];

    const shipIcon = L.divIcon({
      className: '',
      html: `<div style="
        font-size:20px;
        filter:drop-shadow(0 0 6px #00d4ff);
        transform:translate(-50%,-50%);
        animation:float 1.5s ease-in-out infinite;
        cursor:default;
      ">${emoji}</div>`,
      iconSize:   [0, 0],
      iconAnchor: [0, 0],
    });

    const startPt = segments[0];
    _shipMarker = L.marker([startPt.from_lat, startPt.from_lon], { icon: shipIcon, zIndexOffset: 1000 }).addTo(_map);
    _animRunning = true;

    let segIdx  = 0;
    let t       = 0;                // 0..1 within current segment
    const SPEED = 0.004;            // fraction per frame

    function step() {
      if (!_animRunning || segIdx >= segments.length) {
        _animRunning = false;
        if (onComplete) onComplete();
        return;
      }
      const seg  = segments[segIdx];
      const lat  = seg.from_lat + (seg.to_lat  - seg.from_lat)  * t;
      const lon  = seg.from_lon + (seg.to_lon  - seg.from_lon)  * t;
      _shipMarker.setLatLng([lat, lon]);
      t += SPEED;
      if (t >= 1) { t = 0; segIdx++; }
      _animFrame = requestAnimationFrame(step);
    }

    _animFrame = requestAnimationFrame(step);
  }

  function stopAnimation() {
    _animRunning = false;
    if (_animFrame) cancelAnimationFrame(_animFrame);
    if (_shipMarker) { _map.removeLayer(_shipMarker); _shipMarker = null; }
  }

  // ── Clear highlights ─────────────────────────────────────────────────────
  function clearPath() {
    stopAnimation();
    _pathLines.forEach(l => _map.removeLayer(l));
    _pathLines = [];
    // Reset all markers to default icon
    Object.entries(_nodeMarkers).forEach(([id, m]) => {
      // re-derive type from stored data
      const dotColor = m._fixedColor || '#00d4ff';
      m.setIcon(L.divIcon({
        className: '',
        html: `<div style="
          width:14px;height:14px;border-radius:50%;
          background:${dotColor}33;border:2px solid ${dotColor};
          box-shadow:0 0 8px ${dotColor}88;cursor:pointer;
        "></div>`,
        iconSize: [14,14], iconAnchor: [7,7],
      }));
    });
  }

  // ── Fit map to path ──────────────────────────────────────────────────────
  function fitPath(segments) {
    if (!segments || !segments.length) return;
    const pts = segments.flatMap(s => [
      [s.from_lat, s.from_lon],
      [s.to_lat,   s.to_lon],
    ]);
    _map.fitBounds(L.latLngBounds(pts), { padding: [60, 60], maxZoom: 6 });
  }

  // ── Public API ────────────────────────────────────────────────────────────
  return { init, renderGraph, highlightPath, animateShipment, stopAnimation, clearPath, fitPath };
})();
