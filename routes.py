"""
routes.py — Flask Blueprint exposing the logistics REST API. LogistiPath v2.

Endpoints:
  GET  /api/graph              — full node + edge data
  POST /api/pathfind           — single optimal route (Dijkstra / A*)
  POST /api/pareto             — Pareto front of routes (multi-objective)
  GET  /api/predict            — ML delay prediction for a route segment
  POST /api/fleet              — multi-vehicle fleet routing (VRP)
  GET  /api/live-status        — live data fetcher status
  GET  /api/constraints        — current constraint state
  POST /api/constraints        — apply a constraint
  GET  /api/events             — recent event log
  POST /api/events/random      — trigger a random disruption
  GET  /api/fx                 — current FX rates
"""
from flask import Blueprint, jsonify, request
from graph import LogisticsGraph
from pathfinding import dijkstra, a_star
from constraints import constraint_engine
from pareto import eps_pareto_paths
from fleet import solve_fleet
import live_data as _ld
import ml_predictor as _ml

api   = Blueprint("api", __name__)
graph = LogisticsGraph()

# ── Startup: initialise live-data fetcher and ML predictor ───────────────
_fetcher   = _ld.init_fetcher(constraint_engine, graph)
_predictor = _ml.init_predictor(graph)

print(f"[LogistiPath v2]  {len(graph.nodes)} hubs  |  {len(graph.edges)} edges loaded.")


# ---------------------------------------------------------------------------
# /api/graph
# ---------------------------------------------------------------------------
@api.route("/graph", methods=["GET"])
def get_graph():
    nodes = [{"id": k, **v} for k, v in graph.nodes.items()]
    return jsonify({
        "nodes":      nodes,
        "edges":      graph.edges,
        "node_count": len(nodes),
        "edge_count": len(graph.edges),
    })


# ---------------------------------------------------------------------------
# /api/pathfind
# ---------------------------------------------------------------------------
@api.route("/pathfind", methods=["POST"])
def pathfind():
    data     = request.get_json(force=True)
    src      = data.get("source", "")
    dst      = data.get("destination", "")
    algo     = data.get("algorithm", "dijkstra")
    optimize = data.get("optimize", "time")

    if src not in graph.nodes:
        return jsonify({"found": False, "error": f"Unknown source: {src}"}), 400
    if dst not in graph.nodes:
        return jsonify({"found": False, "error": f"Unknown destination: {dst}"}), 400
    if src == dst:
        return jsonify({"found": False, "error": "Source and destination must differ."}), 400

    weight = {"time": "eff_time", "distance": "distance", "cost": "eff_cost"}.get(optimize, "eff_time")
    adj    = graph.adj_with_constraints(constraint_engine)

    if algo == "astar":
        def heuristic(n1, n2):
            dist_km = graph.haversine(n1, n2)
            if optimize == "distance":
                return dist_km
            elif optimize == "cost":
                return dist_km * 0.7
            else:
                return dist_km / 820.0
        result = a_star(adj, graph.nodes, src, dst, heuristic, weight=weight)
    else:
        result = dijkstra(adj, graph.nodes, src, dst, weight=weight)

    if result is None:
        return jsonify({"found": False, "error": "No path found between these hubs."})

    result["algorithm"] = "A*" if algo == "astar" else "Dijkstra"
    result["optimize"]  = optimize

    # Attach ML delay prediction for dominant segment
    if _predictor and _predictor._trained and result.get("segments"):
        dominant_seg  = max(result["segments"], key=lambda s: s["distance"])
        ml_pred       = _predictor.predict(
            dominant_seg["from"], dominant_seg["to"],
            dominant_seg["mode"], constraint_engine
        )
        result["ml_prediction"] = ml_pred
    else:
        result["ml_prediction"] = None

    src_name = graph.nodes[src]["name"]
    dst_name = graph.nodes[dst]["name"]
    constraint_engine.log(
        f"✅ [{result['algorithm']}] {src_name} → {dst_name} | "
        f"{result['total_distance']:,} km | {result['total_time']:.1f} h | "
        f"${result['total_cost']:,.0f}",
        "success"
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# /api/pareto  — POST { source, destination [, n_samples] }
# ---------------------------------------------------------------------------
@api.route("/pareto", methods=["POST"])
def pareto_find():
    data      = request.get_json(force=True)
    src       = data.get("source", "")
    dst       = data.get("destination", "")
    n_samples = int(data.get("n_samples", 50))

    if src not in graph.nodes:
        return jsonify({"error": f"Unknown source: {src}"}), 400
    if dst not in graph.nodes:
        return jsonify({"error": f"Unknown destination: {dst}"}), 400
    if src == dst:
        return jsonify({"error": "Source and destination must differ."}), 400

    adj   = graph.adj_with_constraints(constraint_engine)
    front = eps_pareto_paths(adj, graph.nodes, src, dst, n_samples=n_samples)

    if not front:
        return jsonify({"found": False, "pareto_front": [],
                        "error": "No path found between these hubs."})

    src_name = graph.nodes[src]["name"]
    dst_name = graph.nodes[dst]["name"]
    constraint_engine.log(
        f"◈ [Pareto] {src_name} → {dst_name} | {len(front)} non-dominated routes",
        "info"
    )
    return jsonify({"found": True, "pareto_front": front, "count": len(front)})


# ---------------------------------------------------------------------------
# /api/predict  — GET ?from=X&to=Y&mode=Z
# ---------------------------------------------------------------------------
@api.route("/predict", methods=["GET"])
def predict_delay():
    from_node = request.args.get("from", "")
    to_node   = request.args.get("to",   "")
    mode      = request.args.get("mode", "sea")

    if from_node not in graph.nodes:
        return jsonify({"error": f"Unknown hub: {from_node}"}), 400
    if to_node not in graph.nodes:
        return jsonify({"error": f"Unknown hub: {to_node}"}), 400

    if not _predictor:
        return jsonify({"error": "ML predictor not initialised."}), 503

    result = _predictor.predict(from_node, to_node, mode, constraint_engine)
    return jsonify(result)


# ---------------------------------------------------------------------------
# /api/fleet  — POST { vehicles: [...] }
# ---------------------------------------------------------------------------
@api.route("/fleet", methods=["POST"])
def fleet_routing():
    data = request.get_json(force=True)

    # Basic validation
    vehicles = data.get("vehicles", [])
    if not vehicles:
        return jsonify({"error": "No vehicles provided."}), 400

    for i, v in enumerate(vehicles):
        if "origin" not in v:
            return jsonify({"error": f"Vehicle {i}: missing 'origin'."}), 400
        if v["origin"] not in graph.nodes:
            return jsonify({"error": f"Vehicle {i}: unknown origin '{v['origin']}'."}), 400
        for d in v.get("destinations", []):
            if d not in graph.nodes:
                return jsonify({"error": f"Vehicle {i}: unknown destination '{d}'."}), 400

    result = solve_fleet(data, graph, constraint_engine,
                         predictor=_predictor)

    constraint_engine.log(
        f"🚛 Fleet routed: {len(vehicles)} vehicles | "
        f"total cost ${result['fleet_summary'].get('fleet_cost_usd', 0):,.0f}",
        "info"
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# /api/live-status  — GET
# ---------------------------------------------------------------------------
@api.route("/live-status", methods=["GET"])
def live_status():
    status = _fetcher.get_status() if _fetcher else {"mode": "unavailable"}
    status["ml_active"] = _predictor._trained if _predictor else False
    return jsonify(status)


# ---------------------------------------------------------------------------
# /api/fx  — GET
# ---------------------------------------------------------------------------
@api.route("/fx", methods=["GET"])
def fx_rates():
    rates = _fetcher.get_fx_rates() if _fetcher else {}
    return jsonify({"rates": rates})


# ---------------------------------------------------------------------------
# /api/constraints
# ---------------------------------------------------------------------------
@api.route("/constraints", methods=["GET"])
def get_constraints():
    return jsonify(constraint_engine.get_state())


@api.route("/constraints", methods=["POST"])
def set_constraints():
    data  = request.get_json(force=True)
    ctype = data.get("type", "")

    if ctype == "weather":
        node = data["target"]
        mult = float(data.get("value", 1.0))
        constraint_engine.set_weather(node, mult)
        name = graph.nodes.get(node, {}).get("name", node)
        if mult > 1.0:
            constraint_engine.log(f"🌪️ Weather disruption at {name}: {mult}× delay", "warning")
        else:
            constraint_engine.log(f"☀️ Weather cleared at {name}", "success")

    elif ctype == "traffic":
        frm  = data.get("from_node", "")
        to   = data.get("target", "")
        mult = float(data.get("value", 1.0))
        constraint_engine.set_traffic(frm, to, mult)
        name = graph.nodes.get(to, {}).get("name", to)
        constraint_engine.log(f"🚦 Traffic congestion on route to {name}: {mult}×", "warning")

    elif ctype == "customs":
        node  = data["target"]
        hours = float(data.get("value", 0))
        constraint_engine.set_customs(node, hours)
        name  = graph.nodes.get(node, {}).get("name", node)
        if hours > 0:
            constraint_engine.log(f"🛃 Customs delay at {name}: +{hours}h", "info")
        else:
            constraint_engine.log(f"✅ Customs cleared at {name}", "success")

    elif ctype == "reset":
        constraint_engine.reset()
        constraint_engine.log("🔄 All constraints reset to defaults", "info")

    return jsonify({"success": True, "state": constraint_engine.get_state()})


# ---------------------------------------------------------------------------
# /api/events
# ---------------------------------------------------------------------------
@api.route("/events", methods=["GET"])
def get_events():
    limit  = int(request.args.get("limit", 20))
    events = constraint_engine.recent(limit)
    return jsonify({"events": events, "total": len(constraint_engine.events)})


@api.route("/events/random", methods=["POST"])
def random_event():
    nodes = [{"id": k, **v} for k, v in graph.nodes.items()]
    msg   = constraint_engine.generate_random_event(nodes)
    return jsonify({"success": True, "message": msg,
                    "state": constraint_engine.get_state()})
