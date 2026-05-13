"""
signals/rates.py — Rates Regime signal layer.

Real yield direction is the most important signal for growth equities.
Rising real yields compress multiples; a steepening curve from inversion is nuanced.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import latest
from config import REAL_YIELD_SPIKE


def score_rates(fred_data: dict) -> SignalResult:
    """
    Inputs:
    - US10Y: DGS10
    - US2Y: DGS2
    - Real yield: DFII10
    - 2s10s curve
    - 3m10y curve
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 5
    component_scores = []

    us10y = fred_data.get("us10y", pd.Series(dtype=float)).dropna()
    us2y  = fred_data.get("us2y",  pd.Series(dtype=float)).dropna()
    us3m  = fred_data.get("us3m",  pd.Series(dtype=float)).dropna()
    real10y = fred_data.get("real_yield_10y", pd.Series(dtype=float)).dropna()

    # ── 10Y Real Yield ───────────────────────────────────────────────────────────
    real_now = latest(real10y)
    if not np.isnan(real_now):
        available += 1
        # Negative real yields = very bullish; positive and rising = bearish
        real_score = clamp(70 - real_now * 20)  # at 0% real → 70; at +2% → 30
        component_scores.append(("Real Yield", real_score, 0.40))
        sub_scores["10Y Real Yield (%)"] = round(real_now, 2)
        drivers.append(
            f"10Y real yield: {real_now:+.2f}% "
            f"({'negative — supportive of growth equities' if real_now < 0 else 'positive — headwind for duration'})"
        )

        # 20D real yield change
        if len(real10y) >= 21:
            real_20d_ago = float(real10y.iloc[-21])
            real_change = real_now - real_20d_ago
            if real_change > REAL_YIELD_SPIKE:
                real_score = min(real_score, 20)
                drivers.append(f"Real yields spiked +{real_change:.2f}pp in 20 days — VETO risk")
            else:
                sign = "+" if real_change > 0 else ""
                drivers.append(f"Real yield 20D change: {sign}{real_change:.2f}pp")

    # ── 2s10s Curve ─────────────────────────────────────────────────────────────
    ten_y = latest(us10y)
    two_y = latest(us2y)
    if not np.isnan(ten_y) and not np.isnan(two_y):
        available += 1
        curve_2s10s = (ten_y - two_y) * 100  # bps
        # Steepening = more positive; deeply inverted = bearish (but from growth scare angle)
        # We penalise inverted curve, but not deeply inverted in isolation (could be rate-cut cycle)
        curve_score = _curve_score(curve_2s10s)
        component_scores.append(("2s10s", curve_score, 0.25))
        sub_scores["2s10s Curve (bps)"] = round(curve_2s10s, 1)
        status = "normal" if curve_2s10s > 0 else "inverted"
        drivers.append(f"2s10s curve: {curve_2s10s:+.0f}bps ({status})")

    # ── 3m10y Curve ─────────────────────────────────────────────────────────────
    three_m = latest(us3m)
    if not np.isnan(three_m) and not np.isnan(ten_y):
        available += 1
        curve_3m10y = (ten_y - three_m) * 100
        curve_3m_score = _curve_score(curve_3m10y)
        component_scores.append(("3m10y", curve_3m_score, 0.20))
        sub_scores["3m10y Curve (bps)"] = round(curve_3m10y, 1)
        status = "normal" if curve_3m10y > 0 else "inverted"
        drivers.append(f"3m10y curve: {curve_3m10y:+.0f}bps ({status})")

    # ── 10Y Nominal Level ────────────────────────────────────────────────────────
    if not np.isnan(ten_y):
        available += 1
        # High rates (>5%) are headwinds; very low (<2%) can be growth scare signal
        nominal_score = _nominal_yield_score(ten_y)
        component_scores.append(("10Y Nom", nominal_score, 0.15))
        sub_scores["10Y Yield (%)"] = round(ten_y, 2)
        drivers.append(f"10Y nominal yield: {ten_y:.2f}% ({'high' if ten_y > 5 else 'moderate' if ten_y > 3.5 else 'low'})")

    # ── Composite ────────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight
    score = clamp(score)

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)
    explanation = _build_explanation(score, real_now if not np.isnan(real_now) else float("nan"))

    return SignalResult(
        name="Rates",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 3 else ("Partial" if available >= 1 else "No Data"),
    )


def _curve_score(bps: float) -> float:
    """Positive (steep) curve = more bullish. Inverted = bearish."""
    if bps > 100:
        return 75
    elif bps > 50:
        return 65
    elif bps > 0:
        return 55
    elif bps > -50:
        return 40
    elif bps > -100:
        return 30
    else:
        return 20


def _nominal_yield_score(yield_pct: float) -> float:
    """Map 10Y yield to score. Very high = bad for equities."""
    if yield_pct < 2.0:
        return 45  # low yields = growth scare
    elif yield_pct < 3.5:
        return 70
    elif yield_pct < 4.5:
        return 55
    elif yield_pct < 5.5:
        return 35
    else:
        return 20


def _build_explanation(score: float, real_yield: float) -> str:
    if np.isnan(real_yield):
        return "Rates signal running on limited data."
    if real_yield < -0.5 and score > 60:
        return f"Real yields negative at {real_yield:.2f}%. Supportive of growth equity multiples."
    elif real_yield > 1.5:
        return f"Real yields elevated at {real_yield:.2f}%. Headwind for long-duration growth equities."
    elif score >= 55:
        return f"Rates environment broadly supportive. Real yield: {real_yield:.2f}%."
    else:
        return f"Rates regime is a headwind. Real yield {real_yield:.2f}% and curve positioning unclear."


def get_real_yield_dxy_veto(fred_data: dict, prices: dict) -> bool:
    """
    Returns True if both real yields AND DXY are rising sharply (dual tightening veto).
    """
    from data.market_data import compute_roc
    from config import DXY_STRONG_20D

    real10y = fred_data.get("real_yield_10y", pd.Series(dtype=float)).dropna()
    uup = prices.get("UUP", pd.Series(dtype=float)).dropna()

    real_rising = False
    dxy_rising = False

    if len(real10y) >= 21:
        real_change = float(real10y.iloc[-1]) - float(real10y.iloc[-21])
        real_rising = real_change > REAL_YIELD_SPIKE

    if len(uup) >= 21:
        uup_roc = compute_roc(uup, 20)
        dxy_rising = not np.isnan(uup_roc) and uup_roc > DXY_STRONG_20D

    return real_rising and dxy_rising
