/**
 * api.js — Thin fetch() wrapper for all LogistiPath REST calls. v2
 */

const API_BASE = '/api';

const Api = {
  /** GET /api/graph */
  async getGraph() {
    const r = await fetch(`${API_BASE}/graph`);
    if (!r.ok) throw new Error('Failed to load graph');
    return r.json();
  },

  /** POST /api/pathfind */
  async pathfind({ source, destination, algorithm, optimize }) {
    const r = await fetch(`${API_BASE}/pathfind`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, destination, algorithm, optimize }),
    });
    return r.json();
  },

  /** POST /api/pareto — multi-objective Pareto front */
  async paretoFind({ source, destination, n_samples = 50 }) {
    const r = await fetch(`${API_BASE}/pareto`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, destination, n_samples }),
    });
    return r.json();
  },

  /** GET /api/predict?from=X&to=Y&mode=Z */
  async predictDelay(fromNode, toNode, mode = 'sea') {
    const r = await fetch(
      `${API_BASE}/predict?from=${encodeURIComponent(fromNode)}&to=${encodeURIComponent(toNode)}&mode=${mode}`
    );
    return r.json();
  },

  /** POST /api/fleet */
  async solveFleet(vehicles) {
    const r = await fetch(`${API_BASE}/fleet`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicles }),
    });
    return r.json();
  },

  /** GET /api/live-status */
  async getLiveStatus() {
    const r = await fetch(`${API_BASE}/live-status`);
    return r.json();
  },

  /** GET /api/fx */
  async getFxRates() {
    const r = await fetch(`${API_BASE}/fx`);
    return r.json();
  },

  /** GET /api/constraints */
  async getConstraints() {
    const r = await fetch(`${API_BASE}/constraints`);
    return r.json();
  },

  /** POST /api/constraints — set a single constraint */
  async setConstraint(payload) {
    const r = await fetch(`${API_BASE}/constraints`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return r.json();
  },

  /** POST /api/constraints — reset all */
  async resetConstraints() {
    return Api.setConstraint({ type: 'reset' });
  },

  /** GET /api/events */
  async getEvents(limit = 25) {
    const r = await fetch(`${API_BASE}/events?limit=${limit}`);
    return r.json();
  },

  /** POST /api/events/random */
  async randomEvent() {
    const r = await fetch(`${API_BASE}/events/random`, { method: 'POST' });
    return r.json();
  },
};
