"""
pareto.py — Multi-objective Pareto front path finder for logistics routing.

Uses weighted-scalarization sampling + ε-dominance filtering to produce
a diverse Pareto front (time, cost, distance) without requiring a true
NSGA-II population-based approach.

API:
    eps_pareto_paths(adj, nodes_meta, src, dst, n_samples=40) -> list[dict]
    Each result dict: { path, path_info, segments, total_time, total_cost,
                        total_distance, label, pareto_rank }
"""
import heapq
import math
import random


# ---------------------------------------------------------------------------
# Internals — single-objective Dijkstra with composite weight
# ---------------------------------------------------------------------------
def _dijkstra_composite(adj, nodes_meta, src, dst, w_time, w_cost, w_dist):
    """
    Run Dijkstra minimising  w_time*eff_time + w_cost*eff_cost + w_dist*distance.
    Returns (path, segments) or (None, None).
    """
    INF = float("inf")
    score     = {n: INF for n in nodes_meta}
    prev_node = {n: None for n in nodes_meta}
    prev_edge = {n: None for n in nodes_meta}
    score[src] = 0.0
    pq = [(0.0, src)]

    while pq:
        s, u = heapq.heappop(pq)
        if s > score[u]:
            continue
        if u == dst:
            break
        for edge in adj.get(u, []):
            v = edge["to"]
            ns = (s + w_time * edge["eff_time"]
                    + w_cost * edge["eff_cost"]
                    + w_dist * edge["distance"])
            if ns < score[v]:
                score[v]      = ns
                prev_node[v]  = u
                prev_edge[v]  = edge
                heapq.heappush(pq, (ns, v))

    if score[dst] == INF:
        return None, None

    # Reconstruct
    path, segments = [], []
    cur = dst
    while cur is not None:
        path.append(cur)
        if prev_edge[cur] is not None:
            segments.append(prev_edge[cur])
        cur = prev_node[cur]
    path.reverse()
    segments.reverse()
    return path, segments


def _enrich_segments(segments, nodes_meta):
    for s in segments:
        fn, tn      = s["from"], s["to"]
        s["from_name"] = nodes_meta[fn]["name"]
        s["to_name"]   = nodes_meta[tn]["name"]
        s["from_lat"]  = nodes_meta[fn]["lat"]
        s["from_lon"]  = nodes_meta[fn]["lon"]
        s["to_lat"]    = nodes_meta[tn]["lat"]
        s["to_lon"]    = nodes_meta[tn]["lon"]
    return segments


def _build_result(path, segments, nodes_meta, label=""):
    total_dist = sum(s["distance"]  for s in segments)
    total_time = sum(s["eff_time"]  for s in segments)
    total_cost = sum(s["eff_cost"]  for s in segments)
    segs = _enrich_segments([dict(s) for s in segments], nodes_meta)
    path_info = [{"id": n, **nodes_meta[n]} for n in path]
    return {
        "found":          True,
        "path":           path,
        "path_info":      path_info,
        "segments":       segs,
        "total_distance": round(total_dist, 1),
        "total_time":     round(total_time, 2),
        "total_cost":     round(total_cost, 2),
        "label":          label,
        "pareto_rank":    0,
    }


# ---------------------------------------------------------------------------
# Pareto dominance check
# ---------------------------------------------------------------------------
def _dominates(a, b):
    """Return True if solution a ε-dominates solution b on (time, cost, dist)."""
    eps = 1e-6
    ta, ca, da = a["total_time"], a["total_cost"], a["total_distance"]
    tb, cb, db = b["total_time"], b["total_cost"], b["total_distance"]
    return (ta <= tb + eps and ca <= cb + eps and da <= db + eps and
            (ta < tb - eps or ca < cb - eps or da < db - eps))


def _pareto_filter(solutions):
    """Return non-dominated subset of solutions."""
    front = []
    for i, s in enumerate(solutions):
        dominated = False
        for j, other in enumerate(solutions):
            if i != j and _dominates(other, s):
                dominated = True
                break
        if not dominated:
            front.append(s)
    return front


def _deduplicate(solutions, tol=0.02):
    """Remove near-duplicate solutions (same path fingerprint or very similar KPIs)."""
    seen_paths = set()
    seen_kpis  = []
    unique = []
    for s in solutions:
        fp = tuple(s["path"])
        if fp in seen_paths:
            continue
        # KPI similarity check (2% tolerance on all three objectives)
        dup = False
        for (t, c, d) in seen_kpis:
            if (abs(s["total_time"]     - t) / max(t, 1)     < tol and
                abs(s["total_cost"]     - c) / max(c, 1)     < tol and
                abs(s["total_distance"] - d) / max(d, 1)     < tol):
                dup = True
                break
        if not dup:
            seen_paths.add(fp)
            seen_kpis.append((s["total_time"], s["total_cost"], s["total_distance"]))
            unique.append(s)
    return unique


# ---------------------------------------------------------------------------
# Normalisation scale estimators for weight sampling
# ---------------------------------------------------------------------------
def _estimate_scales(adj, nodes_meta, src, dst):
    """Estimate typical magnitudes by running 3 single-objective searches."""
    def run(wt, wc, wd):
        path, segs = _dijkstra_composite(adj, nodes_meta, src, dst, wt, wc, wd)
        if segs is None:
            return None
        return {
            "t": sum(s["eff_time"]  for s in segs),
            "c": sum(s["eff_cost"]  for s in segs),
            "d": sum(s["distance"]  for s in segs),
        }

    r_time = run(1, 0, 0)
    r_cost = run(0, 1, 0)
    r_dist = run(0, 0, 1)

    if r_time is None:
        return None, None, None

    scale_t = max(r_time["t"], 1)
    scale_c = max((r_cost or r_time)["c"], 1)
    scale_d = max((r_dist or r_time)["d"], 1)
    return scale_t, scale_c, scale_d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def eps_pareto_paths(adj, nodes_meta, src, dst, n_samples=50):
    """
    Find a Pareto front of diverse paths between src and dst.

    Strategy:
      1. Estimate normalisation scales from 3 extreme solutions.
      2. Sample n_samples random weight triples (wt, wc, wd) covering the
         Simplex (including corners and evenly spaced interior points).
      3. Run weighted Dijkstra for each weight triple.
      4. Collect unique paths, filter for Pareto non-dominance.
      5. Label each Pareto point meaningfully and return sorted by time.

    Returns list of result dicts (empty list if no path exists).
    """
    scale_t, scale_c, scale_d = _estimate_scales(adj, nodes_meta, src, dst)
    if scale_t is None:
        return []

    # Generate weight triples on the simplex
    rng = random.Random(42)  # deterministic seed for reproducibility
    weights = []
    # Corners
    weights += [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    # Mid-edges
    weights += [(0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]
    # Centroid
    weights.append((1/3, 1/3, 1/3))
    # Random interior points
    for _ in range(n_samples - len(weights)):
        a = rng.random()
        b = rng.random() * (1 - a)
        c = 1 - a - b
        weights.append((a, b, c))

    raw_solutions = []
    for (wt, wc, wd) in weights:
        # Normalise weights to avoid scale dominance
        wt_n = wt / scale_t
        wc_n = wc / scale_c
        wd_n = wd / scale_d

        path, segs = _dijkstra_composite(adj, nodes_meta, src, dst, wt_n, wc_n, wd_n)
        if path is None:
            continue
        result = _build_result(path, segs, nodes_meta)
        raw_solutions.append(result)

    if not raw_solutions:
        return []

    # Deduplicate then filter for Pareto front
    unique = _deduplicate(raw_solutions)
    front  = _pareto_filter(unique)

    # Sort by time then label each
    front.sort(key=lambda s: s["total_time"])
    labels = _auto_label(front)
    for s, lbl in zip(front, labels):
        s["label"] = lbl
        s["pareto_rank"] = 1

    return front


def _auto_label(front):
    """Assign human-readable labels to Pareto points."""
    if not front:
        return []
    if len(front) == 1:
        return ["Optimal"]

    min_t = min(s["total_time"]     for s in front)
    min_c = min(s["total_cost"]     for s in front)
    min_d = min(s["total_distance"] for s in front)

    labels = []
    for s in front:
        is_fastest  = abs(s["total_time"]     - min_t) < 1e-3
        is_cheapest = abs(s["total_cost"]     - min_c) < 1e-3
        is_shortest = abs(s["total_distance"] - min_d) < 1e-3

        if is_fastest and is_cheapest:
            labels.append("⚡💲 Fastest & Cheapest")
        elif is_fastest:
            labels.append("⚡ Fastest")
        elif is_cheapest:
            labels.append("💲 Cheapest")
        elif is_shortest:
            labels.append("📏 Shortest")
        else:
            t_pct = (s["total_time"]     - min_t) / max(min_t, 1) * 100
            c_pct = (s["total_cost"]     - min_c) / max(min_c, 1) * 100
            if t_pct < c_pct:
                labels.append("⚖ Time-Balanced")
            else:
                labels.append("⚖ Cost-Balanced")
    return labels
