/**
 * app.js v2 — LogistiPath main controller
 * Features: SearchableSelect, presets, risk badge, timeline, impact delta
 */

// ── SearchableSelect ──────────────────────────────────────────────────
class SearchableSelect {
  constructor({ host, placeholder, onChange }) {
    this._val  = '';
    this._opts = [];
    this._cb   = onChange;
    this._open = false;

    this._wrap  = Object.assign(document.createElement('div'), { className: 'ss-wrap' });
    this._input = Object.assign(document.createElement('input'), {
      type: 'text', placeholder, className: 'ss-input', autocomplete: 'off',
    });
    this._arrow = Object.assign(document.createElement('span'), {
      className: 'ss-arrow', textContent: '▾',
    });
    this._list  = Object.assign(document.createElement('div'), { className: 'ss-list' });

    this._wrap.append(this._input, this._arrow, this._list);
    host.appendChild(this._wrap);
    this._bindEvents();
  }

  _bindEvents() {
    this._input.addEventListener('focus',  () => this._openList());
    this._input.addEventListener('input',  () => this._filter(this._input.value));
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
    // Restore last valid value if input doesn't match
    const match = this._opts.find(o => o.label === this._input.value);
    if (!match) {
      const cur = this._opts.find(o => o.value === this._val);
      this._input.value = cur ? cur.label : '';
    }
  }

  _filter(q) {
    const lower = q.toLowerCase();
    const visible = q ? this._opts.filter(o => o.label.toLowerCase().includes(lower)) : this._opts;
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
      item.addEventListener('keydown',   e => { if (e.key === 'Enter') this._select(item.dataset.value); });
    });
  }

  _select(val) {
    this._val = val;
    const o   = this._opts.find(x => x.value === val);
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

  getValue()  { return this._val; }
  setValue(v) {
    this._val = v;
    const o = this._opts.find(x => x.value === v);
    this._input.value = o ? o.label : '';
  }
  clear() { this._val = ''; this._input.value = ''; }
}

// ── Presets ───────────────────────────────────────────────────────────
const PRESETS = {
  fastest:  { algo: 'astar',    optimize: 'time',     label: 'Fastest',  icon: '⚡' },
  cheapest: { algo: 'dijkstra', optimize: 'cost',     label: 'Cheapest', icon: '💲' },
  balanced: { algo: 'dijkstra', optimize: 'time',     label: 'Balanced', icon: '⚖' },
  lowrisk:  { algo: 'dijkstra', optimize: 'distance', label: 'Safe',     icon: '🛡' },
};

// ── State ─────────────────────────────────────────────────────────────
const State = {
  nodes: [], algo: 'dijkstra', optimize: 'time',
  lastResult: null, animPlaying: false,
  srcSS: null, dstSS: null, weatherSS: null, customsSS: null,
};

// ── DOM refs ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const el = {
  swapBtn:       $('swap-btn'),
  algoToggle:    $('algo-toggle'),
  optToggle:     $('opt-toggle'),
  findBtn:       $('find-btn'),
  weatherSlider: $('weather-slider'),
  weatherVal:    $('weather-val'),
  customsSlider: $('customs-slider'),
  customsVal:    $('customs-val'),
  applyWeather:  $('apply-weather'),
  applyCustoms:  $('apply-customs'),
  randomBtn:     $('random-btn'),
  resetBtn:      $('reset-btn'),
  chipEdges:     $('chip-edges'),
  chipStatus:    $('chip-status'),
  drawerHandle:  $('drawer-handle'),
  drawerLabel:   $('drawer-label'),
  algBadge:      $('drawer-alg-badge'),
  resultCards:   $('result-cards'),
  resultSegs:    $('result-segments'),
  eventList:     $('event-list'),
  animBtn:       $('animate-btn'),
  activePanel:   $('panel-active'),
  activeList:    $('active-list'),
  headerClock:   $('header-clock'),
  riskBadge:     $('risk-badge'),
  timelineWrap:  $('timeline-wrap'),
  impactWeather: $('impact-weather'),
  impactCustoms: $('impact-customs'),
};

// ── Clock ─────────────────────────────────────────────────────────────
(function tickClock() {
  el.headerClock.textContent = new Date().toUTCString().slice(17,22) + ' UTC';
  setTimeout(tickClock, 1000);
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
  State.algo     = p.algo;
  State.optimize = p.optimize;
  setToggleValue(el.algoToggle, p.algo);
  setToggleValue(el.optToggle,  p.optimize);
  document.querySelectorAll('.preset-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.preset === key);
  });
  // Auto-run if both hubs selected
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
setupToggle(el.optToggle,  v => {
  State.optimize = v;
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
});

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
    el.findBtn.disabled  = !(src && dst);

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
    el.animBtn.textContent   = '▶ Animate Shipment';
    State.animPlaying        = false;
    refreshEvents();
    updateImpactDeltas();
  } catch (err) {
    console.error(err);
    setStatus('Error', 'danger');
    el.findBtn.innerHTML = '<span class="btn-glyph">◈</span> Find Optimal Route';
    el.findBtn.disabled  = false;
  }
}

// ── Render Results ────────────────────────────────────────────────────
function fmtTime(h) {
  if (h < 1)  return `${Math.round(h * 60)} min`;
  if (h < 24) return `${h.toFixed(1)} h`;
  const d = Math.floor(h / 24), r = Math.round(h % 24);
  return r ? `${d}d ${r}h` : `${d}d`;
}

function renderResults(r) {
  el.algBadge.textContent = r.algorithm;

  // ── Risk badge ──────────────────────────────────────────────────────
  const risk = computeRisk(r);
  el.riskBadge.className  = `risk-badge ${risk.level}`;
  el.riskBadge.style.display = 'inline-flex';
  el.riskBadge.innerHTML  = `${risk.icon} ${risk.label}` +
    (risk.deltaHours > 0 ? ` <span style="font-size:9px;opacity:0.8">+${risk.deltaHours.toFixed(1)}h</span>` : '');

  // ── Timeline ────────────────────────────────────────────────────────
  renderTimeline(r.segments);

  // ── Stat cards ──────────────────────────────────────────────────────
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
      <div class="r-card-val" style="font-size:11px">${eta.toUTCString().slice(5,22)}</div>
      <div class="r-card-sub">Arrival ETA (UTC)</div>
    </div>`;

  // ── Segment table ────────────────────────────────────────────────────
  const MI = { air:'✈', sea:'🚢', rail:'🚂', road:'🚛' };
  const baseTotal = r.segments.reduce((s, x) => s + (x.time || 0), 0);
  const rows = r.segments.map((s, i) => {
    const delayH  = (s.eff_time - (s.time || s.eff_time)).toFixed(1);
    const hasDelay= parseFloat(delayH) > 0.05;
    return `<tr>
      <td style="color:var(--txt-3)">${i + 1}</td>
      <td style="color:var(--txt)">${s.from_name}</td>
      <td style="color:var(--txt-3)">→</td>
      <td style="color:var(--txt)">${s.to_name}</td>
      <td><span class="mode-badge ${s.mode}">${MI[s.mode]||''} ${s.mode.toUpperCase()}</span></td>
      <td>${s.distance.toLocaleString()} km</td>
      <td>${fmtTime(s.eff_time)}</td>
      <td class="delta-cell ${hasDelay ? 'pos' : 'none'}">${hasDelay ? '+'+delayH+'h' : '—'}</td>
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
  const delta    = r.total_time - baseTime;
  const ratio    = baseTime > 0 ? delta / baseTime : 0;
  if (ratio < 0.05) return { level: 'low',    label: 'Low Risk',   icon: '🟢', deltaHours: delta };
  if (ratio < 0.25) return { level: 'medium', label: 'Moderate',   icon: '🟡', deltaHours: delta };
  return              { level: 'high',   label: 'High Risk',  icon: '🔴', deltaHours: delta };
}

// ── Timeline ──────────────────────────────────────────────────────────
function renderTimeline(segments) {
  if (!segments?.length) { el.timelineWrap.innerHTML = ''; return; }
  const totalTime = segments.reduce((s, x) => s + x.eff_time, 0);
  const MODE_COLOR = { air:'#00c4ee', sea:'#3b82f6', rail:'#f59e0b', road:'#6b7280' };
  const MODE_ICON  = { air:'✈', sea:'🚢', rail:'🚂', road:'🚛' };

  const bars = segments.map(s => {
    const pct   = (s.eff_time / totalTime * 100).toFixed(2);
    const color = MODE_COLOR[s.mode] || '#94a3b8';
    const label = fmtTime(s.eff_time);
    const title = `${s.from_name} → ${s.to_name} | ${s.mode.toUpperCase()} | ${label}`;
    return `<div class="tl-seg" style="flex:${pct}" title="${title}" data-bg="${color}">
      <div class="tl-seg-inner">
        <span class="tl-icon">${MODE_ICON[s.mode]||'📦'}</span>
        <div class="tl-texts">
          <span class="tl-time">${label}</span>
          <span class="tl-from">${s.from_name}</span>
        </div>
      </div>
    </div>`;
  }).join('');

  el.timelineWrap.innerHTML = `<div class="timeline-viz">${bars}</div>`;
  // Apply background colours after render
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
  const r      = State.lastResult;
  const nodeId = type === 'weather' ? State.weatherSS?.getValue() : State.customsSS?.getValue();
  const el_    = type === 'weather' ? el.impactWeather : el.impactCustoms;
  const slider = type === 'weather' ? el.weatherSlider : el.customsSlider;
  const val    = parseFloat(slider.value);

  if (!r || !nodeId) { el_.textContent = ''; el_.className = 'impact-delta'; return; }

  const segs   = r.segments.filter(s => s.to === nodeId);
  const onPath = segs.length > 0;

  if (!onPath) {
    el_.textContent  = 'Not on route';
    el_.className    = 'impact-delta off-path';
    return;
  }

  let extraH = 0, extraCost = 0;
  if (type === 'weather') {
    if (val <= 1) { el_.textContent = ''; return; }
    segs.forEach(s => { extraH += (s.time || 0) * (val - 1); extraCost += (s.cost || 0) * (val - 1); });
  } else {
    extraH = val; // flat delay per border crossing on path
  }

  if (extraH > 0 || extraCost > 0) {
    el_.className   = 'impact-delta on-path';
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
  const val  = parseFloat(el.weatherSlider.value);
  if (!node) { alert('Select a hub first.'); return; }
  await Api.setConstraint({ type: 'weather', target: node, value: val });
  refreshEvents(); updateActivePanel();
  if (State.lastResult) rerouteIfNeeded();
});

el.applyCustoms.addEventListener('click', async () => {
  const node = State.customsSS?.getValue();
  const val  = parseFloat(el.customsSlider.value);
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
  el.customsSlider.value = 0; el.customsVal.textContent = '0 h';  updateSliderTrack(el.customsSlider);
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
function openDrawer()  { drawer.classList.add('drawer-open');    el.drawerLabel.textContent = '▼ Route Results'; }
function toggleDrawer(){ drawer.classList.contains('drawer-open') ? (drawer.classList.remove('drawer-open'), el.drawerLabel.textContent = '▲ Route Results') : openDrawer(); }
el.drawerHandle.addEventListener('click',   toggleDrawer);
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
    danger:  'color:#fb7185;border-color:rgba(244,63,94,0.3);',
    info:    'color:var(--txt-2);border-color:var(--border);',
  };
  c.style.cssText = styles[kind] || styles.info;
}

// ── Event feed ────────────────────────────────────────────────────────
async function refreshEvents() {
  const { events } = await Api.getEvents(25);
  el.eventList.innerHTML = events.map(ev => {
    const t = new Date(ev.timestamp * 1000).toUTCString().slice(17,22);
    return `<div class="ev-item ${ev.type||'info'}">
      <div>${ev.message}</div>
      <div class="ev-time">${t} UTC</div>
    </div>`;
  }).join('');
}
setInterval(refreshEvents, 6000);

// ── Bootstrap ─────────────────────────────────────────────────────────
async function bootstrap() {
  setStatus('Loading…', 'info');
  MapController.init();
  try {
    const g = await Api.getGraph();
    State.nodes = g.nodes;

    // Init searchable selects
    State.srcSS     = new SearchableSelect({ host: $('source-ss'),  placeholder: 'Search origin hub…',      onChange: onSelectChange });
    State.dstSS     = new SearchableSelect({ host: $('dest-ss'),    placeholder: 'Search destination hub…', onChange: onSelectChange });
    State.weatherSS = new SearchableSelect({ host: $('weather-ss'), placeholder: 'Select hub…',             onChange: () => updateOneDelta('weather') });
    State.customsSS = new SearchableSelect({ host: $('customs-ss'), placeholder: 'Select hub…',             onChange: () => updateOneDelta('customs') });

    const sorted = [...g.nodes].sort((a,b) => a.name.localeCompare(b.name));
    [State.srcSS, State.dstSS, State.weatherSS, State.customsSS].forEach(ss => ss.populate(sorted));

    MapController.renderGraph(g);
    el.chipEdges.textContent = `↔ ${g.edge_count} Routes`;

    // Init slider tracks
    updateSliderTrack(el.weatherSlider);
    updateSliderTrack(el.customsSlider);

    setStatus('Ready', 'success');
    await refreshEvents();
  } catch (err) {
    console.error('Bootstrap error:', err);
    setStatus('Connection error', 'danger');
  }
}

bootstrap();
