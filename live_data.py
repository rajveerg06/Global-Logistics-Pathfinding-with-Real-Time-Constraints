"""
live_data.py — Simulated live data fetcher (no API key required).

Mimics real-world patterns:
  - Weather: generated from realistic per-region storm probability distributions
  - FX rates: small random walk from realistic baseline USD rates
  - Customs: updates based on hub-traffic simulation

Runs in a background thread; updates constraint_engine automatically every
REFRESH_INTERVAL_S seconds.

Public API:
    LiveDataFetcher(constraint_engine, graph)
    fetcher.start()          — starts background thread
    fetcher.get_status()     — returns dict with last_updated, mode, active_alerts
    fetcher.get_fx_rates()   — returns {currency: usd_rate}
    fetcher.force_refresh()  — immediate refresh (blocking, for testing)
"""

import math
import random
import threading
import time as _time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REFRESH_INTERVAL_S = 600   # refresh every 10 minutes
STORM_PROB_PER_HUB = 0.06  # 6% chance a hub gets a weather event per cycle
CUSTOMS_PROB       = 0.04  # 4% chance of customs surge per hub per cycle
CLEAR_PROB         = 0.25  # 25% chance an existing disruption clears each cycle

# ---------------------------------------------------------------------------
# Realistic baseline FX rates (1 USD = X local currency)
# ---------------------------------------------------------------------------
_BASE_FX = {
    "USD": 1.00,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 154.5,
    "CNY": 7.24,
    "INR": 83.4,
    "AED": 3.67,
    "SGD": 1.35,
    "AUD": 1.55,
    "BRL": 4.97,
    "KRW": 1370.0,
    "MYR": 4.72,
    "THB": 35.4,
    "IDR": 15800.0,
    "ZAR": 18.6,
    "NGN": 1555.0,
    "EGP": 47.6,
    "SAR": 3.75,
    "TRY": 32.9,
    "MXN": 17.2,
    "CAD": 1.38,
    "RUB": 92.5,
    "PKR": 278.0,
    "BDT": 110.0,
    "LKR": 305.0,
    "DKK": 6.89,
    "SEK": 10.55,
    "NOK": 10.75,
    "CHF": 0.91,
    "PLN": 4.00,
    "CLP": 950.0,
    "PEN": 3.72,
    "COP": 3900.0,
    "ARS": 900.0,
    "NZD": 1.63,
    "KWD": 0.307,
    "QAR": 3.64,
    "OMR": 0.385,
    "BHD": 0.377,
    "MAD": 10.1,
}

# Country → currency mapping
_COUNTRY_CURRENCY = {
    "US": "USD", "CA": "CAD", "MX": "MXN", "PA": "USD", "CU": "USD",
    "JM": "USD", "BR": "BRL", "AR": "ARS", "CL": "CLP", "PE": "PEN",
    "CO": "COP", "EC": "USD", "VE": "USD", "UY": "USD",
    "GB": "GBP", "FR": "EUR", "DE": "EUR", "NL": "EUR", "BE": "EUR",
    "ES": "EUR", "PT": "EUR", "IT": "EUR", "AT": "EUR", "GR": "EUR",
    "FI": "EUR", "IE": "EUR", "CH": "CHF", "SE": "SEK", "NO": "NOK",
    "DK": "DKK", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON",
    "BG": "BGN", "UA": "UAH", "LV": "EUR", "EE": "EUR", "TR": "TRY",
    "RU": "RUB",
    "CN": "CNY", "HK": "HKD", "TW": "TWD", "JP": "JPY", "KR": "KRW",
    "VN": "VND", "PH": "PHP", "TH": "THB", "ID": "IDR", "MY": "MYR",
    "SG": "SGD", "MM": "MMK", "KH": "KHR",
    "IN": "INR", "PK": "PKR", "LK": "LKR", "BD": "BDT", "NP": "NPR",
    "AE": "AED", "SA": "SAR", "OM": "OMR", "KW": "KWD", "QA": "QAR",
    "BH": "BHD", "IR": "IRR", "IQ": "IQD", "KZ": "KZT", "UZ": "UZS",
    "IL": "ILS", "LB": "LBP", "SY": "SYP", "YE": "YER", "DJ": "DJF",
    "EG": "EGP", "MA": "MAD", "TN": "TND", "LY": "LYD",
    "ZA": "ZAR", "NG": "NGN", "GH": "GHS", "CI": "XOF", "SN": "XOF",
    "KE": "KES", "TZ": "TZS", "ET": "ETB", "AO": "AOA", "MZ": "MZN",
    "AU": "AUD", "NZ": "NZD", "PG": "PGK", "FJ": "FJD",
}

# Regional storm probability (higher = more volatile weather)
_REGION_STORM_PROB = {
    "asia":     0.10,  # monsoon, typhoon zone
    "oceania":  0.08,  # cyclone zone
    "namerica": 0.06,  # hurricane zone
    "samerica": 0.07,
    "africa":   0.05,
    "europe":   0.04,
    "eurasia":  0.05,
    "other":    0.05,
}

_CONTINENT_MAP = {
    "CN": "asia", "HK": "asia", "TW": "asia", "JP": "asia", "KR": "asia",
    "VN": "asia", "PH": "asia", "TH": "asia", "ID": "asia", "MY": "asia",
    "SG": "asia", "MM": "asia", "KH": "asia", "IN": "asia", "PK": "asia",
    "LK": "asia", "BD": "asia", "NP": "asia",
    "AE": "asia", "SA": "asia", "OM": "asia", "KW": "asia", "QA": "asia",
    "BH": "asia", "IR": "asia", "IQ": "asia", "KZ": "asia", "UZ": "asia",
    "IL": "asia", "LB": "asia", "SY": "asia", "YE": "asia", "DJ": "asia",
    "RU": "eurasia",
    "NL": "europe", "BE": "europe", "DE": "europe", "GB": "europe",
    "FR": "europe", "CH": "europe", "AT": "europe", "IT": "europe",
    "ES": "europe", "PT": "europe", "SE": "europe", "NO": "europe",
    "DK": "europe", "FI": "europe", "GR": "europe", "TR": "europe",
    "PL": "europe", "CZ": "europe", "HU": "europe", "RO": "europe",
    "BG": "europe", "UA": "europe", "LV": "europe", "EE": "europe",
    "MA": "africa", "EG": "africa", "TN": "africa", "LY": "africa",
    "ZA": "africa", "NG": "africa", "GH": "africa", "CI": "africa",
    "SN": "africa", "KE": "africa", "TZ": "africa", "ET": "africa",
    "AO": "africa", "MZ": "africa",
    "US": "namerica", "CA": "namerica", "MX": "namerica",
    "PA": "namerica", "CU": "namerica", "JM": "namerica",
    "BR": "samerica", "AR": "samerica", "CL": "samerica",
    "PE": "samerica", "CO": "samerica", "EC": "samerica",
    "VE": "samerica", "UY": "samerica",
    "AU": "oceania", "NZ": "oceania", "PG": "oceania", "FJ": "oceania",
}

# Weather event descriptions by region
_STORM_DESCS = {
    "asia":     ["🌀 Typhoon", "🌧 Monsoon surge", "🌊 Storm surge", "🌪 Tropical cyclone"],
    "oceania":  ["🌀 Cyclone", "⚡ Severe storm", "🌊 High swell"],
    "namerica": ["🌀 Hurricane", "🌪 Tornado warning", "❄ Blizzard", "⛈ Severe storm"],
    "samerica": ["🌧 Amazon flooding", "🌀 Tropical storm", "⛈ Severe convection"],
    "africa":   ["🌵 Harmattan wind", "⛈ Tropical storm", "🌊 Coastal surge"],
    "europe":   ["❄ Winter storm", "🌬 Storm Ciaran", "🌧 Heavy rainfall", "⛈ Squall line"],
    "eurasia":  ["❄ Arctic blast", "🌨 Heavy snowfall", "🌬 Siberian front"],
    "other":    ["⛈ Severe weather", "🌬 Strong winds"],
}

# Customs surge descriptions
_CUSTOMS_DESCS = [
    "🛃 Security inspection surge",
    "🛃 Document verification backlog",
    "🛃 Regulatory compliance review",
    "🛃 Trade quota enforcement",
    "🛃 Phytosanitary inspection",
    "🛃 Anti-dumping investigation",
]


class LiveDataFetcher:
    """
    Simulated live data module — no external API calls required.
    Generates realistic weather, customs events and FX rates using
    probabilistic simulation seeded on real-world distributions.
    """

    def __init__(self, constraint_engine, graph):
        self._ce        = constraint_engine
        self._graph     = graph
        self._fx        = dict(_BASE_FX)
        self._thread    = None
        self._running   = False
        self._last_update = None
        self._alerts    = []   # list of recent alert strings
        self._lock      = threading.Lock()
        self._rng       = random.Random()   # independent RNG for this module

    # ------------------------------------------------------------------
    def start(self):
        """Start background refresh thread (non-blocking)."""
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self.force_refresh()   # initial load immediately
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    def _loop(self):
        while self._running:
            _time.sleep(REFRESH_INTERVAL_S)
            if self._running:
                self.force_refresh()

    # ------------------------------------------------------------------
    def force_refresh(self):
        """Run one full simulation cycle (blocking)."""
        with self._lock:
            self._refresh_weather()
            self._refresh_customs()
            self._refresh_fx()
            self._last_update = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    def _refresh_weather(self):
        nodes = self._graph.nodes
        new_alerts = []

        for nid, node in nodes.items():
            country = node.get("country", "")
            region  = _CONTINENT_MAP.get(country, "other")
            prob    = _REGION_STORM_PROB.get(region, 0.05)

            current = self._ce.weather_multiplier(nid)

            if current > 1.0:
                # Existing disruption: chance to clear
                if self._rng.random() < CLEAR_PROB:
                    self._ce.set_weather(nid, 1.0)
                    self._ce.log(f"☀️ Weather cleared at {node['name']}", "success")
            else:
                # No disruption: probabilistic new event
                if self._rng.random() < prob:
                    mult  = round(self._rng.uniform(1.4, 3.2), 1)
                    descs = _STORM_DESCS.get(region, _STORM_DESCS["other"])
                    desc  = self._rng.choice(descs)
                    self._ce.set_weather(nid, mult)
                    msg = f"{desc} at {node['name']} — {int((mult-1)*100)}% delay"
                    self._ce.log(msg, "warning")
                    new_alerts.append(msg)

        self._alerts = (new_alerts + self._alerts)[:20]

    # ------------------------------------------------------------------
    def _refresh_customs(self):
        nodes = list(self._graph.nodes.items())

        for nid, node in nodes:
            current = self._ce.customs_delay(nid)

            if current > 0:
                # Existing delay: small chance to clear
                if self._rng.random() < CLEAR_PROB * 0.6:
                    self._ce.set_customs(nid, 0)
                    self._ce.log(f"✅ Customs cleared at {node['name']}", "success")
            else:
                # Probabilistic new customs surge
                if self._rng.random() < CUSTOMS_PROB:
                    hours = self._rng.choice([6, 12, 18, 24, 36, 48])
                    self._ce.set_customs(nid, hours)
                    desc = self._rng.choice(_CUSTOMS_DESCS)
                    msg  = f"{desc} at {node['name']} — +{hours}h"
                    self._ce.log(msg, "info")

    # ------------------------------------------------------------------
    def _refresh_fx(self):
        """Simulate small random walk on FX rates (±0.3% per cycle)."""
        for currency in list(self._fx.keys()):
            if currency == "USD":
                continue
            drift = self._rng.gauss(0, 0.003)   # 0.3% std dev
            self._fx[currency] = round(
                max(0.001, self._fx[currency] * (1 + drift)), 4
            )

    # ------------------------------------------------------------------
    def get_status(self):
        """Return live status dict for the UI."""
        with self._lock:
            active_weather  = sum(1 for v in self._ce._weather.values() if v > 1.0)
            active_customs  = sum(1 for v in self._ce._customs.values() if v > 0)
            return {
                "mode":           "simulation",
                "last_updated":   self._last_update,
                "refresh_interval_s": REFRESH_INTERVAL_S,
                "active_weather_alerts":  active_weather,
                "active_customs_delays":  active_customs,
                "recent_alerts":  list(self._alerts[:5]),
                "hub_count":      len(self._graph.nodes),
                "edge_count":     len(self._graph.edges),
            }

    def get_fx_rates(self):
        """Return current FX rates dict {currency: usd_rate}."""
        with self._lock:
            return dict(self._fx)

    def get_hub_currency(self, node_id):
        """Return the currency code for a given hub."""
        node = self._graph.nodes.get(node_id, {})
        country = node.get("country", "US")
        return _COUNTRY_CURRENCY.get(country, "USD")

    def convert_cost_to_local(self, cost_usd, node_id):
        """Convert a USD cost to the local currency of the hub."""
        currency = self.get_hub_currency(node_id)
        rate = self._fx.get(currency, 1.0)
        return {
            "usd":      round(cost_usd, 2),
            "local":    round(cost_usd * rate, 2),
            "currency": currency,
            "rate":     rate,
        }


# Module-level singleton (initialised by app.py after graph is ready)
_fetcher_instance = None


def init_fetcher(constraint_engine, graph):
    """Called once at startup by app.py."""
    global _fetcher_instance
    _fetcher_instance = LiveDataFetcher(constraint_engine, graph)
    _fetcher_instance.start()
    return _fetcher_instance


def get_fetcher():
    return _fetcher_instance
