"""
engine/scoring.py — Weighted composite score from 8 signal layers.
Weights are configurable in config.py.
"""

import numpy as np
from typing import Dict
from signals.base import SignalResult
from config import SIGNAL_WEIGHTS


def compute_composite_score(signals: Dict[str, SignalResult]) -> float:
    """
    Compute weighted composite score (0–100) from all signal results.
    Missing signals are excluded from the weight total.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    key_map = {
        "trend":         "trend",
        "momentum":      "momentum",
        "volatility":    "volatility",
        "credit":        "credit",
        "liquidity":     "liquidity",
        "rates":         "rates",
        "risk_appetite": "risk_appetite",
        "breadth":       "breadth",
    }

    for key, signal_key in key_map.items():
        weight = SIGNAL_WEIGHTS.get(key, 0.0)
        signal = signals.get(signal_key)
        if signal is None:
            continue
        if signal.data_quality == "No Data":
            continue  # skip fully missing signals

        weighted_sum += signal.score * weight
        total_weight += weight

    if total_weight == 0:
        return 50.0  # fallback neutral

    return float(np.clip(weighted_sum / total_weight, 0, 100))


def score_summary_table(signals: Dict[str, SignalResult]) -> list:
    """Return a list of dicts suitable for a DataFrame display."""
    rows = []
    for key, signal in signals.items():
        weight_pct = int(SIGNAL_WEIGHTS.get(key, 0) * 100)
        rows.append({
            "Signal": signal.name,
            "Score": round(signal.score, 1),
            "Direction": signal.direction,
            "Confidence": signal.confidence,
            "Weight": f"{weight_pct}%",
            "Data": signal.data_quality,
        })
    return rows
