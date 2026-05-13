"""
signals/volatility.py — Volatility Regime signal layer.

VIX level, direction, and term structure are the primary inputs.
Backwardation is a hard veto trigger.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import compute_roc, latest
from config import VIX_LOW, VIX_ELEVATED, VIX_SPIKE_5D


def score_volatility(prices: dict) -> SignalResult:
    """
    Inputs:
    - VIX level (^VIX)
    - VIX 5D and 20D change
    - VIX term structure: VIX3M / VIX (if available)
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 4

    vix = prices.get("^VIX", pd.Series(dtype=float)).dropna()
    vix3m = prices.get("^VIX3M", pd.Series(dtype=float)).dropna()

    component_scores = []

    # ── VIX Level ──────────────────────────────────────────────────────────────
    vix_now = latest(vix) if not vix.empty else float("nan")
    if not np.isnan(vix_now):
        available += 1
        level_score = _vix_level_score(vix_now)
        component_scores.append(("VIX Level", level_score, 0.45))
        sub_scores["VIX Level"] = level_score
        drivers.append(f"VIX at {vix_now:.1f} ({'low' if vix_now < VIX_LOW else 'elevated' if vix_now < VIX_ELEVATED else 'HIGH'})")
    else:
        vix_now = 20.0  # neutral fallback
        drivers.append("VIX: no data (using neutral 20 fallback)")

    # ── VIX 5D Change ──────────────────────────────────────────────────────────
    vix_5d = compute_roc(vix, 5) if len(vix) >= 6 else float("nan")
    if not np.isnan(vix_5d):
        available += 1
        change_5d_score = 70 - vix_5d * 3  # rising VIX → lower score
        component_scores.append(("VIX 5D Chg", clamp(change_5d_score), 0.20))
        sub_scores["VIX 5D Change"] = clamp(change_5d_score)
        sign = "+" if vix_5d > 0 else ""
        drivers.append(f"VIX 5D change: {sign}{vix_5d:.1f}% ({'rising' if vix_5d > VIX_SPIKE_5D else 'falling' if vix_5d < -VIX_SPIKE_5D else 'flat'})")

    # ── VIX 20D Change ─────────────────────────────────────────────────────────
    vix_20d = compute_roc(vix, 20) if len(vix) >= 21 else float("nan")
    if not np.isnan(vix_20d):
        available += 1
        change_20d_score = 65 - vix_20d * 2
        component_scores.append(("VIX 20D Chg", clamp(change_20d_score), 0.15))
        sub_scores["VIX 20D Change"] = clamp(change_20d_score)
        sign = "+" if vix_20d > 0 else ""
        drivers.append(f"VIX 20D change: {sign}{vix_20d:.1f}%")

    # ── VIX Term Structure (VIX3M / VIX) ───────────────────────────────────────
    backwardation = False
    vix3m_now = latest(vix3m) if not vix3m.empty else float("nan")
    if not np.isnan(vix3m_now) and not np.isnan(vix_now):
        available += 1
        ts_ratio = vix3m_now / vix_now
        backwardation = ts_ratio < 1.0  # front > back = backwardation = stress
        ts_score = 80 if ts_ratio > 1.05 else 50 if ts_ratio > 0.95 else 20
        component_scores.append(("Term Structure", ts_score, 0.20))
        sub_scores["VIX Term Structure"] = ts_score
        structure = "contango (healthy)" if ts_ratio > 1.0 else "BACKWARDATION (stress)"
        drivers.append(f"VIX term structure: {ts_ratio:.2f} — {structure}")
    else:
        drivers.append("VIX3M: not available (term structure skipped)")

    # ── Composite ──────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight

    # Hard backwardation penalty
    if backwardation:
        score = min(score, 30)

    score = clamp(score)
    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)
    explanation = _build_explanation(score, vix_now, backwardation)

    return SignalResult(
        name="Volatility",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 2 else ("Partial" if available >= 1 else "No Data"),
    )


def _vix_level_score(vix: float) -> float:
    """Map VIX level to a 0–100 score. Lower VIX = higher score."""
    if vix < 13:
        return 95
    elif vix < VIX_LOW:   # < 18
        return 80
    elif vix < 22:
        return 60
    elif vix < VIX_ELEVATED:  # < 25
        return 45
    elif vix < 30:
        return 30
    elif vix < 40:
        return 15
    else:
        return 5


def _build_explanation(score: float, vix: float, backwardation: bool) -> str:
    if backwardation:
        return f"VIX in BACKWARDATION at {vix:.1f}. Severe near-term stress. Hard veto condition."
    elif vix < VIX_LOW:
        return f"VIX at {vix:.1f} — low vol regime. Conditions supportive of risk-taking."
    elif vix < VIX_ELEVATED:
        return f"VIX at {vix:.1f} — elevated but manageable. Proceed with caution."
    else:
        return f"VIX at {vix:.1f} — high volatility regime. Risk-off caution warranted."


def get_vix_backwardation(prices: dict) -> bool:
    """Used by the veto engine to check backwardation."""
    vix = prices.get("^VIX", pd.Series(dtype=float)).dropna()
    vix3m = prices.get("^VIX3M", pd.Series(dtype=float)).dropna()
    v = latest(vix)
    v3 = latest(vix3m)
    if np.isnan(v) or np.isnan(v3):
        return False
    return v3 < v  # front term > back term = backwardation
