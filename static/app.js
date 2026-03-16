/**
 * app.js — Main application controller for LogistiPath.
 * Wires UI → Api → MapController, manages state & events.
 */

// ── State ─────────────────────────────────────────────────────────────────
const State = {
  nodes: [],
  algo: 'dijkstra',
  optimize: 'time',
  lastResult: null,
  animPlaying: false,
  eventCount: 0,
};

// ── DOM refs ──────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const el = {
  sourceSel: $('source-select'),
  destSel: $('dest-select'),
  swapBtn: $('swap-btn'),
  algoToggle: $('algo-toggle'),
  optToggle: $('opt-toggle'),
  findBtn: $('find-btn'),
  weatherNode: $('weather-node'),
  weatherSlider: $('weather-slider'),
  weatherVal: $('weather-val'),
  applyWeather: $('apply-weather'),
  customsNode: $('customs-node'),
  customsSlider: $('customs-slider'),
  customsVal: $('customs-val'),
  applyCustoms: $('apply-customs'),
  randomBtn: $('random-btn'),
  resetBtn: $('reset-btn'),
  chipEdges: $('chip-edges'),
  chipStatus: $('chip-status'),
  drawerHandle: $('drawer-handle'),
  drawerLabel: $('drawer-label'),
  algBadge: $('drawer-alg-badge'),
  resultCards: $('result-cards'),
  resultSegs: $('result-segments'),
  eventList: $('event-list'),
  animBtn: $('animate-btn'),
  activePanel: $('panel-active'),
  activeList: $('active-list'),
  headerClock: $('header-clock'),
};

// ── Clock ─────────────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  el.headerClock.textContent = now.toUTCString().slice(17, 22) + ' UTC';
}
setInterval(tickClock, 1000);
tickClock();

// ── Toggle groups ─────────────────────────────────────────────────────────
function setupToggle(groupEl, onSelect) {
  groupEl.querySelectorAll('.tog').forEach(btn => {
    btn.addEventListener('click', () => {
      groupEl.querySelectorAll('.tog').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      onSelect(btn.dataset.value);
    });
  });
}

// ── Populate node selects ─────────────────────────────────────────────────
function populateSelects(nodes) {
  const sorted = [...nodes].sort((a, b) => a.name.localeCompare(b.name));
  const opts = sorted.map(n =>
    `<option value="${n.id}">${n.name} (${n.country_name})</option>`
  ).join('');
  const placeholder = '<option value="">Select hub…</option>';
  [el.sourceSel, el.destSel, el.weatherNode, el.customsNode].forEach(sel => {
    sel.innerHTML = placeholder + opts;
  });
}

// ── Find Route ────────────────────────────────────────────────────────────
async function findRoute() {
  const src = el.sourceSel.value;
  const dst = el.destSel.value;
  if (!src || !dst) return;

  setStatus('Calculating…', 'warning');
  el.findBtn.disabled = true;
  el.findBtn.innerHTML = '<span class="btn-glyph">⟳</span> Calculating…';

  try {
    const result = await Api.pathfind({
      source: src,
      destination: dst,
      algorithm: State.algo,
      optimize: State.optimize,
    });

    el.findBtn.innerHTML = '<span class="btn-glyph">◈</span> Find Optimal Route';
    el.findBtn.disabled = !(el.sourceSel.value && el.destSel.value);

    if (!result.found) {
      setStatus('No path found', 'danger');
      alert('⚠️ ' + (result.error || 'No path found.'));
      return;
    }

    State.lastResult = result;
    setStatus('Route found ✓', 'success');

    // Map
    MapController.highlightPath(result.segments);
    MapController.fitPath(result.segments);

    // Drawer
    renderResults(result);
    openDrawer();

    // Animate button
    el.animBtn.style.display = 'block';
    el.animBtn.textContent = '▶ Animate Shipment';
    State.animPlaying = false;

    // Refresh events
    refreshEvents();

  } catch (err) {
    console.error(err);
    setStatus('Error', 'danger');
    el.findBtn.innerHTML = '<span class="btn-glyph">◈</span> Find Optimal Route';
    el.findBtn.disabled = !(el.sourceSel.value && el.destSel.value);
  }
}

// ── Render Results ────────────────────────────────────────────────────────
function renderResults(r) {
  // Badge
  el.algBadge.textContent = r.algorithm;

  // Summary cards
  const eta = new Date(Date.now() + r.total_time * 3600 * 1000);
  const etaStr = eta.toUTCString().slice(5, 22);
  el.resultCards.innerHTML = `
    <div class="r-card">
      <div class="r-card-val">${r.total_distance.toLocaleString()} km</div>
      <div class="r-card-sub">Distance</div>
    </div>
    <div class="r-card">
      <div class="r-card-val">${fmtTime(r.total_time)}</div>
      <div class="r-card-sub">Transit Time</div>
    </div>
    <div class="r-card">
      <div class="r-card-val">$${Math.round(r.total_cost).toLocaleString()}</div>
      <div class="r-card-sub">Est. Cost</div>
    </div>
    <div class="r-card">
      <div class="r-card-val">${r.segments.length}</div>
      <div class="r-card-sub">Segments</div>
    </div>
    <div class="r-card" style="min-width:160px">
      <div class="r-card-val" style="font-size:12px">${etaStr}</div>
      <div class="r-card-sub">Arrival ETA (UTC)</div>
    </div>`;

  // Segment table
  const MODE_ICON = { air: '✈', sea: '🚢', rail: '🚂', road: '🚛' };
  const rows = r.segments.map((s, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${s.from_name}</td>
      <td style="color:#475569">→</td>
      <td>${s.to_name}</td>
      <td><span class="mode-badge ${s.mode}">${MODE_ICON[s.mode] || ''} ${s.mode.toUpperCase()}</span></td>
      <td>${s.distance.toLocaleString()} km</td>
      <td>${fmtTime(s.eff_time)}</td>
      <td>$${Math.round(s.eff_cost).toLocaleString()}</td>
    </tr>`).join('');

  el.resultSegs.innerHTML = `
    <table class="seg-table">
      <thead>
        <tr>
          <th>#</th><th>From</th><th></th><th>To</th>
          <th>Mode</th><th>Dist</th><th>Time</th><th>Cost</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function fmtTime(h) {
  if (h < 1) return `${Math.round(h * 60)} min`;
  if (h < 24) return `${h.toFixed(1)} h`;
  const d = Math.floor(h / 24);
  const r = Math.round(h % 24);
  return r > 0 ? `${d}d ${r}h` : `${d}d`;
}

// ── Drawer ────────────────────────────────────────────────────────────────
const drawer = $('results-drawer');
function openDrawer() { drawer.classList.add('drawer-open'); el.drawerLabel.textContent = '▼ Route Results'; }
function closeDrawer() { drawer.classList.remove('drawer-open'); el.drawerLabel.textContent = '▲ Route Results'; }
function toggleDrawer() { drawer.classList.contains('drawer-open') ? closeDrawer() : openDrawer(); }

el.drawerHandle.addEventListener('click', toggleDrawer);
el.drawerHandle.addEventListener('keydown', e => e.key === 'Enter' && toggleDrawer());

// ── Animate Shipment ──────────────────────────────────────────────────────
el.animBtn.addEventListener('click', () => {
  if (!State.lastResult) return;
  if (State.animPlaying) {
    MapController.stopAnimation();
    State.animPlaying = false;
    el.animBtn.textContent = '▶ Animate Shipment';
    return;
  }
  State.animPlaying = true;
  el.animBtn.textContent = '■ Stop Animation';
  MapController.animateShipment(State.lastResult.segments, () => {
    State.animPlaying = false;
    el.animBtn.textContent = '▶ Animate Shipment';
  });
});

// ── Status chip ───────────────────────────────────────────────────────────
function setStatus(msg, kind = 'info') {
  const chip = el.chipStatus;
  chip.textContent = `● ${msg}`;
  chip.className = 'chip';
  if (kind === 'success') chip.style.cssText = 'color:#10b981;border-color:rgba(16,185,129,0.25);';
  else if (kind === 'warning') chip.style.cssText = 'color:#f59e0b;border-color:rgba(245,158,11,0.25);';
  else if (kind === 'danger') chip.style.cssText = 'color:#f43f5e;border-color:rgba(244,63,94,0.25);';
  else chip.style.cssText = 'color:#94a3b8;border-color:rgba(255,255,255,0.08);';
}

// ── Source / Dest selects ─────────────────────────────────────────────────
function onSelectChange() {
  const ok = el.sourceSel.value && el.destSel.value && el.sourceSel.value !== el.destSel.value;
  el.findBtn.disabled = !ok;
}
el.sourceSel.addEventListener('change', onSelectChange);
el.destSel.addEventListener('change', onSelectChange);

el.swapBtn.addEventListener('click', () => {
  const tmp = el.sourceSel.value;
  el.sourceSel.value = el.destSel.value;
  el.destSel.value = tmp;
  onSelectChange();
});

el.findBtn.addEventListener('click', findRoute);

// ── Toggle groups ─────────────────────────────────────────────────────────
setupToggle(el.algoToggle, v => { State.algo = v; });
setupToggle(el.optToggle, v => { State.optimize = v; });

// ── Sliders ───────────────────────────────────────────────────────────────
el.weatherSlider.addEventListener('input', () => {
  el.weatherVal.textContent = parseFloat(el.weatherSlider.value).toFixed(1) + '×';
});
el.customsSlider.addEventListener('input', () => {
  el.customsVal.textContent = el.customsSlider.value + ' h';
});

// ── Constraint buttons ────────────────────────────────────────────────────
el.applyWeather.addEventListener('click', async () => {
  const node = el.weatherNode.value;
  const val = parseFloat(el.weatherSlider.value);
  if (!node) { alert('Please select a hub first.'); return; }
  await Api.setConstraint({ type: 'weather', target: node, value: val });
  refreshEvents();
  updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.applyCustoms.addEventListener('click', async () => {
  const node = el.customsNode.value;
  const val = parseFloat(el.customsSlider.value);
  if (!node) { alert('Please select a hub first.'); return; }
  await Api.setConstraint({ type: 'customs', target: node, value: val });
  refreshEvents();
  updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.randomBtn.addEventListener('click', async () => {
  el.randomBtn.textContent = '⟳ Generating…';
  await Api.randomEvent();
  el.randomBtn.textContent = '⚡ Random Event';
  refreshEvents();
  updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.resetBtn.addEventListener('click', async () => {
  await Api.resetConstraints();
  refreshEvents();
  updateActivePanel();
  el.weatherSlider.value = 1; el.weatherVal.textContent = '1.0×';
  el.customsSlider.value = 0; el.customsVal.textContent = '0 h';
});

// ── Re-route on constraint change ─────────────────────────────────────────
async function rerouteIfNeeded() {
  if (!State.lastResult) return;
  setStatus('Re-routing…', 'warning');
  const src = State.lastResult.path[0];
  const dst = State.lastResult.path[State.lastResult.path.length - 1];
  const result = await Api.pathfind({
    source: src, destination: dst,
    algorithm: State.algo, optimize: State.optimize,
  });
  if (result.found) {
    State.lastResult = result;
    MapController.highlightPath(result.segments);
    renderResults(result);
    setStatus('Re-routed ✓', 'success');
    refreshEvents();
  }
}

// ── Active disruptions panel ──────────────────────────────────────────────
async function updateActivePanel() {
  const state = await Api.getConstraints();
  const items = [];

  Object.entries(state.weather).forEach(([nid, mult]) => {
    const name = State.nodes.find(n => n.id === nid)?.name || nid;
    items.push(`🌪️ Weather at ${name}: ${mult}× delay`);
  });
  Object.entries(state.customs).forEach(([nid, hrs]) => {
    const name = State.nodes.find(n => n.id === nid)?.name || nid;
    items.push(`🛃 Customs at ${name}: +${hrs}h`);
  });

  if (items.length === 0) {
    el.activePanel.style.display = 'none';
  } else {
    el.activePanel.style.display = '';
    el.activeList.innerHTML = items.map(t => `<div class="active-badge">${t}</div>`).join('');
  }
}

// ── Event log refresh ─────────────────────────────────────────────────────
async function refreshEvents() {
  const { events } = await Api.getEvents(25);
  el.eventList.innerHTML = events.map(ev => {
    const t = new Date(ev.timestamp * 1000).toUTCString().slice(17, 22);
    return `<div class="ev-item ${ev.type || 'info'}">
      <div>${ev.message}</div>
      <div class="ev-time">${t} UTC</div>
    </div>`;
  }).join('');
}

// Poll events every 6 seconds
setInterval(refreshEvents, 6000);

// ── Bootstrap ─────────────────────────────────────────────────────────────
async function bootstrap() {
  setStatus('Loading graph…', 'info');
  MapController.init();

  try {
    const graphData = await Api.getGraph();
    State.nodes = graphData.nodes;

    // Store type on markers for later icon reset
    graphData.nodes.forEach(n => {
      n._color = n.type === 'port' ? '#00d4ff' : '#8b5cf6';
    });

    MapController.renderGraph(graphData);
    populateSelects(graphData.nodes);

    el.chipEdges.textContent = `↔ ${graphData.edge_count} Routes`;
    setStatus('Ready', 'success');

    // Seed event log
    await refreshEvents();
  } catch (err) {
    console.error('Bootstrap error:', err);
    setStatus('Connection error', 'danger');
  }
}

bootstrap();
