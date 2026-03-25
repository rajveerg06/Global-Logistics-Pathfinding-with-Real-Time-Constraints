/**
 * map.js — Leaflet map controller with realistic sea-route waypoints.
 */

const MapController = (() => {

  // ── Internals ─────────────────────────────────────────────────────────
  let _map         = null;
  let _edgeLines   = [];
  let _pathLines   = [];
  let _nodeMarkers = {};
  let _shipMarker  = null;
  let _animFrame   = null;
  let _animRunning = false;

  const MODE_COLOR = { air:'#00d4ff', sea:'#3b82f6', rail:'#f59e0b', road:'#6b7280' };
  const MODE_DASH  = { air:'7,5',     sea:null,       rail:'10,5',    road:'4,4'     };
  const MODE_ICON  = { air:'✈',       sea:'🚢',       rail:'🚂',      road:'🚛'      };

  // ── Sea-route waypoints ──────────────────────────────────────────────
  // Groups of node IDs sharing a corridor characteristic
  const G = {
    EAST_ASIA : ['shanghai','hong_kong','shenzhen','busan','seoul','tokyo','vladivostok'],
    SE_ASIA   : ['singapore','colombo'],
    S_ASIA    : ['mumbai','colombo','karachi'],
    MID_EAST  : ['dubai','karachi'],
    EUROPE    : ['rotterdam','hamburg','antwerp','london'],
    AM_WEST   : ['los_angeles'],
    AM_EAST   : ['new_york','sao_paulo'],
    OCEANIA   : ['sydney'],
    AFRICA    : ['johannesburg'],
  };

  // Key ocean corridor waypoints (lat, lon arrays)
  const WP = {
    // Suez Canal corridor (going west from Asia)
    SUEZ_FWD : [
      [  1.2, 104.0],  // Singapore Strait
      [  5.5,  79.5],  // Sri Lanka south
      [ 11.5,  43.5],  // Bab-el-Mandeb (Red Sea entrance)
      [ 27.0,  33.8],  // Suez Canal
      [ 31.5,  32.3],  // Suez exit Mediterranean
      [ 34.0,  23.0],  // E. Mediterranean
      [ 37.5,  13.5],  // C. Mediterranean (Sicily area)
      [ 36.0,  -5.4],  // Strait of Gibraltar
      [ 44.5,  -8.5],  // Bay of Biscay
    ],
    // Singapore-Dubai (Indian Ocean direct)
    SG_DUBAI : [
      [  5.5,  79.5],  // Sri Lanka south
      [ 10.0,  65.0],  // Arabian Sea centre
    ],
    // Trans-Pacific northerly (Asia → W. Americas)
    PACIFIC_N_FWD : [
      [ 39.0, 155.0],  // East of Japan
      [ 45.0, 175.0],  // NW Pacific
      [ 47.0,-175.0],  // Cross date line
      [ 43.0,-155.0],  // NE Pacific
    ],
    // Trans-Pacific southerly (Oceania → W. Americas)
    PACIFIC_S_FWD : [
      [-28.0, 172.0],  // E. of New Zealand
      [-30.0,-145.0],  // South Pacific
    ],
    // Trans-Atlantic northerly (Europe → E. Americas)
    ATLANTIC_N_FWD : [
      [ 42.0, -22.0],  // Mid-North Atlantic
      [ 38.0, -50.0],  // West North Atlantic
    ],
    // South Atlantic (S. America ↔ Africa/Europe)
    ATLANTIC_S_FWD : [
      [ -8.0, -16.0],  // Equatorial Atlantic
    ],
    // Africa → Europe (east coast of Atlantic)
    AFRICA_EUR_FWD : [
      [-30.0,  18.0],  // Cape region / S. Atlantic
      [-20.0,   5.0],  // South Atlantic
      [  5.0,  -5.0],  // Gulf of Guinea
      [ 25.0, -18.0],  // Canary Islands area
    ],
    // South China Sea (Shanghai → Singapore)
    SCS_FWD : [
      [ 22.0, 114.5],  // Pearl River / HK area
      [ 12.5, 109.5],  // South China Sea centre
      [  4.5, 105.0],  // Near Singapore approach
    ],
    // E. Africa / Indian Ocean (Johannesburg sea - around Cape of Good Hope)
    SA_SUEZ_FWD : [
      [-30.0,  30.5],  // Cape Agulhas / around Cape
      [-20.0,  38.0],  // Mozambique Channel
      [  5.0,  45.0],  // Horn of Africa
      [ 11.5,  43.5],  // Bab-el-Mandeb
      [ 27.0,  33.8],  // Suez Canal
      [ 31.5,  32.3],  // Mediterranean entry
      [ 37.5,  13.5],  // C. Mediterranean
      [ 36.0,  -5.4],  // Gibraltar
      [ 44.5,  -8.5],  // Bay of Biscay
    ],
    // Johannesburg → Sao Paulo (south Atlantic, below Cape)
    SA_SAP_FWD : [
      [-30.0,  20.0],  // Past Cape
      [-35.0,  -5.0],  // Deep South Atlantic
    ],
    // Mumbai ↔ Europe (via Suez, start further north)
    MUM_EUR_FWD : [
      [ 12.0,  44.5],  // Gulf of Aden
      [ 27.0,  33.8],  // Suez
      [ 31.5,  32.3],  // Med entry
      [ 37.5,  13.5],  // C. Mediterranean
      [ 36.0,  -5.4],  // Gibraltar
      [ 44.5,  -8.5],  // Bay of Biscay
    ],
    // Colombo → Rotterdam via Suez
    COL_EUR_FWD : [
      [ 11.5,  43.5],  // Bab-el-Mandeb
      [ 27.0,  33.8],  // Suez
      [ 31.5,  32.3],  // Med entry
      [ 37.5,  13.5],  // C. Mediterranean
      [ 36.0,  -5.4],  // Gibraltar
      [ 44.5,  -8.5],  // Bay of Biscay
    ],
    // Singapore → Sydney (around Australia east side)
    SG_SYD_FWD : [
      [  3.0, 108.0],  // South China Sea / Borneo east
      [ -8.0, 117.0],  // Bali / Lombok Strait
      [-15.0, 130.0],  // Timor Sea
      [-23.0, 148.0],  // Coral Sea / Queensland coast
    ],
    // Los Angeles → Sydney (South Pacific east route)
    LA_SYD_FWD : [
      [ 20.0,-155.0],  // Hawaii area
      [  5.0,-170.0],  // SW Pacific
      [-15.0,-175.0],  // Approaching Fiji
      [-30.0, 170.0],  // West of New Zealand
    ],
    // Vladivostok ↔ Busan (short Sea of Japan)
    VLAD_BUSAN_FWD : [],  // straight is fine (Sea of Japan)
    // Busan ↔ Los Angeles (North Pacific)
    BUSAN_LA_FWD : [
      [ 42.0, 155.0],
      [ 47.0, 175.0],
      [ 47.0,-175.0],
      [ 43.0,-150.0],
    ],
    // New York → São Paulo (south along Americas coast)
    NY_SAP_FWD : [
      [ 25.0, -70.0],  // Bahamas
      [ 10.0, -55.0],  // Caribbean exit
      [  0.0, -48.0],  // Equatorial Atlantic
    ],
  };

  /**
   * Returns an array of [lat, lon] waypoints for sea routes.
   * Returns null if no special routing is needed (straight line OK).
   */
  function getSeaWaypoints(from_id, to_id) {
    const inG = (id, g) => G[g] && G[g].includes(id);

    // Helper: reverse waypoints for opposite direction
    const rev = wp => [...wp].reverse();

    // East Asia → Europe (Suez)
    if (inG(from_id, 'EAST_ASIA') && inG(to_id, 'EUROPE'))
      return WP.SUEZ_FWD;
    if (inG(from_id, 'EUROPE') && inG(to_id, 'EAST_ASIA'))
      return rev(WP.SUEZ_FWD);

    // SE Asia → Europe (Suez, skip first waypoint)
    if ((from_id === 'singapore' || from_id === 'colombo') && inG(to_id, 'EUROPE'))
      return WP.SUEZ_FWD.slice(1);
    if (inG(from_id, 'EUROPE') && (to_id === 'singapore' || to_id === 'colombo'))
      return rev(WP.SUEZ_FWD.slice(1));

    // Mumbai/Karachi → Europe (Suez, start at Aden)
    if ((from_id === 'mumbai' || from_id === 'karachi') && inG(to_id, 'EUROPE'))
      return WP.MUM_EUR_FWD;
    if (inG(from_id, 'EUROPE') && (to_id === 'mumbai' || to_id === 'karachi'))
      return rev(WP.MUM_EUR_FWD);

    // Dubai → Europe (Suez, start at Aden)
    if (from_id === 'dubai' && inG(to_id, 'EUROPE'))
      return WP.MUM_EUR_FWD;
    if (inG(from_id, 'EUROPE') && to_id === 'dubai')
      return rev(WP.MUM_EUR_FWD);

    // Johannesburg → Europe (around Cape + Suez or direct Atlantic)
    if (from_id === 'johannesburg' && inG(to_id, 'EUROPE'))
      return WP.SA_SUEZ_FWD;
    if (inG(from_id, 'EUROPE') && to_id === 'johannesburg')
      return rev(WP.SA_SUEZ_FWD);

    // São Paulo ↔ Europe (South + North Atlantic)
    if (from_id === 'sao_paulo' && inG(to_id, 'EUROPE'))
      return [[...WP.ATLANTIC_S_FWD[0]], [20.0, -22.0], [42.0, -20.0], [44.5, -8.5]];
    if (inG(from_id, 'EUROPE') && to_id === 'sao_paulo')
      return rev([[...WP.ATLANTIC_S_FWD[0]], [20.0, -22.0], [42.0, -20.0], [44.5, -8.5]]);

    // East Asia ↔ W. Americas (Trans-Pacific)
    if (inG(from_id, 'EAST_ASIA') && inG(to_id, 'AM_WEST'))
      return WP.PACIFIC_N_FWD;
    if (inG(from_id, 'AM_WEST') && inG(to_id, 'EAST_ASIA'))
      return rev(WP.PACIFIC_N_FWD);

    // Busan → Los Angeles (similar to east asia)
    if (from_id === 'busan' && to_id === 'los_angeles') return WP.BUSAN_LA_FWD;
    if (from_id === 'los_angeles' && to_id === 'busan')  return rev(WP.BUSAN_LA_FWD);

    // Oceania ↔ W. Americas
    if (from_id === 'sydney' && inG(to_id, 'AM_WEST'))  return WP.PACIFIC_S_FWD;
    if (inG(from_id, 'AM_WEST') && to_id === 'sydney')  return rev(WP.PACIFIC_S_FWD);

    // Oceania ↔ Singapore (up through Indonesia)
    if (from_id === 'sydney' && to_id === 'singapore')   return rev(WP.SG_SYD_FWD);
    if (from_id === 'singapore' && to_id === 'sydney')   return WP.SG_SYD_FWD;

    // W. Americas ↔ Sydney (via South Pacific)
    if (from_id === 'los_angeles' && to_id === 'sydney') return WP.LA_SYD_FWD;
    if (from_id === 'sydney' && to_id === 'los_angeles') return rev(WP.LA_SYD_FWD);

    // Europe ↔ E. Americas (Trans-Atlantic)
    if (inG(from_id, 'EUROPE') && to_id === 'new_york')  return WP.ATLANTIC_N_FWD;
    if (from_id === 'new_york' && inG(to_id, 'EUROPE'))  return rev(WP.ATLANTIC_N_FWD);

    // New York ↔ São Paulo (down Americas coast)
    if (from_id === 'new_york' && to_id === 'sao_paulo') return WP.NY_SAP_FWD;
    if (from_id === 'sao_paulo' && to_id === 'new_york') return rev(WP.NY_SAP_FWD);

    // São Paulo ↔ Johannesburg (South Atlantic)
    if (from_id === 'sao_paulo' && to_id === 'johannesburg') return WP.SA_SAP_FWD;
    if (from_id === 'johannesburg' && to_id === 'sao_paulo') return rev(WP.SA_SAP_FWD);

    // Johannesburg ↔ E. Americas
    if (from_id === 'johannesburg' && inG(to_id, 'AM_EAST')) return rev(WP.SA_SAP_FWD);
    if (inG(from_id, 'AM_EAST') && to_id === 'johannesburg') return WP.SA_SAP_FWD;

    // Africa ↔ Europe (Atlantic coast)
    if (from_id === 'johannesburg' && inG(to_id, 'EUROPE')) return WP.SA_SUEZ_FWD;

    // Singapore ↔ Dubai (Indian Ocean)
    if (from_id === 'singapore' && to_id === 'dubai')    return WP.SG_DUBAI;
    if (from_id === 'dubai' && to_id === 'singapore')    return rev(WP.SG_DUBAI);

    // Singapore ↔ Mumbai (Bay of Bengal / Indian Ocean)
    if (from_id === 'singapore' && to_id === 'mumbai')   return [[5.5, 79.5]];
    if (from_id === 'mumbai' && to_id === 'singapore')   return [[5.5, 79.5]];

    // Colombo ↔ Dubai (Arabian Sea)
    if (from_id === 'colombo' && to_id === 'dubai')      return [[10.5, 62.0]];
    if (from_id === 'dubai' && to_id === 'colombo')      return [[10.5, 62.0]];

    // Colombo ↔ Rotterdam (Suez)
    if (from_id === 'colombo' && inG(to_id, 'EUROPE'))   return WP.COL_EUR_FWD;
    if (inG(from_id, 'EUROPE') && to_id === 'colombo')   return rev(WP.COL_EUR_FWD);

    // Colombo ↔ Singapore (Bay of Bengal)
    if (from_id === 'colombo' && to_id === 'singapore') return [[5.0, 93.0]];
    if (from_id === 'singapore' && to_id === 'colombo') return [[5.0, 93.0]];

    // Karachi ↔ Singapore (Arabian Sea + Indian Ocean)
    if (from_id === 'karachi' && to_id === 'singapore')  return [[5.5, 79.5], [4.0, 93.0]];
    if (from_id === 'singapore' && to_id === 'karachi')  return [[4.0, 93.0], [5.5, 79.5]];

    // Shanghai ↔ Singapore (South China Sea)
    if (from_id === 'shanghai' && to_id === 'singapore') return WP.SCS_FWD;
    if (from_id === 'singapore' && to_id === 'shanghai') return rev(WP.SCS_FWD);

    // Hong Kong ↔ Singapore (South China Sea)
    if (from_id === 'hong_kong' && to_id === 'singapore') return [[15.0, 112.0], [4.5, 105.0]];
    if (from_id === 'singapore' && to_id === 'hong_kong') return [[4.5, 105.0], [15.0, 112.0]];

    // Mumbai ↔ Dubai (Arabian Sea — short, OK with small bend)
    if ((from_id === 'mumbai' && to_id === 'dubai') ||
        (from_id === 'dubai'  && to_id === 'mumbai'))   return [[15.0, 65.0]];

    // Mumbai ↔ Rotterdam (via Suez)
    if (from_id === 'mumbai' && inG(to_id, 'EUROPE'))   return WP.MUM_EUR_FWD;
    if (inG(from_id, 'EUROPE') && to_id === 'mumbai')   return rev(WP.MUM_EUR_FWD);

    // Rotterdam ↔ São Paulo (south Atlantic)  
    if ((inG(from_id, 'EUROPE') && to_id === 'sao_paulo') ||
        (from_id === 'sao_paulo' && inG(to_id, 'EUROPE')))
      return [[42.0, -20.0], [20.0, -22.0], [-6.0, -20.0]];

    // No waypoints needed
    return null;
  }

  // ── Build lat/lon path (with waypoints) ──────────────────────────────
  function buildLatLngs(from_lat, from_lon, to_lat, to_lon, from_id, to_id, mode) {
    const src = [from_lat, from_lon];
    const dst = [to_lat,   to_lon  ];
    if (mode !== 'sea') return [src, dst];
    const wp = getSeaWaypoints(from_id, to_id);
    if (!wp || !wp.length) return [src, dst];
    return [src, ...wp, dst];
  }

  // ── Init ──────────────────────────────────────────────────────────────
  function init() {
    _map = L.map('map', {
      center: [20, 15], zoom: 2,
      minZoom: 2, maxZoom: 8,
      worldCopyJump: true,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd', maxZoom: 19,
    }).addTo(_map);

    return _map;
  }

  // ── Render graph ─────────────────────────────────────────────────────
  function renderGraph(graphData) {
    const nodeById = Object.fromEntries(graphData.nodes.map(n => [n.id, n]));
    const edgeGroup = L.layerGroup().addTo(_map);

    graphData.edges.forEach(e => {
      const from = nodeById[e.from];
      const to   = nodeById[e.to];
      if (!from || !to) return;

      const color   = MODE_COLOR[e.mode] || '#ffffff';
      const dashArr = MODE_DASH[e.mode]  || null;
      const latlngs = buildLatLngs(from.lat, from.lon, to.lat, to.lon, e.from, e.to, e.mode);

      L.polyline(latlngs, { color, weight: 1.2, opacity: 0.22, dashArray: dashArr })
        .addTo(edgeGroup);
      _edgeLines.push(edgeGroup);
    });

    // Markers
    graphData.nodes.forEach(node => {
      const isPort = node.type === 'port';
      const color  = isPort ? '#00d4ff' : '#8b5cf6';
      const icon = L.divIcon({
        className: '',
        html: `<div style="width:13px;height:13px;border-radius:50%;background:${color}33;border:2px solid ${color};box-shadow:0 0 8px ${color}88;cursor:pointer;"></div>`,
        iconSize: [13,13], iconAnchor: [6,6],
      });
      const marker = L.marker([node.lat, node.lon], { icon });
      marker.bindPopup(_popup(node), { maxWidth: 220 });
      marker.on('click', () => marker.openPopup());
      marker.addTo(_map);
      _nodeMarkers[node.id] = { marker, color };
    });
  }

  function _popup(node) {
    return `<div style="font-family:'Outfit',sans-serif;padding:4px;">
      <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:4px;">${node.name}</div>
      <div style="font-size:11px;color:#94a3b8;">
        <span style="background:rgba(255,255,255,0.07);padding:2px 7px;border-radius:10px;margin-right:4px;">${node.type.toUpperCase()}</span>
        ${node.country_name}
      </div>
      <div style="font-size:10px;color:#475569;margin-top:5px;font-family:'JetBrains Mono',monospace;">${node.lat.toFixed(2)}°, ${node.lon.toFixed(2)}°</div>
    </div>`;
  }

  // ── Highlight path ────────────────────────────────────────────────────
  function highlightPath(segments) {
    _pathLines.forEach(l => _map.removeLayer(l));
    _pathLines = [];

    segments.forEach(seg => {
      const latlngs = buildLatLngs(
        seg.from_lat, seg.from_lon,
        seg.to_lat,   seg.to_lon,
        seg.from,     seg.to,
        seg.mode
      );

      // Glow layer
      const glow = L.polyline(latlngs, { color:'#00d4ff', weight: 8, opacity: 0.15 }).addTo(_map);
      // Main line
      const line = L.polyline(latlngs, {
        color:'#00d4ff', weight: 3, opacity: 0.95,
        dashArray: seg.mode === 'air' ? '10,6' : null,
      }).addTo(_map);
      _pathLines.push(glow, line);
    });

    if (segments.length) {
      _pulseNode(segments[0].from, '#00d4ff');
      _pulseNode(segments[segments.length - 1].to, '#f59e0b');
    }
  }

  function _pulseNode(nodeId, color) {
    const entry = _nodeMarkers[nodeId];
    if (!entry) return;
    entry.marker.setIcon(L.divIcon({
      className: '',
      html: `<div style="width:18px;height:18px;border-radius:50%;background:${color}44;border:2.5px solid ${color};box-shadow:0 0 18px ${color};"></div>`,
      iconSize: [18,18], iconAnchor: [9,9],
    }));
  }

  // ── Animate shipment ──────────────────────────────────────────────────
  function animateShipment(segments, onComplete) {
    if (_animRunning) stopAnimation();

    // Expand each segment into sub-legs following waypoints
    const legs = [];
    segments.forEach(seg => {
      const latlngs = buildLatLngs(
        seg.from_lat, seg.from_lon,
        seg.to_lat,   seg.to_lon,
        seg.from,     seg.to,
        seg.mode
      );
      for (let i = 0; i < latlngs.length - 1; i++) {
        legs.push({ from: latlngs[i], to: latlngs[i+1], mode: seg.mode });
      }
    });

    const dominant = segments[0]?.mode || 'air';
    const emoji    = MODE_ICON[dominant];

    const shipIcon = L.divIcon({
      className: '',
      html: `<div style="font-size:20px;filter:drop-shadow(0 0 6px #00d4ff);transform:translate(-50%,-50%);">${emoji}</div>`,
      iconSize:[0,0], iconAnchor:[0,0],
    });

    _shipMarker = L.marker(legs[0].from, { icon: shipIcon, zIndexOffset: 1000 }).addTo(_map);
    _animRunning = true;

    let legIdx = 0, t = 0;
    const SPEED = 0.005;

    function step() {
      if (!_animRunning || legIdx >= legs.length) {
        _animRunning = false;
        if (onComplete) onComplete();
        return;
      }
      const leg = legs[legIdx];
      const lat = leg.from[0] + (leg.to[0] - leg.from[0]) * t;
      const lon = leg.from[1] + (leg.to[1] - leg.from[1]) * t;
      _shipMarker.setLatLng([lat, lon]);
      t += SPEED;
      if (t >= 1) { t = 0; legIdx++; }
      _animFrame = requestAnimationFrame(step);
    }
    _animFrame = requestAnimationFrame(step);
  }

  function stopAnimation() {
    _animRunning = false;
    if (_animFrame) cancelAnimationFrame(_animFrame);
    if (_shipMarker) { _map.removeLayer(_shipMarker); _shipMarker = null; }
  }

  function clearPath() {
    stopAnimation();
    _pathLines.forEach(l => _map.removeLayer(l));
    _pathLines = [];
    Object.values(_nodeMarkers).forEach(({ marker, color }) => {
      marker.setIcon(L.divIcon({
        className: '',
        html: `<div style="width:13px;height:13px;border-radius:50%;background:${color}33;border:2px solid ${color};box-shadow:0 0 8px ${color}88;cursor:pointer;"></div>`,
        iconSize: [13,13], iconAnchor: [6,6],
      }));
    });
  }

  function fitPath(segments) {
    if (!segments?.length) return;
    const pts = [];
    segments.forEach(seg => {
      const latlngs = buildLatLngs(seg.from_lat, seg.from_lon, seg.to_lat, seg.to_lon, seg.from, seg.to, seg.mode);
      latlngs.forEach(p => pts.push(p));
    });
    _map.fitBounds(L.latLngBounds(pts), { padding:[60,60], maxZoom:6 });
  }

  return { init, renderGraph, highlightPath, animateShipment, stopAnimation, clearPath, fitPath };

})();
