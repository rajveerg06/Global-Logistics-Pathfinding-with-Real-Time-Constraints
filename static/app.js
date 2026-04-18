/**
 * app.js v2 — LogistiPath main controller
 * Features: 210-hub SearchableSelect, Pareto front, ML prediction,
 *           Fleet VRP, Live status, existing route/constraints/events.
 */

// ── SearchableSelect (virtual scroll for 210+ nodes) ──────────────────
class SearchableSelect {
  constructor({ host, placeholder, onChange }) {
    this._val = '';
    this._opts = [];
    this._cb = onChange;
    this._open = false;

    this._wrap = Object.assign(document.createElement('div'), { className: 'ss-wrap' });
    this._input = Object.assign(document.createElement('input'), {
      type: 'text', placeholder, className: 'ss-input', autocomplete: 'off',
    });
    this._arrow = Object.assign(document.createElement('span'), {
      className: 'ss-arrow', textContent: '▾',
    });
    this._list = Object.assign(document.createElement('div'), { className: 'ss-list' });

    this._wrap.append(this._input, this._arrow, this._list);
    host.appendChild(this._wrap);
    this._bindEvents();
  }

  _bindEvents() {
    this._input.addEventListener('focus', () => this._openList());
    this._input.addEventListener('input', () => this._filter(this._input.value));
    this._arrow.addEventListener('mousedown', e => { e.preventDefault(); this._open ? this._closeList() : this._input.focus(); });
    document.addEventListener('click', e => { if (!this._wrap.contains(e.target)) this._closeList(); });
    this._input.addEventListener('keydown', e => {
      if (e.key === 'Escape') this._closeList();
      if (e.key === 'ArrowDown') { const first = this._list.querySelector('.ss-item'); if (first) first.focus(); }
    });
  }

  _openList() {
    this._open = true;
    this._wrap.classList.add('open');
    this._filter(this._input.value);
    this._list.style.display = 'block';
  }

  _closeList() {
    this._open = false;
    this._wrap.classList.remove('open');
    this._list.style.display = 'none';
    const match = this._opts.find(o => o.label === this._input.value);
    if (!match) {
      const cur = this._opts.find(o => o.value === this._val);
      this._input.value = cur ? cur.label : '';
    }
  }

  _filter(q) {
    const lower = q.toLowerCase();
    // Show all matches for 210 hubs
    const visible = q
      ? this._opts.filter(o => o.label.toLowerCase().includes(lower))
      : this._opts;
    this._renderList(visible);
  }

  _renderList(opts) {
    if (!opts.length) {
      this._list.innerHTML = '<div class="ss-empty">No hubs found</div>';
      return;
    }
    this._list.innerHTML = opts.map(o => `
      <div class="ss-item${o.value === this._val ? ' selected' : ''}" data-value="${o.value}" tabindex="0">
        <span class="ss-name">${o.name}</span>
        <span class="ss-meta">
          <span class="ss-type">${o.type}</span>
          <span class="ss-country">${o.country}</span>
        </span>
      </div>`).join('');
    this._list.querySelectorAll('.ss-item').forEach(item => {
      item.addEventListener('mousedown', e => { e.preventDefault(); this._select(item.dataset.value); });
      item.addEventListener('keydown', e => { if (e.key === 'Enter') this._select(item.dataset.value); });
    });
  }

  _select(val) {
    this._val = val;
    const o = this._opts.find(x => x.value === val);
    if (o) this._input.value = o.label;
    this._closeList();
    if (this._cb) this._cb(val);
  }

  populate(nodes) {
    this._opts = nodes.map(n => ({
      value: n.id, name: n.name,
      label: `${n.name} — ${n.country_name}`,
      country: n.country_name, type: n.type,
    }));
  }

  getValue() { return this._val; }
  setValue(v) {
    this._val = v;
    const o = this._opts.find(x => x.value === v);
    this._input.value = o ? o.label : '';
  }
  clear() { this._val = ''; this._input.value = ''; }
}

// ── Presets ───────────────────────────────────────────────────────────
const PRESETS = {
  fastest: { algo: 'astar', optimize: 'time', label: 'Fastest', icon: '⚡' },
  cheapest: { algo: 'dijkstra', optimize: 'cost', label: 'Cheapest', icon: '💲' },
  balanced: { algo: 'dijkstra', optimize: 'time', label: 'Balanced', icon: '⚖' },
  lowrisk: { algo: 'dijkstra', optimize: 'distance', label: 'Safe', icon: '🛡' },
};

// ── State ─────────────────────────────────────────────────────────────
const State = {
  nodes: [], algo: 'dijkstra', optimize: 'time',
  lastResult: null, animPlaying: false,
  srcSS: null, dstSS: null, weatherSS: null, customsSS: null,
  paretoSrcSS: null, paretoDstSS: null,
  paretoDepth: 30,
  paretoFront: [],
  fleetVehicles: [],
  fleetVehicleCounter: 0,
  paretoChart: null,
};

// ── DOM refs ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const el = {
  swapBtn: $('swap-btn'),
  algoToggle: $('algo-toggle'),
  optToggle: $('opt-toggle'),
  findBtn: $('find-btn'),
  weatherSlider: $('weather-slider'),
  weatherVal: $('weather-val'),
  customsSlider: $('customs-slider'),
  customsVal: $('customs-val'),
  applyWeather: $('apply-weather'),
  applyCustoms: $('apply-customs'),
  randomBtn: $('random-btn'),
  resetBtn: $('reset-btn'),
  chipEdges: $('chip-edges'),
  chipHubs: $('chip-hubs'),
  chipStatus: $('chip-status'),
  chipLive: $('chip-live'),
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
  riskBadge: $('risk-badge'),
  timelineWrap: $('timeline-wrap'),
  impactWeather: $('impact-weather'),
  impactCustoms: $('impact-customs'),
  // V2
  mlPanel: $('panel-ml'),
  mlBody: $('ml-prediction-body'),
  mlStatusDot: $('ml-status-dot'),
  mlInlineBadge: $('ml-inline-badge'),
  paretoBtn: $('pareto-btn'),
  paretoResults: $('pareto-results-panel'),
  paretoList: $('pareto-results-list'),
  paretoChart: $('pareto-chart-panel'),
  paretoCount: $('pareto-count-badge'),
  paretoDepth: $('pareto-depth-toggle'),
  fleetAddBtn: $('fleet-add-btn'),
  fleetSolveBtn: $('fleet-solve-btn'),
  fleetList: $('fleet-vehicles-list'),
  fleetResults: $('fleet-results-panel'),
  fleetSummary: $('fleet-summary-cards'),
  fleetVehicles: $('fleet-vehicle-results'),
  liveGrid: $('live-stats-grid'),
  liveModeLabel: $('live-mode-label'),
  liveModeDot: $('live-mode-dot'),
};

// ── Clock ─────────────────────────────────────────────────────────────
(function tickClock() {
  el.headerClock.textContent = new Date().toUTCString().slice(17, 22) + ' UTC';
  setTimeout(tickClock, 1000);
})();

// ── Sidebar Tab Switcher ──────────────────────────────────────────────
document.querySelectorAll('.stab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.stab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const tabId = 'panel-' + btn.dataset.tab + '-tab';
    const panel = $(tabId) || $('panel-' + btn.dataset.tab);
    if (panel) panel.classList.add('active');
  });
});
// Ensure route tab default active
(() => {
  const routeTab = $('panel-route');
  if (routeTab) routeTab.classList.add('active');
})();

// ── Toggle groups ─────────────────────────────────────────────────────
function setupToggle(groupEl, cb) {
  groupEl.querySelectorAll('.tog').forEach(btn => {
    btn.addEventListener('click', () => {
      groupEl.querySelectorAll('.tog').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      cb(btn.dataset.value);
    });
  });
}
function setToggleValue(groupEl, val) {
  groupEl.querySelectorAll('.tog').forEach(b => {
    b.classList.toggle('active', b.dataset.value === val);
  });
}

// ── Presets ───────────────────────────────────────────────────────────
function applyPreset(key) {
  const p = PRESETS[key];
  if (!p) return;
  State.algo = p.algo;
  State.optimize = p.optimize;
  setToggleValue(el.algoToggle, p.algo);
  setToggleValue(el.optToggle, p.optimize);
  document.querySelectorAll('.preset-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.preset === key);
  });
  if (State.srcSS?.getValue() && State.dstSS?.getValue()) findRoute();
}
document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
});

// ── Source / dest change ──────────────────────────────────────────────
function onSelectChange() {
  const ok = State.srcSS?.getValue() && State.dstSS?.getValue() && State.srcSS.getValue() !== State.dstSS.getValue();
  el.findBtn.disabled = !ok;
}

el.swapBtn.addEventListener('click', () => {
  const a = State.srcSS.getValue(), b = State.dstSS.getValue();
  State.srcSS.setValue(b); State.dstSS.setValue(a);
  onSelectChange();
});

el.findBtn.addEventListener('click', findRoute);

// ── Algorithm / optimize toggles ──────────────────────────────────────
setupToggle(el.algoToggle, v => {
  State.algo = v;
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
});
setupToggle(el.optToggle, v => {
  State.optimize = v;
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
});

// ── Pareto depth toggle ───────────────────────────────────────────────
setupToggle(el.paretoDepth, v => { State.paretoDepth = parseInt(v); });

// ── Pathfinding ───────────────────────────────────────────────────────
async function findRoute() {
  const src = State.srcSS?.getValue();
  const dst = State.dstSS?.getValue();
  if (!src || !dst) return;

  setStatus('Calculating…', 'warning');
  el.findBtn.disabled = true;
  el.findBtn.innerHTML = '<span class="btn-glyph">⟳</span> Calculating…';

  try {
    const result = await Api.pathfind({ source: src, destination: dst, algorithm: State.algo, optimize: State.optimize });
    el.findBtn.innerHTML = '<span class="btn-glyph">◈</span> Find Optimal Route';
    el.findBtn.disabled = !(src && dst);

    if (!result.found) {
      setStatus('No path found', 'danger');
      alert('⚠️ ' + (result.error || 'No path found.'));
      return;
    }

    State.lastResult = result;
    setStatus('Route found ✓', 'success');
    MapController.highlightPath(result.segments);
    MapController.fitPath(result.segments);
    renderResults(result);
    openDrawer();

    el.animBtn.style.display = 'block';
    el.animBtn.textContent = '▶ Animate Shipment';
    State.animPlaying = false;
    refreshEvents();
    updateImpactDeltas();

    // Show ML prediction
    if (result.ml_prediction) renderMLPrediction(result.ml_prediction);

  } catch (err) {
    console.error(err);
    setStatus('Error', 'danger');
    el.findBtn.innerHTML = '<span class="btn-glyph">◈</span> Find Optimal Route';
    el.findBtn.disabled = false;
  }
}

// ── ML Prediction rendering ───────────────────────────────────────────
function renderMLPrediction(pred) {
  if (!pred) return;
  const delay = pred.predicted_delay_h || 0;
  const conf = pred.confidence || 0;
  const confClass = conf >= 0.75 ? 'high' : conf >= 0.5 ? 'medium' : 'low';
  const confLabel = conf >= 0.75 ? `${Math.round(conf * 100)}% confident` : conf >= 0.5 ? `${Math.round(conf * 100)}% confident` : 'Low confidence';

  let breakdownHTML = '';
  if (pred.breakdown && Object.keys(pred.breakdown).length) {
    const rows = Object.entries(pred.breakdown).map(([k, v]) =>
      `<div class="ml-breakdown-row"><span>${k.replace(/_/g, ' ')}</span><span>${v}</span></div>`
    ).join('');
    breakdownHTML = `<div class="ml-breakdown">${rows}</div>`;
  }

  el.mlBody.innerHTML = `
    <div class="ml-prediction-row">
      <div>
        <div class="ml-delay-val">+${delay.toFixed(1)}h</div>
        <div class="ml-delay-label">Predicted Extra Delay</div>
      </div>
      <span class="ml-confidence ${confClass}">${confLabel}</span>
    </div>
    ${breakdownHTML}
    <div style="font-size:10px;color:var(--txt-3);text-align:right">
      🤖 ${pred.model_active ? 'GBR model active' : 'Heuristic fallback'}
    </div>`;
  el.mlPanel.style.display = '';

  // Inline badge in drawer handle
  el.mlInlineBadge.textContent = `🤖 +${delay.toFixed(1)}h predicted`;
  el.mlInlineBadge.style.display = '';
}

// ── Render Results ────────────────────────────────────────────────────
function fmtTime(h) {
  if (h < 1) return `${Math.round(h * 60)} min`;
  if (h < 24) return `${h.toFixed(1)} h`;
  const d = Math.floor(h / 24), r = Math.round(h % 24);
  return r ? `${d}d ${r}h` : `${d}d`;
}

function renderResults(r) {
  el.algBadge.textContent = r.algorithm;

  // Risk badge
  const risk = computeRisk(r);
  el.riskBadge.className = `risk-badge ${risk.level}`;
  el.riskBadge.style.display = 'inline-flex';
  el.riskBadge.innerHTML = `${risk.icon} ${risk.label}` +
    (risk.deltaHours > 0 ? ` <span style="font-size:9px;opacity:0.8">+${risk.deltaHours.toFixed(1)}h</span>` : '');

  // Timeline
  renderTimeline(r.segments);

  // Stat cards
  const eta = new Date(Date.now() + r.total_time * 3600000);
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
    <div class="r-card" style="min-width:150px">
      <div class="r-card-val" style="font-size:11px">${eta.toUTCString().slice(5, 22)}</div>
      <div class="r-card-sub">Arrival ETA (UTC)</div>
    </div>`;

  // Segment table
  const MI = { air: '✈', sea: '🚢', rail: '🚂', road: '🚛' };
  const rows = r.segments.map((s, i) => {
    const delayH = (s.eff_time - (s.time || s.eff_time)).toFixed(1);
    const hasDelay = parseFloat(delayH) > 0.05;
    return `<tr>
      <td style="color:var(--txt-3)">${i + 1}</td>
      <td style="color:var(--txt)">${s.from_name}</td>
      <td style="color:var(--txt-3)">→</td>
      <td style="color:var(--txt)">${s.to_name}</td>
      <td><span class="mode-badge ${s.mode}">${MI[s.mode] || ''} ${s.mode.toUpperCase()}</span></td>
      <td>${s.distance.toLocaleString()} km</td>
      <td>${fmtTime(s.eff_time)}</td>
      <td class="delta-cell ${hasDelay ? 'pos' : 'none'}">${hasDelay ? '+' + delayH + 'h' : '—'}</td>
      <td>$${Math.round(s.eff_cost).toLocaleString()}</td>
    </tr>`;
  }).join('');

  el.resultSegs.innerHTML = `
    <table class="seg-table">
      <thead><tr>
        <th>#</th><th>From</th><th></th><th>To</th>
        <th>Mode</th><th>Dist</th><th>Time</th><th>Delay</th><th>Cost</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ── Risk Badge ────────────────────────────────────────────────────────
function computeRisk(r) {
  const baseTime = r.segments.reduce((s, x) => s + (x.time || 0), 0);
  const delta = r.total_time - baseTime;
  const ratio = baseTime > 0 ? delta / baseTime : 0;
  if (ratio < 0.05) return { level: 'low', label: 'Low Risk', icon: '🟢', deltaHours: delta };
  if (ratio < 0.25) return { level: 'medium', label: 'Moderate', icon: '🟡', deltaHours: delta };
  return { level: 'high', label: 'High Risk', icon: '🔴', deltaHours: delta };
}

// ── Timeline ──────────────────────────────────────────────────────────
function renderTimeline(segments) {
  if (!segments?.length) { el.timelineWrap.innerHTML = ''; return; }
  const totalTime = segments.reduce((s, x) => s + x.eff_time, 0);
  const MODE_COLOR = { air: '#00c4ee', sea: '#3b82f6', rail: '#f59e0b', road: '#6b7280' };
  const MODE_ICON = { air: '✈', sea: '🚢', rail: '🚂', road: '🚛' };

  const bars = segments.map(s => {
    const pct = (s.eff_time / totalTime * 100).toFixed(2);
    const color = MODE_COLOR[s.mode] || '#94a3b8';
    const label = fmtTime(s.eff_time);
    const title = `${s.from_name} → ${s.to_name} | ${s.mode.toUpperCase()} | ${label}`;
    return `<div class="tl-seg" style="flex:${pct}" title="${title}" data-bg="${color}">
      <div class="tl-seg-inner">
        <span class="tl-icon">${MODE_ICON[s.mode] || '📦'}</span>
        <div class="tl-texts">
          <span class="tl-time">${label}</span>
          <span class="tl-from">${s.from_name}</span>
        </div>
      </div>
    </div>`;
  }).join('');

  el.timelineWrap.innerHTML = `<div class="timeline-viz">${bars}</div>`;
  el.timelineWrap.querySelectorAll('.tl-seg').forEach(seg => {
    const c = seg.dataset.bg;
    seg.style.background = `linear-gradient(135deg, ${c}cc, ${c}88)`;
  });
}

// ── Impact Delta ──────────────────────────────────────────────────────
function updateImpactDeltas() {
  updateOneDelta('weather');
  updateOneDelta('customs');
}

function updateOneDelta(type) {
  const r = State.lastResult;
  const nodeId = type === 'weather' ? State.weatherSS?.getValue() : State.customsSS?.getValue();
  const el_ = type === 'weather' ? el.impactWeather : el.impactCustoms;
  const slider = type === 'weather' ? el.weatherSlider : el.customsSlider;
  const val = parseFloat(slider.value);

  if (!r || !nodeId) { el_.textContent = ''; el_.className = 'impact-delta'; return; }

  const segs = r.segments.filter(s => s.to === nodeId);
  const onPath = segs.length > 0;

  if (!onPath) {
    el_.textContent = 'Not on route';
    el_.className = 'impact-delta off-path';
    return;
  }

  let extraH = 0, extraCost = 0;
  if (type === 'weather') {
    if (val <= 1) { el_.textContent = ''; return; }
    segs.forEach(s => { extraH += (s.time || 0) * (val - 1); extraCost += (s.cost || 0) * (val - 1); });
  } else {
    extraH = val;
  }

  if (extraH > 0 || extraCost > 0) {
    el_.className = 'impact-delta on-path';
    el_.textContent = `+${fmtTime(extraH)}${extraCost > 0 ? '  +$' + Math.round(extraCost).toLocaleString() : ''}`;
  } else {
    el_.textContent = '';
  }
}

// ── Sliders ───────────────────────────────────────────────────────────
function updateSliderTrack(input) {
  const min = +input.min, max = +input.max, val = +input.value;
  const pct = ((val - min) / (max - min) * 100).toFixed(1);
  input.style.background = `linear-gradient(90deg, var(--cyan) ${pct}%, var(--border) ${pct}%)`;
}

el.weatherSlider.addEventListener('input', () => {
  el.weatherVal.textContent = parseFloat(el.weatherSlider.value).toFixed(1) + '×';
  updateSliderTrack(el.weatherSlider);
  updateOneDelta('weather');
});
el.customsSlider.addEventListener('input', () => {
  el.customsVal.textContent = el.customsSlider.value + ' h';
  updateSliderTrack(el.customsSlider);
  updateOneDelta('customs');
});

// ── Constraint actions ────────────────────────────────────────────────
el.applyWeather.addEventListener('click', async () => {
  const node = State.weatherSS?.getValue();
  const val = parseFloat(el.weatherSlider.value);
  if (!node) { alert('Select a hub first.'); return; }
  await Api.setConstraint({ type: 'weather', target: node, value: val });
  refreshEvents(); updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.applyCustoms.addEventListener('click', async () => {
  const node = State.customsSS?.getValue();
  const val = parseFloat(el.customsSlider.value);
  if (!node) { alert('Select a hub first.'); return; }
  await Api.setConstraint({ type: 'customs', target: node, value: val });
  refreshEvents(); updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.randomBtn.addEventListener('click', async () => {
  el.randomBtn.textContent = '⟳ Generating…';
  await Api.randomEvent();
  el.randomBtn.textContent = '⚡ Random Event';
  refreshEvents(); updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.resetBtn.addEventListener('click', async () => {
  await Api.resetConstraints();
  refreshEvents(); updateActivePanel();
  el.weatherSlider.value = 1; el.weatherVal.textContent = '1.0×'; updateSliderTrack(el.weatherSlider);
  el.customsSlider.value = 0; el.customsVal.textContent = '0 h'; updateSliderTrack(el.customsSlider);
  el.impactWeather.textContent = '';
  el.impactCustoms.textContent = '';
});

// ── Re-route ──────────────────────────────────────────────────────────
async function rerouteIfNeeded() {
  if (!State.lastResult) return;
  setStatus('Re-routing…', 'warning');
  const path = State.lastResult.path;
  const result = await Api.pathfind({
    source: path[0], destination: path[path.length - 1],
    algorithm: State.algo, optimize: State.optimize,
  });
  if (result.found) {
    State.lastResult = result;
    MapController.highlightPath(result.segments);
    renderResults(result);
    setStatus('Re-routed ✓', 'success');
    refreshEvents(); updateImpactDeltas();
    if (result.ml_prediction) renderMLPrediction(result.ml_prediction);
  }
}

// ── Active disruptions panel ──────────────────────────────────────────
async function updateActivePanel() {
  const state = await Api.getConstraints();
  const items = [];
  Object.entries(state.weather).forEach(([id, m]) => {
    const n = State.nodes.find(x => x.id === id);
    items.push(`🌪️ ${n?.name || id}: ${m}× delay`);
  });
  Object.entries(state.customs).forEach(([id, h]) => {
    const n = State.nodes.find(x => x.id === id);
    items.push(`🛃 ${n?.name || id}: +${h}h`);
  });
  el.activePanel.style.display = items.length ? '' : 'none';
  el.activeList.innerHTML = items.map(t => `<div class="active-badge">${t}</div>`).join('');
}

// ── Drawer ────────────────────────────────────────────────────────────
const drawer = $('results-drawer');
function openDrawer() { drawer.classList.add('drawer-open'); el.drawerLabel.textContent = '▼ Route Results'; }
function toggleDrawer() { drawer.classList.contains('drawer-open') ? (drawer.classList.remove('drawer-open'), el.drawerLabel.textContent = '▲ Route Results') : openDrawer(); }
el.drawerHandle.addEventListener('click', toggleDrawer);
el.drawerHandle.addEventListener('keydown', e => e.key === 'Enter' && toggleDrawer());

// ── Animate ───────────────────────────────────────────────────────────
el.animBtn.addEventListener('click', () => {
  if (!State.lastResult) return;
  if (State.animPlaying) {
    MapController.stopAnimation();
    State.animPlaying = false; el.animBtn.textContent = '▶ Animate Shipment'; return;
  }
  State.animPlaying = true; el.animBtn.textContent = '■ Stop Animation';
  MapController.animateShipment(State.lastResult.segments, () => {
    State.animPlaying = false; el.animBtn.textContent = '▶ Animate Shipment';
  });
});

// ── Status chip ───────────────────────────────────────────────────────
function setStatus(msg, kind = 'info') {
  const c = el.chipStatus;
  c.textContent = `● ${msg}`;
  const styles = {
    success: 'color:#34d399;border-color:rgba(16,185,129,0.3);',
    warning: 'color:#fbbf24;border-color:rgba(245,158,11,0.3);',
    danger: 'color:#fb7185;border-color:rgba(244,63,94,0.3);',
    info: 'color:var(--txt-2);border-color:var(--border);',
  };
  c.style.cssText = styles[kind] || styles.info;
}

// ── Event feed ────────────────────────────────────────────────────────
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
setInterval(refreshEvents, 6000);

// ══════════════════════════════════════════════════════════════════════
// PARETO FRONT CONTROLLER
// ══════════════════════════════════════════════════════════════════════
function onParetoSelectChange() {
  const ok = State.paretoSrcSS?.getValue() && State.paretoDstSS?.getValue()
    && State.paretoSrcSS.getValue() !== State.paretoDstSS.getValue();
  el.paretoBtn.disabled = !ok;
}

el.paretoBtn.addEventListener('click', runParetoSearch);

async function runParetoSearch() {
  const src = State.paretoSrcSS?.getValue();
  const dst = State.paretoDstSS?.getValue();
  if (!src || !dst) return;

  el.paretoBtn.disabled = true;
  el.paretoBtn.innerHTML = '<span class="btn-glyph">⟳</span> Computing…';
  el.paretoResults.style.display = 'none';
  el.paretoChart.style.display = 'none';

  // Show computing indicator
  const tmpDiv = document.createElement('div');
  tmpDiv.className = 'computing-overlay';
  tmpDiv.innerHTML = '<div class="spinner"></div> Running Pareto solver…';
  el.paretoList.innerHTML = '';
  el.paretoResults.style.display = '';
  el.paretoList.appendChild(tmpDiv);

  try {
    const result = await Api.paretoFind({ source: src, destination: dst, n_samples: State.paretoDepth });
    el.paretoBtn.innerHTML = '<span class="btn-glyph">⬡</span> Compute Pareto Front';
    el.paretoBtn.disabled = false;

    if (!result.found || !result.pareto_front?.length) {
      el.paretoList.innerHTML = '<div class="ss-empty">No Pareto paths found.</div>';
      return;
    }

    State.paretoFront = result.pareto_front;
    el.paretoCount.textContent = result.count;
    renderParetoResults(result.pareto_front);
    renderParetoChart(result.pareto_front);
    el.paretoChart.style.display = '';
  } catch (e) {
    console.error(e);
    el.paretoBtn.innerHTML = '<span class="btn-glyph">⬡</span> Compute Pareto Front';
    el.paretoBtn.disabled = false;
    el.paretoList.innerHTML = '<div class="ss-empty">Error computing Pareto front.</div>';
  }
}

function renderParetoResults(front) {
  el.paretoList.innerHTML = '';
  front.forEach((sol, i) => {
    const item = document.createElement('div');
    item.className = 'pareto-result-item';
    item.innerHTML = `
      <div class="pareto-item-label">${sol.label || `Route ${i + 1}`}</div>
      <div class="pareto-kpis">
        <div class="pareto-kpi">
          <div class="pareto-kpi-val">${fmtTime(sol.total_time)}</div>
          <div class="pareto-kpi-lbl">Time</div>
        </div>
        <div class="pareto-kpi">
          <div class="pareto-kpi-val">$${Math.round(sol.total_cost / 1000)}K</div>
          <div class="pareto-kpi-lbl">Cost</div>
        </div>
        <div class="pareto-kpi">
          <div class="pareto-kpi-val">${Math.round(sol.total_distance / 1000)}K km</div>
          <div class="pareto-kpi-lbl">Dist</div>
        </div>
      </div>
      <div style="font-size:10px;color:var(--txt-3);font-family:var(--mono)">${sol.path?.length || 0} hubs · ${sol.segments?.length || 0} segments</div>`;
    item.addEventListener('click', () => {
      el.paretoList.querySelectorAll('.pareto-result-item').forEach(x => x.classList.remove('selected'));
      item.classList.add('selected');
      // Show this Pareto solution on map
      if (sol.segments?.length) {
        MapController.highlightPath(sol.segments);
        MapController.fitPath(sol.segments);
      }
    });
    el.paretoList.appendChild(item);
  });
  el.paretoResults.style.display = '';
}

function renderParetoChart(front) {
  const canvas = $('pareto-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  if (State.paretoChart) { State.paretoChart.destroy(); State.paretoChart = null; }

  const data = front.map((s, i) => ({
    x: parseFloat(s.total_time.toFixed(1)),
    y: parseFloat((s.total_cost / 1000).toFixed(1)),
    label: s.label || `R${i + 1}`,
  }));

  State.paretoChart = new Chart(canvas, {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Pareto Front',
        data,
        backgroundColor: data.map((_, i) => `hsla(${180 + i * 30}, 80%, 60%, 0.85)`),
        pointRadius: 7,
        pointHoverRadius: 10,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.raw.label}: ${ctx.raw.x}h · $${ctx.raw.y}K`,
          },
          backgroundColor: 'rgba(7,16,31,0.95)',
          borderColor: 'rgba(0,212,255,0.4)',
          borderWidth: 1,
          titleColor: '#00d4ff',
          bodyColor: '#dde6f0',
        },
      },
      scales: {
        x: {
          title: { display: true, text: 'Time (hours)', color: '#6080a0', font: { size: 10 } },
          grid: { color: 'rgba(255,255,255,0.06)' },
          ticks: { color: '#6080a0', font: { size: 10 } },
        },
        y: {
          title: { display: true, text: 'Cost (K USD)', color: '#6080a0', font: { size: 10 } },
          grid: { color: 'rgba(255,255,255,0.06)' },
          ticks: { color: '#6080a0', font: { size: 10 } },
        },
      },
    }
  });
}

// ══════════════════════════════════════════════════════════════════════
// FLEET ROUTING CONTROLLER
// ══════════════════════════════════════════════════════════════════════
const FLEET_COLORS = ['#f43f5e', '#f59e0b', '#10b981', '#8b5cf6', '#06b6d4'];

function addFleetVehicle() {
  const id = 'V' + (++State.fleetVehicleCounter);
  const card = document.createElement('div');
  card.className = 'fleet-vehicle-card';
  card.dataset.vid = id;
  card.innerHTML = `
    <div class="fleet-vehicle-header">
      <span class="fleet-vehicle-id">🚛 ${id}</span>
      <button class="fleet-remove-btn" title="Remove vehicle">✕</button>
    </div>
    <div class="field-label" style="font-size:9px">Origin Hub</div>
    <div class="ss-host" id="fleet-origin-${id}"></div>
    <div class="field-label" style="font-size:9px;margin-top:4px">Stops (hub IDs, comma-separated)</div>
    <input class="fleet-mini-input fleet-stops-input" placeholder="e.g. rotterdam, hamburg, antwerp" data-role="stops" />
    <div class="field-label" style="font-size:9px;margin-top:4px">Preferred Mode</div>
    <div class="fleet-mode-row">
      ${['any', 'air', 'sea', 'rail'].map(m =>
    `<button class="fleet-mode-btn${m === 'any' ? ' active' : ''}" data-mode="${m}">${m.toUpperCase()}</button>`
  ).join('')}
    </div>`;

  // Remove button
  card.querySelector('.fleet-remove-btn').addEventListener('click', () => {
    card.remove();
    State.fleetVehicles = State.fleetVehicles.filter(v => v.id !== id);
    updateFleetSolveBtn();
  });

  // Mode buttons
  card.querySelectorAll('.fleet-mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      card.querySelectorAll('.fleet-mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  el.fleetList.appendChild(card);

  // Init origin searchable select
  const ss = new SearchableSelect({
    host: $(`fleet-origin-${id}`),
    placeholder: 'Search hub…',
    onChange: () => updateFleetSolveBtn(),
  });
  const sorted = [...State.nodes].sort((a, b) => a.name.localeCompare(b.name));
  ss.populate(sorted);
  State.fleetVehicles.push({ id, ss, card });
  updateFleetSolveBtn();
}

function updateFleetSolveBtn() {
  el.fleetSolveBtn.disabled = State.fleetVehicles.length === 0;
}

el.fleetAddBtn.addEventListener('click', addFleetVehicle);

el.fleetSolveBtn.addEventListener('click', async () => {
  if (State.fleetVehicles.length === 0) return;

  el.fleetSolveBtn.disabled = true;
  el.fleetSolveBtn.innerHTML = '<span class="btn-glyph">⟳</span> Solving…';

  // Build request
  const vehicles = State.fleetVehicles.map(v => {
    const origin = v.ss.getValue();
    const stopsInput = v.card.querySelector('[data-role="stops"]').value;
    const stops = stopsInput.split(',').map(s => s.trim().toLowerCase().replace(/ /g, '_')).filter(Boolean);
    const modeBtn = v.card.querySelector('.fleet-mode-btn.active');
    const mode = modeBtn ? modeBtn.dataset.mode : 'any';
    return { id: v.id, origin, destinations: stops, preferred_mode: mode };
  }).filter(v => v.origin);

  if (!vehicles.length) {
    alert('Please set an origin for at least one vehicle.');
    el.fleetSolveBtn.disabled = false;
    el.fleetSolveBtn.innerHTML = '<span class="btn-glyph">🚛</span> Solve Fleet Routes';
    return;
  }

  try {
    const result = await Api.solveFleet(vehicles);
    el.fleetSolveBtn.innerHTML = '<span class="btn-glyph">🚛</span> Solve Fleet Routes';
    el.fleetSolveBtn.disabled = false;
    renderFleetResults(result);
    // Draw fleet on map
    MapController.renderFleetRoutes(result.vehicles);
  } catch (e) {
    console.error(e);
    el.fleetSolveBtn.innerHTML = '<span class="btn-glyph">🚛</span> Solve Fleet Routes';
    el.fleetSolveBtn.disabled = false;
    alert('Fleet routing failed: ' + e.message);
  }
});

function renderFleetResults(result) {
  const s = result.fleet_summary;
  el.fleetSummary.innerHTML = `
    <div class="fleet-summary-kpi"><div class="fleet-kpi-val">${s.total_vehicles}</div><div class="fleet-kpi-lbl">Vehicles</div></div>
    <div class="fleet-summary-kpi"><div class="fleet-kpi-val">${s.total_stops}</div><div class="fleet-kpi-lbl">Stops</div></div>
    <div class="fleet-summary-kpi"><div class="fleet-kpi-val">${fmtTime(s.fleet_makespan_h)}</div><div class="fleet-kpi-lbl">Makespan</div></div>
    <div class="fleet-summary-kpi"><div class="fleet-kpi-val">$${Math.round((s.fleet_cost_usd || 0) / 1000)}K</div><div class="fleet-kpi-lbl">Total Cost</div></div>
    <div class="fleet-summary-kpi"><div class="fleet-kpi-val">+${(s.fleet_ml_delay_h || 0).toFixed(1)}h</div><div class="fleet-kpi-lbl">ML Delay</div></div>`;

  el.fleetVehicles.innerHTML = '';
  result.vehicles.forEach((v, idx) => {
    const color = FLEET_COLORS[idx % FLEET_COLORS.length];
    const route = (v.route_sequence || []).join(' → ');
    const legsHTML = (v.legs || []).map(leg => `
      <div class="fleet-leg-row">
        <span>${leg.from_name || leg.from}</span>
        <span class="fleet-leg-arrow">→</span>
        <span>${leg.to_name || leg.to}</span>
        <span class="fleet-leg-mode"><span class="mode-badge ${leg.segments?.[0]?.mode || 'sea'}">${leg.segments?.[0]?.mode?.toUpperCase() || 'SEA'}</span></span>
        <span style="margin-left:4px;font-size:10px;color:var(--txt-3)">${fmtTime(leg.time_h || 0)}</span>
      </div>`).join('');

    const div = document.createElement('div');
    div.className = 'fleet-vehicle-result';
    div.innerHTML = `
      <div class="fleet-vr-header" style="border-left:3px solid ${color}">
        <span class="fleet-vr-id" style="color:${color}">${v.id}</span>
        <span class="fleet-vr-route">${route}</span>
        <span class="fleet-vr-toggle">▼</span>
      </div>
      <div class="fleet-vr-kpis">
        <div class="fleet-vr-kpi"><div class="fleet-vr-kpi-val">${fmtTime(v.total_time_h || 0)}</div><div class="fleet-vr-kpi-lbl">Time</div></div>
        <div class="fleet-vr-kpi"><div class="fleet-vr-kpi-val">$${Math.round((v.total_cost_usd || 0) / 1000)}K</div><div class="fleet-vr-kpi-lbl">Cost</div></div>
        <div class="fleet-vr-kpi"><div class="fleet-vr-kpi-val">${Math.round(v.total_distance_km || 0)}km</div><div class="fleet-vr-kpi-lbl">Dist</div></div>
        <div class="fleet-vr-kpi"><div class="fleet-vr-kpi-val">+${(v.ml_delay_h || 0).toFixed(1)}h</div><div class="fleet-vr-kpi-lbl">ML Delay</div></div>
      </div>
      <div class="fleet-vr-legs">${legsHTML}</div>`;

    div.querySelector('.fleet-vr-header').addEventListener('click', () => {
      const legs = div.querySelector('.fleet-vr-legs');
      const tog = div.querySelector('.fleet-vr-toggle');
      legs.classList.toggle('open');
      tog.textContent = legs.classList.contains('open') ? '▲' : '▼';
    });

    el.fleetVehicles.appendChild(div);
  });

  el.fleetResults.style.display = '';
}

// ══════════════════════════════════════════════════════════════════════
// LIVE STATUS CONTROLLER
// ══════════════════════════════════════════════════════════════════════
async function refreshLiveStatus() {
  try {
    const s = await Api.getLiveStatus();
    const isLive = s.mode !== 'simulation';
    el.liveModeDot.className = `live-dot ${isLive ? 'live' : 'sim'}`;
    el.liveModeLabel.textContent = isLive ? '🟢 Live API Mode' : '🟡 Simulation Mode';
    el.chipLive.textContent = isLive ? '🟢 Live' : '🟡 Simulation';

    el.liveGrid.innerHTML = `
      <div class="live-stat"><div class="live-stat-val">${s.hub_count || '—'}</div><div class="live-stat-lbl">Hubs</div></div>
      <div class="live-stat"><div class="live-stat-val">${s.edge_count || '—'}</div><div class="live-stat-lbl">Routes</div></div>
      <div class="live-stat"><div class="live-stat-val">${s.active_weather_alerts || 0}</div><div class="live-stat-lbl">Weather</div></div>
      <div class="live-stat"><div class="live-stat-val">${s.active_customs_delays || 0}</div><div class="live-stat-lbl">Customs</div></div>`;

    // ML indicator
    if (el.mlStatusDot) {
      el.mlStatusDot.style.color = s.ml_active ? '#10b981' : '#6080a0';
      el.mlStatusDot.title = s.ml_active ? 'GBR model active' : 'Model loading…';
    }
  } catch (e) { /* silent */ }
}
setInterval(refreshLiveStatus, 15000);

// ── Bootstrap ─────────────────────────────────────────────────────────
async function bootstrap() {
  setStatus('Loading…', 'info');
  MapController.init();
  try {
    const g = await Api.getGraph();
    State.nodes = g.nodes;

    const sorted = [...g.nodes].sort((a, b) => a.name.localeCompare(b.name));

    // Route tab selects
    State.srcSS = new SearchableSelect({ host: $('source-ss'), placeholder: 'Search origin hub…', onChange: onSelectChange });
    State.dstSS = new SearchableSelect({ host: $('dest-ss'), placeholder: 'Search destination hub…', onChange: onSelectChange });
    State.weatherSS = new SearchableSelect({ host: $('weather-ss'), placeholder: 'Select hub…', onChange: () => updateOneDelta('weather') });
    State.customsSS = new SearchableSelect({ host: $('customs-ss'), placeholder: 'Select hub…', onChange: () => updateOneDelta('customs') });
    [State.srcSS, State.dstSS, State.weatherSS, State.customsSS].forEach(ss => ss.populate(sorted));

    // Pareto tab selects
    State.paretoSrcSS = new SearchableSelect({ host: $('pareto-src-ss'), placeholder: 'Search origin…', onChange: onParetoSelectChange });
    State.paretoDstSS = new SearchableSelect({ host: $('pareto-dst-ss'), placeholder: 'Search destination…', onChange: onParetoSelectChange });
    [State.paretoSrcSS, State.paretoDstSS].forEach(ss => ss.populate(sorted));

    MapController.renderGraph(g);

    el.chipHubs.textContent = `⬡ ${g.node_count} Hubs`;
    el.chipEdges.textContent = `↔ ${g.edge_count} Routes`;

    updateSliderTrack(el.weatherSlider);
    updateSliderTrack(el.customsSlider);

    setStatus('Ready', 'success');
    await refreshEvents();
    await refreshLiveStatus();
    updateActivePanel();
  } catch (err) {
    console.error('Bootstrap error:', err);
    setStatus('Connection error', 'danger');
  }
}

bootstrap();
