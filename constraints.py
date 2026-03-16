"""
constraints.py — Real-time constraint engine (weather, traffic, customs).
"""
import random
import time as _time


class ConstraintEngine:
    MAX_EVENTS = 60

    def __init__(self):
        self._weather  = {}   # node_id -> multiplier  (1.0 = normal)
        self._traffic  = {}   # "from__to" -> multiplier
        self._customs  = {}   # node_id -> delay_hours
        self.events    = []

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------
    def weather_multiplier(self, node: str) -> float:
        return self._weather.get(node, 1.0)

    def traffic_multiplier(self, frm: str, to: str) -> float:
        return self._traffic.get(f"{frm}__{to}", 1.0)

    def customs_delay(self, node: str) -> float:
        return self._customs.get(node, 0.0)

    def get_state(self) -> dict:
        return {
            "weather":  dict(self._weather),
            "traffic":  dict(self._traffic),
            "customs":  dict(self._customs),
        }

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------
    def set_weather(self, node: str, multiplier: float):
        multiplier = round(float(multiplier), 2)
        if multiplier <= 1.0:
            self._weather.pop(node, None)
        else:
            self._weather[node] = multiplier

    def set_traffic(self, frm: str, to: str, multiplier: float):
        key = f"{frm}__{to}"
        multiplier = round(float(multiplier), 2)
        if multiplier <= 1.0:
            self._traffic.pop(key, None)
        else:
            self._traffic[key] = multiplier

    def set_customs(self, node: str, hours: float):
        hours = round(float(hours), 1)
        if hours <= 0:
            self._customs.pop(node, None)
        else:
            self._customs[node] = hours

    def reset(self):
        self._weather.clear()
        self._traffic.clear()
        self._customs.clear()

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------
    def log(self, message: str, kind: str = "info"):
        self.events.append({
            "message":   message,
            "type":      kind,
            "timestamp": round(_time.time(), 3),
        })
        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]

    def recent(self, n: int = 20) -> list:
        return list(reversed(self.events[-n:]))

    # ------------------------------------------------------------------
    # Random disruption generator
    # ------------------------------------------------------------------
    def generate_random_event(self, nodes: list) -> str:
        node = random.choice(nodes)
        nid, name = node["id"], node["name"]
        kind = random.choice(["weather", "weather", "customs", "traffic"])

        if kind == "weather":
            mult = round(random.uniform(1.5, 3.5), 1)
            self.set_weather(nid, mult)
            descs = ["Tropical storm", "Dense fog", "Blizzard", "Cyclone", "Heavy turbulence"]
            desc  = random.choice(descs)
            msg = f"🌪️ {desc} at {name} — {int((mult-1)*100)}% delay added"
            self.log(msg, "warning")

        elif kind == "customs":
            hours = random.choice([12, 24, 36, 48, 72])
            self.set_customs(nid, hours)
            msg = f"🛃 Customs inspection surge at {name} — +{hours}h delay"
            self.log(msg, "info")

        else:
            mult = round(random.uniform(1.3, 2.2), 1)
            self._weather[nid] = max(self._weather.get(nid, 1.0), mult)
            descs = ["Port congestion", "Labour strike", "Berth shortage", "Vessel queue"]
            desc  = random.choice(descs)
            msg = f"🚢 {desc} at {name} — {mult}x slowdown"
            self.log(msg, "danger")

        return msg


# Singleton used by routes.py
constraint_engine = ConstraintEngine()
