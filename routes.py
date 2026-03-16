"""
routes.py — Flask Blueprint exposing the logistics REST API.
"""
from flask import Blueprint, jsonify, request
from graph import LogisticsGraph
from pathfinding import dijkstra, a_star
from constraints import constraint_engine

api = Blueprint("api", __name__)
graph = LogisticsGraph()


# ---------------------------------------------------------------------------
# /api/graph  — full node + edge data for the map
# ---------------------------------------------------------------------------
@api.route("/graph", methods=["GET"])
def get_graph():
    nodes = [{"id": k, **v} for k, v in graph.nodes.items()]
    edges = graph.edges          # base (no constraints) for map rendering
    return jsonify({"nodes": nodes, "edges": edges,
                    "node_count": len(nodes), "edge_count": len(edges)})


# ---------------------------------------------------------------------------
# /api/pathfind  — POST {source, destination, algorithm, optimize}
# ---------------------------------------------------------------------------
@api.route("/pathfind", methods=["POST"])
def pathfind():
    data = request.get_json(force=True)
    src      = data.get("source", "")
    dst      = data.get("destination", "")
    algo     = data.get("algorithm", "dijkstra")   # "dijkstra" | "astar"
    optimize = data.get("optimize",  "time")        # "time" | "distance" | "cost"

    # Validation
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
            # Admissible: assume best-case air speed (820 km/h) for time,
            # straight-line for distance, cheapest mode for cost
            if optimize == "distance":
                return dist_km
            elif optimize == "cost":
                return dist_km * 0.7      # sea cost / km
            else:
                return dist_km / 820.0    # hours at top air speed

        result = a_star(adj, graph.nodes, src, dst, heuristic, weight=weight)
    else:
        result = dijkstra(adj, graph.nodes, src, dst, weight=weight)

    if result is None:
        return jsonify({"found": False, "error": "No path found between these hubs."})

    result["algorithm"] = "A*" if algo == "astar" else "Dijkstra"
    result["optimize"]  = optimize

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
# /api/constraints  — GET current state, POST to change
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
# /api/events  — GET recent log events
# ---------------------------------------------------------------------------
@api.route("/events", methods=["GET"])
def get_events():
    limit  = int(request.args.get("limit", 20))
    events = constraint_engine.recent(limit)
    return jsonify({"events": events, "total": len(constraint_engine.events)})


# ---------------------------------------------------------------------------
# /api/events/random  — POST to trigger a random disruption
# ---------------------------------------------------------------------------
@api.route("/events/random", methods=["POST"])
def random_event():
    nodes = [{"id": k, **v} for k, v in graph.nodes.items()]
    msg   = constraint_engine.generate_random_event(nodes)
    return jsonify({"success": True, "message": msg,
                    "state": constraint_engine.get_state()})
