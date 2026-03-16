"""
pathfinding.py — Dijkstra and A* algorithms for logistics routing.
"""
import heapq
import math


# ---------------------------------------------------------------------------
def _reconstruct(prev_node, prev_edge, src, dst, nodes_meta):
    """Walk back predecessor maps to build path + segment list."""
    path, segments = [], []
    cur = dst
    while cur is not None:
        path.append(cur)
        if prev_edge[cur] is not None:
            segments.append(prev_edge[cur])
        cur = prev_node[cur]
    path.reverse()
    segments.reverse()

    total_dist = sum(s["distance"]  for s in segments)
    total_time = sum(s["eff_time"]  for s in segments)
    total_cost = sum(s["eff_cost"]  for s in segments)

    # Enrich segments with human-readable names and coordinates
    for s in segments:
        fn, tn = s["from"], s["to"]
        s["from_name"] = nodes_meta[fn]["name"]
        s["to_name"]   = nodes_meta[tn]["name"]
        s["from_lat"]  = nodes_meta[fn]["lat"]
        s["from_lon"]  = nodes_meta[fn]["lon"]
        s["to_lat"]    = nodes_meta[tn]["lat"]
        s["to_lon"]    = nodes_meta[tn]["lon"]

    path_info = [{"id": n, **nodes_meta[n]} for n in path]

    return {
        "found":          True,
        "path":           path,
        "path_info":      path_info,
        "segments":       segments,
        "total_distance": round(total_dist, 1),
        "total_time":     round(total_time, 2),
        "total_cost":     round(total_cost, 2),
    }


# ---------------------------------------------------------------------------
def dijkstra(adj: dict, nodes_meta: dict, src: str, dst: str,
             weight: str = "eff_time") -> dict | None:
    """
    Classic Dijkstra's shortest-path.
    Returns enriched result dict or None if no path exists.
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
            v  = edge["to"]
            nd = d + edge[weight]
            if nd < dist[v]:
                dist[v]      = nd
                prev_node[v] = u
                prev_edge[v] = edge
                heapq.heappush(pq, (nd, v))

    if dist[dst] == INF:
        return None

    return _reconstruct(prev_node, prev_edge, src, dst, nodes_meta)


# ---------------------------------------------------------------------------
def a_star(adj: dict, nodes_meta: dict, src: str, dst: str,
           heuristic_fn, weight: str = "eff_time") -> dict | None:
    """
    A* with caller-supplied heuristic_fn(node_id, goal_id) -> estimated cost.
    Returns enriched result dict or None if no path exists.
    """
    INF = float("inf")
    g         = {n: INF for n in nodes_meta}
    prev_node = {n: None for n in nodes_meta}
    prev_edge = {n: None for n in nodes_meta}
    g[src] = 0.0
    f_src  = heuristic_fn(src, dst)
    open_set = [(f_src, 0, src)]   # (f, tie-breaker, node)
    counter  = 1                   # tie-breaker to avoid comparing nodes
    closed   = set()

    while open_set:
        _, _, u = heapq.heappop(open_set)
        if u in closed:
            continue
        if u == dst:
            break
        closed.add(u)
        for edge in adj.get(u, []):
            v  = edge["to"]
            if v in closed:
                continue
            ng = g[u] + edge[weight]
            if ng < g[v]:
                g[v]         = ng
                prev_node[v] = u
                prev_edge[v] = edge
                f_v = ng + heuristic_fn(v, dst)
                heapq.heappush(open_set, (f_v, counter, v))
                counter += 1

    if g[dst] == INF:
        return None

    return _reconstruct(prev_node, prev_edge, src, dst, nodes_meta)
