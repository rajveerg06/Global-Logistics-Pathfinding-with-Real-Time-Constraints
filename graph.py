"""
graph.py — Logistics graph data: 25 global hub cities/ports and their connections.
"""
import math

# ---------------------------------------------------------------------------
# Nodes — 25 global logistics hubs
# ---------------------------------------------------------------------------
NODES = {
    "shanghai":     {"name": "Shanghai",     "lat": 31.23,  "lon": 121.47,  "type": "port",  "country": "CN", "country_name": "China"},
    "rotterdam":    {"name": "Rotterdam",    "lat": 51.92,  "lon":   4.48,  "type": "port",  "country": "NL", "country_name": "Netherlands"},
    "singapore":    {"name": "Singapore",    "lat":  1.35,  "lon": 103.82,  "type": "port",  "country": "SG", "country_name": "Singapore"},
    "dubai":        {"name": "Dubai",        "lat": 25.20,  "lon":  55.27,  "type": "hub",   "country": "AE", "country_name": "UAE"},
    "hong_kong":    {"name": "Hong Kong",    "lat": 22.32,  "lon": 114.17,  "type": "port",  "country": "HK", "country_name": "Hong Kong"},
    "los_angeles":  {"name": "Los Angeles",  "lat": 34.05,  "lon":-118.24,  "type": "port",  "country": "US", "country_name": "USA"},
    "new_york":     {"name": "New York",     "lat": 40.71,  "lon": -74.01,  "type": "hub",   "country": "US", "country_name": "USA"},
    "tokyo":        {"name": "Tokyo",        "lat": 35.68,  "lon": 139.69,  "type": "port",  "country": "JP", "country_name": "Japan"},
    "mumbai":       {"name": "Mumbai",       "lat": 19.08,  "lon":  72.88,  "type": "port",  "country": "IN", "country_name": "India"},
    "london":       {"name": "London",       "lat": 51.51,  "lon":  -0.13,  "type": "hub",   "country": "GB", "country_name": "UK"},
    "frankfurt":    {"name": "Frankfurt",    "lat": 50.11,  "lon":   8.68,  "type": "hub",   "country": "DE", "country_name": "Germany"},
    "chicago":      {"name": "Chicago",      "lat": 41.88,  "lon": -87.63,  "type": "hub",   "country": "US", "country_name": "USA"},
    "sydney":       {"name": "Sydney",       "lat":-33.87,  "lon": 151.21,  "type": "port",  "country": "AU", "country_name": "Australia"},
    "sao_paulo":    {"name": "São Paulo",    "lat":-23.55,  "lon": -46.63,  "type": "hub",   "country": "BR", "country_name": "Brazil"},
    "johannesburg": {"name": "Johannesburg", "lat":-26.20,  "lon":  28.04,  "type": "hub",   "country": "ZA", "country_name": "South Africa"},
    "cairo":        {"name": "Cairo",        "lat": 30.04,  "lon":  31.24,  "type": "hub",   "country": "EG", "country_name": "Egypt"},
    "istanbul":     {"name": "Istanbul",     "lat": 41.01,  "lon":  28.96,  "type": "hub",   "country": "TR", "country_name": "Turkey"},
    "seoul":        {"name": "Seoul",        "lat": 37.57,  "lon": 126.98,  "type": "port",  "country": "KR", "country_name": "South Korea"},
    "shenzhen":     {"name": "Shenzhen",     "lat": 22.54,  "lon": 114.06,  "type": "port",  "country": "CN", "country_name": "China"},
    "busan":        {"name": "Busan",        "lat": 35.18,  "lon": 129.08,  "type": "port",  "country": "KR", "country_name": "South Korea"},
    "hamburg":      {"name": "Hamburg",      "lat": 53.55,  "lon":   9.99,  "type": "port",  "country": "DE", "country_name": "Germany"},
    "antwerp":      {"name": "Antwerp",      "lat": 51.22,  "lon":   4.40,  "type": "port",  "country": "BE", "country_name": "Belgium"},
    "colombo":      {"name": "Colombo",      "lat":  6.93,  "lon":  79.85,  "type": "port",  "country": "LK", "country_name": "Sri Lanka"},
    "karachi":      {"name": "Karachi",      "lat": 24.86,  "lon":  67.01,  "type": "port",  "country": "PK", "country_name": "Pakistan"},
    "vladivostok":  {"name": "Vladivostok",  "lat": 43.12,  "lon": 131.88,  "type": "port",  "country": "RU", "country_name": "Russia"},
}

# ---------------------------------------------------------------------------
# Mode speeds (km/h) and cost-per-km-per-ton (USD)
# ---------------------------------------------------------------------------
MODE_SPEED   = {"air": 820, "sea": 38, "rail": 100, "road": 70}
MODE_COST_KM = {"air": 4.8, "sea": 0.7, "rail": 1.4, "road": 2.0}

# ---------------------------------------------------------------------------
# Raw edges: (from, to, distance_km, mode, bidirectional)
# ---------------------------------------------------------------------------
RAW_EDGES = [
    # ── AIR ROUTES ──────────────────────────────────────────────────────────
    ("shanghai",    "tokyo",        1760,  "air", True),
    ("shanghai",    "seoul",         870,  "air", True),
    ("shanghai",    "hong_kong",    1220,  "air", True),
    ("shanghai",    "singapore",    3280,  "air", True),
    ("shanghai",    "los_angeles",  9790,  "air", True),
    ("shanghai",    "frankfurt",    9200,  "air", True),
    ("shanghai",    "dubai",        5750,  "air", True),
    ("shanghai",    "shenzhen",     1150,  "air", True),
    ("tokyo",       "los_angeles",  8800,  "air", True),
    ("tokyo",       "sydney",       7830,  "air", True),
    ("tokyo",       "vladivostok",  1050,  "air", True),
    ("seoul",       "vladivostok",   750,  "air", True),
    ("seoul",       "busan",         320,  "air", True),
    ("busan",       "tokyo",         920,  "air", True),
    ("shenzhen",    "hong_kong",     140,  "air", True),
    ("hong_kong",   "singapore",    2590,  "air", True),
    ("singapore",   "sydney",       6300,  "air", True),
    ("singapore",   "mumbai",       2830,  "air", True),
    ("singapore",   "dubai",        5840,  "air", True),
    ("dubai",       "mumbai",       1900,  "air", True),
    ("dubai",       "london",       5490,  "air", True),
    ("dubai",       "frankfurt",    4700,  "air", True),
    ("dubai",       "cairo",        2390,  "air", True),
    ("dubai",       "istanbul",     3380,  "air", True),
    ("dubai",       "johannesburg", 7520,  "air", True),
    ("dubai",       "karachi",      1330,  "air", True),
    ("mumbai",      "karachi",       920,  "air", True),
    ("mumbai",      "colombo",      1400,  "air", True),
    ("karachi",     "colombo",      1490,  "air", True),
    ("colombo",     "singapore",    2470,  "air", True),
    ("london",      "new_york",     5540,  "air", True),
    ("london",      "frankfurt",     650,  "air", True),
    ("london",      "istanbul",     2490,  "air", True),
    ("london",      "johannesburg", 9000,  "air", True),
    ("frankfurt",   "new_york",     6200,  "air", True),
    ("frankfurt",   "istanbul",     1880,  "air", True),
    ("frankfurt",   "cairo",        2830,  "air", True),
    ("frankfurt",   "chicago",      7540,  "air", True),
    ("istanbul",    "cairo",        1305,  "air", True),
    ("cairo",       "johannesburg", 6200,  "air", True),
    ("new_york",    "chicago",      1150,  "air", True),
    ("new_york",    "los_angeles",  4490,  "air", True),
    ("new_york",    "sao_paulo",    7620,  "air", True),
    ("chicago",     "los_angeles",  2810,  "air", True),
    ("los_angeles", "sydney",      12060,  "air", True),
    ("sao_paulo",   "johannesburg", 7060,  "air", True),
    ("sao_paulo",   "london",       9300,  "air", True),
    # ── RAIL ROUTES ─────────────────────────────────────────────────────────
    ("hamburg",     "rotterdam",     360,  "rail", True),
    ("hamburg",     "antwerp",       310,  "rail", True),
    ("antwerp",     "rotterdam",      90,  "rail", True),
    ("antwerp",     "frankfurt",     440,  "rail", True),
    ("rotterdam",   "frankfurt",     370,  "rail", True),
    ("frankfurt",   "istanbul",     2200,  "rail", True),
    ("istanbul",    "cairo",        2200,  "rail", False),   # one-directional concept
    # ── SEA ROUTES ──────────────────────────────────────────────────────────
    ("shanghai",    "rotterdam",   19500,  "sea", True),
    ("shanghai",    "los_angeles",  9750,  "sea", True),
    ("shanghai",    "singapore",    3400,  "sea", True),
    ("shanghai",    "busan",         870,  "sea", True),
    ("shanghai",    "tokyo",        1760,  "sea", True),
    ("shanghai",    "hong_kong",    1220,  "sea", True),
    ("singapore",   "rotterdam",   15300,  "sea", True),
    ("singapore",   "dubai",        2900,  "sea", True),
    ("singapore",   "mumbai",       2800,  "sea", True),
    ("singapore",   "sydney",       6300,  "sea", True),
    ("singapore",   "hong_kong",    2590,  "sea", True),
    ("rotterdam",   "new_york",     5700,  "sea", True),
    ("rotterdam",   "sao_paulo",    9500,  "sea", True),
    ("rotterdam",   "hamburg",       360,  "sea", True),
    ("rotterdam",   "antwerp",        90,  "sea", True),
    ("dubai",       "rotterdam",   10200,  "sea", True),
    ("dubai",       "mumbai",       1900,  "sea", True),
    ("mumbai",      "rotterdam",   12600,  "sea", True),
    ("mumbai",      "dubai",        1900,  "sea", True),
    ("colombo",     "dubai",        2300,  "sea", True),
    ("colombo",     "rotterdam",   12500,  "sea", True),
    ("colombo",     "singapore",    2470,  "sea", True),
    ("karachi",     "dubai",        1300,  "sea", True),
    ("karachi",     "singapore",    4200,  "sea", True),
    ("busan",       "los_angeles",  9000,  "sea", True),
    ("busan",       "shanghai",      870,  "sea", True),
    ("hong_kong",   "busan",         770,  "sea", True),
    ("hong_kong",   "singapore",    2590,  "sea", True),
    ("los_angeles", "tokyo",        8800,  "sea", True),
    ("los_angeles", "sydney",      12060,  "sea", True),
    ("new_york",    "rotterdam",    5700,  "sea", True),
    ("new_york",    "sao_paulo",    7500,  "sea", True),
    ("sao_paulo",   "rotterdam",    9500,  "sea", True),
    ("sydney",      "los_angeles", 12060,  "sea", True),
    ("sydney",      "singapore",    6300,  "sea", True),
    ("vladivostok", "busan",         750,  "sea", True),
    ("vladivostok", "tokyo",        1050,  "sea", True),
    ("johannesburg","rotterdam",   11400,  "sea", True),
    ("johannesburg","sao_paulo",    7400,  "sea", True),
]


def build_edges():
    """
    Expand RAW_EDGES into full edge dicts, computing time and cost.
    Bidirectional edges produce two records (forward + reverse).
    """
    edges = []
    for entry in RAW_EDGES:
        f, t, dist, mode, bidir = entry
        speed = MODE_SPEED[mode]
        cpm   = MODE_COST_KM[mode]
        time_h = round(dist / speed, 3)
        cost   = round(dist * cpm, 2)

        fwd = {
            "id":       f"{f}__{t}__{mode}",
            "from":     f,
            "to":       t,
            "distance": dist,
            "time":     time_h,
            "mode":     mode,
            "cost":     cost,
        }
        edges.append(fwd)

        if bidir:
            rev = {
                "id":       f"{t}__{f}__{mode}",
                "from":     t,
                "to":       f,
                "distance": dist,
                "time":     time_h,
                "mode":     mode,
                "cost":     cost,
            }
            edges.append(rev)

    return edges


EDGES = build_edges()


# ---------------------------------------------------------------------------
class LogisticsGraph:
    def __init__(self):
        self.nodes = NODES
        self.edges = EDGES
        self._adj  = self._build_adj(EDGES)

    # ------------------------------------------------------------------
    @staticmethod
    def _build_adj(edges):
        adj = {n: [] for n in NODES}
        for e in edges:
            adj[e["from"]].append(e)
        return adj

    # ------------------------------------------------------------------
    def haversine(self, n1: str, n2: str) -> float:
        """Great-circle distance in km between two node IDs."""
        R = 6371
        lat1 = math.radians(self.nodes[n1]["lat"])
        lon1 = math.radians(self.nodes[n1]["lon"])
        lat2 = math.radians(self.nodes[n2]["lat"])
        lon2 = math.radians(self.nodes[n2]["lon"])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))

    # ------------------------------------------------------------------
    def effective_edges(self, constraint_engine):
        """Return edge dicts with eff_time / eff_cost factoring in constraints."""
        eff = []
        for e in self.edges:
            w_mult  = constraint_engine.weather_multiplier(e["to"])
            tr_mult = constraint_engine.traffic_multiplier(e["from"], e["to"])
            cust_h  = constraint_engine.customs_delay(e["to"])
            ee = dict(e)
            ee["eff_time"] = round(e["time"] * w_mult * tr_mult + cust_h, 4)
            ee["eff_cost"] = round(e["cost"] * w_mult * tr_mult, 2)
            eff.append(ee)
        return eff

    # ------------------------------------------------------------------
    def adj_with_constraints(self, constraint_engine):
        """Adjacency list keyed by from-node, using effective weights."""
        adj = {n: [] for n in self.nodes}
        for e in self.effective_edges(constraint_engine):
            adj[e["from"]].append(e)
        return adj
