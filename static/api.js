/**
 * api.js — Thin fetch() wrapper for all LogistiPath REST calls.
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
