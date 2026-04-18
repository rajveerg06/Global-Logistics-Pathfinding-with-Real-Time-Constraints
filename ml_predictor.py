"""
ml_predictor.py — ML-based route delay prediction using scikit-learn.

Model: Gradient Boosted Regressor (GBR) trained on synthetic-but-realistic
       historical route delay data generated at startup.

Features:
  - hub_tier_from / hub_tier_to  (1=mega, 2=regional, 3=local)
  - mode_encoded                  (0=air, 1=sea, 2=rail, 3=road)
  - distance_km                   (route distance)
  - base_time_h                   (nominal travel time)
  - weather_from / weather_to     (active weather multipliers)
  - customs_to                    (active customs delay at destination)
  - hour_of_day                   (0-23, for time-of-day seasonality)
  - day_of_week                   (0=Mon … 6=Sun)
  - throughput_ratio              (dest TEU / global max TEU — congestion proxy)

Output:  predicted_delay_h (additional hours beyond nominal time)
         confidence        (1 - cv of bootstrap estimates, 0-1)

Public API:
    predictor = DelayPredictor(graph)
    predictor.train()   — called at startup
    result = predictor.predict(from_node, to_node, mode, constraint_engine, dt=None)
    # returns { predicted_delay_h, confidence, breakdown, features }
"""

import math
import random
import os
import datetime

import numpy as np

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    import joblib
    _SKLEARN_OK = True
except ImportError:
    _SKLEARN_OK = False

# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_model.pkl")
N_SYNTHETIC = 6000   # number of synthetic training samples

_MODE_ENC = {"air": 0, "sea": 1, "rail": 2, "road": 3}

# Delay distribution parameters per (tier, mode) — (mean_h, std_h)
# Derived from industry benchmarks (UNCTAD, World Bank logistics performance index)
_BASE_DELAY_PARAMS = {
    (1, 0): (0.5,  0.8),   # mega hub, air
    (1, 1): (4.0,  6.0),   # mega hub, sea
    (1, 2): (2.0,  3.0),   # mega hub, rail
    (1, 3): (1.0,  1.5),   # mega hub, road
    (2, 0): (1.2,  1.5),
    (2, 1): (8.0,  10.0),
    (2, 2): (3.5,  4.5),
    (2, 3): (2.0,  2.5),
    (3, 0): (2.5,  3.0),
    (3, 1): (18.0, 20.0),
    (3, 2): (6.0,  8.0),
    (3, 3): (4.0,  5.0),
}

_MAX_TEU = 47_000_000  # Shanghai


class DelayPredictor:
    """ML delay predictor — auto-trains on synthetic data at startup."""

    def __init__(self, graph):
        self._graph   = graph
        self._model   = None
        self._scaler  = None
        self._trained = False
        self._rng     = random.Random(7)

    # ------------------------------------------------------------------
    def train(self, force=False):
        """Train (or load cached) GBR model on synthetic data."""
        if not _SKLEARN_OK:
            print("[ML] scikit-learn not installed — ML prediction disabled.")
            return

        if not force and os.path.exists(MODEL_PATH):
            try:
                bundle = joblib.load(MODEL_PATH)
                self._model   = bundle["model"]
                self._scaler  = bundle["scaler"]
                self._trained = True
                print(f"[ML] Loaded cached model from {MODEL_PATH}")
                return
            except Exception as e:
                print(f"[ML] Cache load failed ({e}), retraining...")

        print(f"[ML] Generating {N_SYNTHETIC} synthetic training samples...")
        X, y = self._generate_synthetic_data(N_SYNTHETIC)

        scaler = StandardScaler()
        X_sc   = scaler.fit_transform(X)

        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.8,
            min_samples_leaf=10,
            random_state=42,
        )
        model.fit(X_sc, y)

        # Quick cross-validation score
        scores = cross_val_score(model, X_sc, y, cv=3, scoring="r2")
        print(f"[ML] Training complete — R² = {scores.mean():.3f} ± {scores.std():.3f}")

        self._model   = model
        self._scaler  = scaler
        self._trained = True

        try:
            joblib.dump({"model": model, "scaler": scaler}, MODEL_PATH)
            print(f"[ML] Model cached to {MODEL_PATH}")
        except Exception as e:
            print(f"[ML] Could not save model cache: {e}")

    # ------------------------------------------------------------------
    def _generate_synthetic_data(self, n):
        """
        Generate synthetic (feature, delay) pairs using domain knowledge.

        Delay = base_delay * weather_amplification * customs_contribution
                + congestion_factor + temporal_factor + noise
        """
        node_list = list(self._graph.nodes.items())
        modes     = list(_MODE_ENC.keys())

        X_rows, y_vals = [], []

        for _ in range(n):
            # Random source / destination
            nid_f, nf = self._rng.choice(node_list)
            nid_t, nt = self._rng.choice(node_list)
            if nid_f == nid_t:
                continue

            mode = self._rng.choice(modes)
            tier_f = nf.get("tier", 2)
            tier_t = nt.get("tier", 2)

            dist = max(100, abs(nf["lat"] - nt["lat"]) * 111
                       + abs(nf["lon"] - nt["lon"]) * 80)
            dist = min(dist, 22000)

            base_time = dist / {"air": 820, "sea": 38, "rail": 100, "road": 70}[mode]

            # Simulate weather multipliers
            weather_f = self._rng.choice([1.0, 1.0, 1.0, 1.5, 2.0, 2.5, 3.0])
            weather_t = self._rng.choice([1.0, 1.0, 1.0, 1.5, 2.0, 2.5, 3.0])
            # Simulate customs delay
            customs_t = self._rng.choice([0, 0, 0, 6, 12, 24, 36, 48])

            # Throughput ratio (congestion proxy)
            teu_t = nt.get("throughput_teu", 1_000_000)
            thrpt_ratio = teu_t / _MAX_TEU

            hour_of_day = self._rng.randint(0, 23)
            day_of_week = self._rng.randint(0, 6)

            # Compute synthetic delay
            params  = _BASE_DELAY_PARAMS.get((tier_t, _MODE_ENC[mode]),
                                             _BASE_DELAY_PARAMS[(2, 1)])
            mu, sigma = params
            base_delay = max(0, self._rng.gauss(mu, sigma))

            # Weather amplification
            avg_weather = (weather_f + weather_t) / 2
            wx_delay = base_delay * max(0, avg_weather - 1) * 0.7

            # Customs
            customs_delay = customs_t * 0.9

            # Congestion (busier hubs → more congestion delay)
            congestion = thrpt_ratio * 3.0 * self._rng.random()

            # Temporal: weekday morning peak +20%
            temporal = (0.2 * base_delay
                        if (day_of_week < 5 and 7 <= hour_of_day <= 10)
                        else 0)

            # Gaussian noise
            noise = abs(self._rng.gauss(0, 0.5))

            total_delay = base_delay + wx_delay + customs_delay + congestion + temporal + noise

            features = [
                tier_f,
                tier_t,
                _MODE_ENC[mode],
                dist,
                base_time,
                weather_f,
                weather_t,
                customs_t,
                hour_of_day,
                day_of_week,
                thrpt_ratio,
            ]
            X_rows.append(features)
            y_vals.append(round(total_delay, 4))

        return np.array(X_rows), np.array(y_vals)

    # ------------------------------------------------------------------
    def _build_features(self, from_node, to_node, mode, constraint_engine, dt=None):
        """Build feature vector for a single prediction."""
        nodes = self._graph.nodes
        nf    = nodes.get(from_node, {})
        nt    = nodes.get(to_node,   {})

        tier_f = nf.get("tier", 2)
        tier_t = nt.get("tier", 2)

        lat_f, lon_f = nf.get("lat", 0), nf.get("lon", 0)
        lat_t, lon_t = nt.get("lat", 0), nt.get("lon", 0)
        dlat  = math.radians(lat_t - lat_f)
        dlon  = math.radians(lon_t - lon_f)
        a     = math.sin(dlat/2)**2 + (math.cos(math.radians(lat_f))
                                       * math.cos(math.radians(lat_t))
                                       * math.sin(dlon/2)**2)
        dist  = 6371 * 2 * math.asin(math.sqrt(max(0, a)))

        speed = {"air": 820, "sea": 38, "rail": 100, "road": 70}.get(mode, 38)
        base_time = dist / speed

        weather_f  = constraint_engine.weather_multiplier(from_node)
        weather_t  = constraint_engine.weather_multiplier(to_node)
        customs_t  = constraint_engine.customs_delay(to_node)

        teu_t = nt.get("throughput_teu", 1_000_000)
        thrpt = teu_t / _MAX_TEU

        if dt is None:
            dt = datetime.datetime.now()
        hour = dt.hour
        dow  = dt.weekday()

        return np.array([[
            tier_f, tier_t,
            _MODE_ENC.get(mode, 1),
            dist, base_time,
            weather_f, weather_t, customs_t,
            hour, dow, thrpt,
        ]])

    # ------------------------------------------------------------------
    def predict(self, from_node, to_node, mode, constraint_engine, dt=None):
        """
        Predict additional delay for a route segment.

        Returns dict:
          { predicted_delay_h, confidence, breakdown, model_active, features }
        """
        if not self._trained or not _SKLEARN_OK:
            # Fallback: simple heuristic
            return self._heuristic_predict(from_node, to_node, mode, constraint_engine)

        X = self._build_features(from_node, to_node, mode, constraint_engine, dt)
        X_sc = self._scaler.transform(X)

        pred = max(0, float(self._model.predict(X_sc)[0]))

        # Bootstrap confidence from staged predictions
        staged = list(self._model.staged_predict(X_sc))
        if len(staged) >= 10:
            late_preds = [float(p[0]) for p in staged[-50:]]
            cv = (np.std(late_preds) / max(np.mean(late_preds), 0.01))
            confidence = round(max(0.0, min(1.0, 1 - cv)), 2)
        else:
            confidence = 0.75

        nf  = self._graph.nodes.get(from_node, {})
        nt  = self._graph.nodes.get(to_node, {})
        wx_f = constraint_engine.weather_multiplier(from_node)
        wx_t = constraint_engine.weather_multiplier(to_node)
        cus  = constraint_engine.customs_delay(to_node)

        breakdown = {}
        if wx_f > 1.0:
            breakdown["weather_origin"]  = f"+{round((wx_f-1)*pred*0.3,1)}h"
        if wx_t > 1.0:
            breakdown["weather_dest"]    = f"+{round((wx_t-1)*pred*0.4,1)}h"
        if cus > 0:
            breakdown["customs"]         = f"+{cus}h"
        tier_delay = (nt.get("tier", 2) - 1) * pred * 0.1
        if tier_delay > 0.1:
            breakdown["hub_congestion"]  = f"+{round(tier_delay,1)}h"

        return {
            "predicted_delay_h": round(pred, 2),
            "confidence":        confidence,
            "model_active":      True,
            "breakdown":         breakdown,
            "features": {
                "from_hub":  nf.get("name", from_node),
                "to_hub":    nt.get("name", to_node),
                "mode":      mode,
                "weather_multiplier_origin": wx_f,
                "weather_multiplier_dest":   wx_t,
                "customs_delay_h":           cus,
            }
        }

    # ------------------------------------------------------------------
    def _heuristic_predict(self, from_node, to_node, mode, constraint_engine):
        """Fallback heuristic if ML unavailable."""
        nt     = self._graph.nodes.get(to_node, {})
        tier_t = nt.get("tier", 2)
        wx_t   = constraint_engine.weather_multiplier(to_node)
        cus_t  = constraint_engine.customs_delay(to_node)

        base   = {0: 0.5, 1: 5.0, 2: 2.5, 3: 1.5}.get(_MODE_ENC.get(mode, 1), 3.0)
        tier_factor = (tier_t - 1) * 2.0
        wx_factor   = (wx_t - 1.0) * base * 0.5
        pred   = max(0, base * tier_factor * 0.3 + wx_factor + cus_t * 0.8)

        return {
            "predicted_delay_h": round(pred, 2),
            "confidence":        0.50,
            "model_active":      False,
            "breakdown":         {"heuristic": f"+{round(pred,1)}h (estimated)"},
            "features":          {"mode": mode, "to_hub": nt.get("name", to_node)},
        }


# Module-level singleton
_predictor_instance = None


def init_predictor(graph):
    """Called once at startup by app.py."""
    global _predictor_instance
    _predictor_instance = DelayPredictor(graph)
    _predictor_instance.train()
    return _predictor_instance


def get_predictor():
    return _predictor_instance
