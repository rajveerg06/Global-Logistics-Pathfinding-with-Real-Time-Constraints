# LogistiPath — Global Logistics Pathfinding with Real-Time Constraints

An interactive full-stack logistics routing simulator that finds optimal global shipment paths across 25 international hubs.

It combines:
- **Backend pathfinding** with **Dijkstra** and **A\***
- **Dynamic disruptions** (weather, traffic, customs delays)
- **Live map visualization** (Leaflet)
- **Real-time route recalculation** when constraints change

---

## Features

- 🌍 **Global network graph** of hubs, ports, and multimodal routes (air, sea, rail)
- 🧠 **Two algorithms**: Dijkstra and A* (heuristic-guided)
- 🎯 **Optimization modes**: time, distance, or cost
- ⚡ **Real-time constraints engine**:
  - Weather multipliers
  - Route traffic multipliers
  - Customs delay hours
- 📡 **Event feed** with disruption and routing logs
- 🗺️ **Interactive map UI** with route highlighting and shipment animation
- 🔁 **Automatic rerouting** after disruption updates

---

## Tech Stack

- **Backend:** Python, Flask, Flask-CORS
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Mapping:** Leaflet.js + CartoDB dark tiles

---

## Project Structure

```text
.
├── app.py               # Flask app entry point + static hosting
├── routes.py            # REST API routes
├── graph.py             # Nodes, edges, graph utilities, effective weights
├── pathfinding.py       # Dijkstra + A* implementations
├── constraints.py       # Constraint engine + event log + random disruptions
├── requirements.txt     # Python dependencies
└── static/
    ├── index.html       # UI shell
    ├── index.css        # Design system + component styling
    ├── api.js           # Frontend API client wrapper
    ├── map.js           # Leaflet map controller + animations
    └── app.js           # Main UI/state controller
```

---

## How It Works

1. Frontend loads graph metadata from `GET /api/graph`.
2. User selects source, destination, algorithm, and optimization target.
3. Frontend calls `POST /api/pathfind`.
4. Backend applies active constraints and runs selected algorithm:
   - `dijkstra` for classic shortest path
   - `astar` with admissible heuristic (by optimize mode)
5. Result returns segments, totals (distance/time/cost), and path details.
6. Frontend renders:
   - highlighted route
   - segment table
   - summary cards
   - live event feed

---

## Setup and Run

### 1) Clone repository

```bash
git clone <your-repo-url>
cd Global-Logistics-Pathfinding-with-Real-Time-Constraints-main
```

### 2) Create virtual environment (recommended)

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Start server

```bash
python app.py
```

Open in browser:

- http://localhost:5000

---

## API Reference

### `GET /api/graph`
Returns nodes and base edges for map rendering.

**Response (shape):**
```json
{
  "nodes": [{"id": "shanghai", "name": "Shanghai", "lat": 31.23, "lon": 121.47, "type": "port"}],
  "edges": [{"from": "shanghai", "to": "tokyo", "mode": "air", "distance": 1760, "time": 2.146, "cost": 8448.0}],
  "node_count": 25,
  "edge_count": 260
}
```

### `POST /api/pathfind`
Find optimal route.

**Request body:**
```json
{
  "source": "shanghai",
  "destination": "rotterdam",
  "algorithm": "dijkstra",
  "optimize": "time"
}
```

- `algorithm`: `dijkstra` | `astar`
- `optimize`: `time` | `distance` | `cost`

### `GET /api/constraints`
Get active constraint state.

### `POST /api/constraints`
Set or reset a constraint.

**Weather example:**
```json
{ "type": "weather", "target": "singapore", "value": 2.1 }
```

**Traffic example:**
```json
{ "type": "traffic", "from_node": "shanghai", "target": "tokyo", "value": 1.6 }
```

**Customs example:**
```json
{ "type": "customs", "target": "dubai", "value": 24 }
```

**Reset all:**
```json
{ "type": "reset" }
```

### `GET /api/events?limit=20`
Fetch recent event log entries.

### `POST /api/events/random`
Generate a random disruption event.

---

## Notes

- The app runs with `debug=True` in `app.py` for local development.
- `flask-cors` is enabled for development-friendly API access.
- Constraints affect effective edge time/cost before each path search.

---

## Future Improvements

- Add authentication and per-user simulation sessions
- Persist events/constraints in a database
- Add route export (CSV/PDF)
- Add test suite for pathfinding and API endpoints

---

## License

No license file is currently included in this repository.
If you plan to publish publicly, consider adding one (e.g., MIT).
