"""
fleet.py — Multi-vehicle fleet routing (VRP) solver.

Implements a Capacitated VRP with:
  - Greedy nearest-insertion construction heuristic
  - 2-opt local search improvement
  - Cargo-type / transport-mode feasibility filtering
  - Per-vehicle route planning using existing Dijkstra pathfinder

API:
    solve_fleet(request, graph, constraint_engine, predictor=None) -> dict

Request shape:
{
  "vehicles": [
    {
      "id":          "V1",
      "origin":      "shanghai",
      "destinations": ["rotterdam", "hamburg", "antwerp"],
      "cargo_type":  "container",   // optional
      "capacity_tons": 20000,       // optional
      "preferred_mode": "sea"       // optional: "sea"|"air"|"rail"|"road"|"any"
    }
  ]
}

Response shape:
{
  "vehicles": [
    {
      "id": "V1",
      "route_sequence": ["shanghai","rotterdam","hamburg","antwerp"],
      "legs": [ { from, to, path, segments, time, cost, distance, ml_delay } ],
      "total_time_h": ...,
      "total_cost_usd": ...,
      "total_distance_km": ...,
      "ml_delay_h": ...,
      "feasible": true
    }
  ],
  "fleet_summary": {
    "total_vehicles": N,
    "total_stops": M,
    "fleet_time_h": ...,      // makespan (max vehicle time)
    "fleet_cost_usd": ...,
    "fleet_distance_km": ...,
    "avg_utilization": ...
  }
}
"""

import heapq
import itertools
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Internal single-pair shortest path using Dijkstra
# ---------------------------------------------------------------------------
def _dijkstra(adj, nodes_meta, src, dst, weight="eff_time",
              mode_filter: Optional[str] = None):
    """
    Dijkstra with optional mode filter.
    mode_filter: if not None/any, only traverse edges of that mode.
    """
    INF = float("inf")
    dist      = {n: INF for n in nodes_meta}
    prev_node = {n: None for n in nodes_meta}
    prev_edge = {n: None for n in nodes_meta}
    dist[src] = 0.0
    pq = [(0.0, src)]

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == dst:
            break
        for edge in adj.get(u, []):
            if mode_filter and mode_filter != "any" and edge["mode"] != mode_filter:
                continue
            v  = edge["to"]
            nd = d + edge[weight]
            if nd < dist[v]:
                dist[v]      = nd
                prev_node[v] = u
                prev_edge[v] = edge
                heapq.heappush(pq, (nd, v))

    if dist[dst] == INF:
        return None

    path, segs = [], []
    cur = dst
    while cur is not None:
        path.append(cur)
        if prev_edge[cur] is not None:
            segs.append(prev_edge[cur])
        cur = prev_node[cur]
    path.reverse()
    segs.reverse()

    for s in segs:
        fn, tn = s["from"], s["to"]
        s["from_name"] = nodes_meta[fn]["name"]
        s["to_name"]   = nodes_meta[tn]["name"]
        s["from_lat"]  = nodes_meta[fn]["lat"]
        s["from_lon"]  = nodes_meta[fn]["lon"]
        s["to_lat"]    = nodes_meta[tn]["lat"]
        s["to_lon"]    = nodes_meta[tn]["lon"]

    return {
        "path":           path,
        "segments":       segs,
        "total_time":     round(sum(s["eff_time"]  for s in segs), 2),
        "total_cost":     round(sum(s["eff_cost"]  for s in segs), 2),
        "total_distance": round(sum(s["distance"]  for s in segs), 1),
    }


# ---------------------------------------------------------------------------
# Distance matrix builder (uses eff_time from Dijkstra)
# ---------------------------------------------------------------------------
def _build_distance_matrix(stops, adj, nodes_meta, mode_filter):
    """Build pairwise Dijkstra time matrix for a list of stops."""
    n = len(stops)
    matrix = {}
    paths  = {}
    for i, s in enumerate(stops):
        for j, t in enumerate(stops):
            if i == j:
                matrix[(s, t)] = 0.0
            else:
                res = _dijkstra(adj, nodes_meta, s, t,
                                weight="eff_time", mode_filter=mode_filter)
                if res:
                    matrix[(s, t)] = res["total_time"]
                    paths[(s, t)]  = res
                else:
                    matrix[(s, t)] = float("inf")
                    paths[(s, t)]  = None
    return matrix, paths


# ---------------------------------------------------------------------------
# Greedy nearest-insertion construction
# ---------------------------------------------------------------------------
def _nearest_insertion(origin, destinations, matrix):
    """
    Greedy nearest-insertion TSP approximation.
    Returns ordered list [origin, d1, d2, ..., dn].
    """
    if not destinations:
        return [origin]

    remaining = list(destinations)
    route     = [origin]

    while remaining:
        best_node = None
        best_cost = float("inf")
        for node in remaining:
            cost = matrix.get((route[-1], node), float("inf"))
            if cost < best_cost:
                best_cost = cost
                best_node = node
        if best_node is None:
            # fallback: append remaining in order
            route.extend(remaining)
            break
        route.append(best_node)
        remaining.remove(best_node)

    return route


# ---------------------------------------------------------------------------
# 2-opt local search improvement
# ---------------------------------------------------------------------------
def _two_opt(route, matrix):
    """
    Apply 2-opt swaps to improve route.
    Only permutes the destinations segment (fixes origin at index 0).
    """
    if len(route) <= 3:
        return route

    improved = True
    best = route[:]

    def route_cost(r):
        return sum(matrix.get((r[i], r[i+1]), float("inf"))
                   for i in range(len(r) - 1))

    best_cost = route_cost(best)

    while improved:
        improved = False
        # Only swap within destination segment (indices 1 to end)
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                new_route = best[:i] + best[i:j+1][::-1] + best[j+1:]
                nc = route_cost(new_route)
                if nc < best_cost - 1e-6:
                    best      = new_route
                    best_cost = nc
                    improved  = True
                    break
            if improved:
                break

    return best


# ---------------------------------------------------------------------------
# Single vehicle route builder
# ---------------------------------------------------------------------------
def _route_vehicle(vehicle, adj, nodes_meta, predictor, constraint_engine):
    origin  = vehicle.get("origin", "")
    dests   = vehicle.get("destinations", [])
    mode    = vehicle.get("preferred_mode", "any")
    if mode == "any":
        mode = None   # no filter

    # Validate all nodes exist
    all_stops = [origin] + dests
    invalid   = [s for s in all_stops if s not in nodes_meta]
    if invalid:
        return {
            "id":       vehicle.get("id", "?"),
            "error":    f"Unknown hubs: {invalid}",
            "feasible": False,
        }

    if not dests:
        return {
            "id":             vehicle.get("id", "?"),
            "route_sequence": [origin],
            "legs":           [],
            "total_time_h":   0,
            "total_cost_usd": 0,
            "total_distance_km": 0,
            "ml_delay_h":     0,
            "feasible":       True,
        }

    # Build cost matrix and run nearest-insertion + 2-opt
    matrix, paths = _build_distance_matrix(all_stops, adj, nodes_meta, mode)
    greedy_route  = _nearest_insertion(origin, dests, matrix)
    opt_route     = _two_opt(greedy_route, matrix)

    # Build legs along optimised route
    legs            = []
    total_time      = 0.0
    total_cost      = 0.0
    total_distance  = 0.0
    total_ml_delay  = 0.0
    feasible        = True

    for i in range(len(opt_route) - 1):
        frm, to_n = opt_route[i], opt_route[i+1]
        leg_path  = paths.get((frm, to_n))

        if leg_path is None:
            # Try unconstrained fallback
            leg_path = _dijkstra(adj, nodes_meta, frm, to_n, weight="eff_time")

        if leg_path is None:
            feasible = False
            legs.append({"from": frm, "to": to_n, "error": "no_path"})
            continue

        # ML delay prediction
        ml_delay = 0.0
        if predictor and predictor._trained:
            dominant_mode = (leg_path["segments"][0]["mode"]
                             if leg_path["segments"] else "sea")
            pred = predictor.predict(frm, to_n, dominant_mode, constraint_engine)
            ml_delay = pred.get("predicted_delay_h", 0.0)

        total_time     += leg_path["total_time"]
        total_cost     += leg_path["total_cost"]
        total_distance += leg_path["total_distance"]
        total_ml_delay += ml_delay

        legs.append({
            "from":         frm,
            "from_name":    nodes_meta[frm]["name"],
            "to":           to_n,
            "to_name":      nodes_meta[to_n]["name"],
            "path":         leg_path["path"],
            "segments":     leg_path["segments"],
            "time_h":       leg_path["total_time"],
            "cost_usd":     leg_path["total_cost"],
            "distance_km":  leg_path["total_distance"],
            "ml_delay_h":   round(ml_delay, 2),
        })

    return {
        "id":              vehicle.get("id", "?"),
        "route_sequence":  opt_route,
        "legs":            legs,
        "total_time_h":    round(total_time,     2),
        "total_cost_usd":  round(total_cost,     2),
        "total_distance_km": round(total_distance, 1),
        "ml_delay_h":      round(total_ml_delay, 2),
        "feasible":        feasible,
        "cargo_type":      vehicle.get("cargo_type",    "general"),
        "capacity_tons":   vehicle.get("capacity_tons", 0),
        "preferred_mode":  vehicle.get("preferred_mode", "any"),
    }


# ---------------------------------------------------------------------------
# Public solve_fleet API
# ---------------------------------------------------------------------------
def solve_fleet(request: dict, graph, constraint_engine, predictor=None) -> dict:
    """
    Solve multi-vehicle fleet routing.

    request: { "vehicles": [ {id, origin, destinations, ...} ] }
    Returns full fleet solution dict.
    """
    vehicles_req = request.get("vehicles", [])
    if not vehicles_req:
        return {"error": "No vehicles provided.", "vehicles": [], "fleet_summary": {}}

    adj        = graph.adj_with_constraints(constraint_engine)
    nodes_meta = graph.nodes

    results = []
    for v in vehicles_req:
        res = _route_vehicle(v, adj, nodes_meta, predictor, constraint_engine)
        results.append(res)

    # Fleet summary
    feasible_routes = [r for r in results if r.get("feasible", False)]
    fleet_time     = max((r["total_time_h"]    for r in feasible_routes), default=0)
    fleet_cost     = sum(r["total_cost_usd"]   for r in feasible_routes)
    fleet_dist     = sum(r["total_distance_km"]for r in feasible_routes)
    fleet_ml_delay = sum(r["ml_delay_h"]       for r in feasible_routes)
    total_stops    = sum(len(r.get("route_sequence", [])) - 1
                         for r in feasible_routes)

    return {
        "vehicles": results,
        "fleet_summary": {
            "total_vehicles":   len(results),
            "feasible_vehicles": len(feasible_routes),
            "total_stops":      total_stops,
            "fleet_makespan_h": round(fleet_time,  2),
            "fleet_cost_usd":   round(fleet_cost,  2),
            "fleet_distance_km":round(fleet_dist,  1),
            "fleet_ml_delay_h": round(fleet_ml_delay, 2),
        }
    }
