"""
signals/credit.py — Credit Stress signal layer.

HY/IG spread levels and direction are the primary stress indicators.
KRE/SPY ratio is an early-warning regional bank stress proxy.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import latest, ratio_series
from config import HY_SPREAD_WIDE, HY_SPREAD_NORMAL, HY_SPIKE_20D


def score_credit(prices: dict, fred_data: dict) -> SignalResult:
    """
    Inputs:
    - HY spread (FRED: BAMLH0A0HYM2)
    - IG spread (FRED: BAMLC0A0CM)
    - HYG/LQD ratio
    - KRE/SPY ratio
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 4

    component_scores = []

    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    hyg = prices.get("HYG", pd.Series(dtype=float)).dropna()
    lqd = prices.get("LQD", pd.Series(dtype=float)).dropna()
    kre = prices.get("KRE", pd.Series(dtype=float)).dropna()
    hy_spread = fred_data.get("hy_spread", pd.Series(dtype=float)).dropna()
    ig_spread = fred_data.get("ig_spread", pd.Series(dtype=float)).dropna()

    # ── HY Spread Level ─────────────────────────────────────────────────────────
    hy_now = latest(hy_spread) if not hy_spread.empty else float("nan")
    if not np.isnan(hy_now):
        available += 1
        hy_score = _spread_to_score(hy_now, HY_SPREAD_NORMAL, HY_SPREAD_WIDE)
        component_scores.append(("HY Spread", hy_score, 0.35))
        sub_scores["HY Spread (bps)"] = hy_now
        stress = "wide (stressed)" if hy_now > HY_SPREAD_WIDE else "normal"
        drivers.append(f"HY OAS spread: {hy_now:.0f}bps ({stress})")

        # Check 20D widening for veto
        if len(hy_spread) >= 21:
            hy_20d_ago = hy_spread.dropna().iloc[-21]
            hy_change_20d = hy_now - hy_20d_ago
            if hy_change_20d > HY_SPIKE_20D:
                hy_score = min(hy_score, 25)  # severe penalty
                drivers.append(f"HY widened sharply: +{hy_change_20d:.0f}bps in 20 days — VETO condition")
            else:
                sign = "+" if hy_change_20d > 0 else ""
                drivers.append(f"HY 20D change: {sign}{hy_change_20d:.0f}bps (spreading {'wider' if hy_change_20d > 0 else 'tighter'})")

    # ── IG Spread ───────────────────────────────────────────────────────────────
    ig_now = latest(ig_spread) if not ig_spread.empty else float("nan")
    if not np.isnan(ig_now):
        available += 1
        ig_score = _spread_to_score(ig_now, 100, 200)
        component_scores.append(("IG Spread", ig_score, 0.20))
        sub_scores["IG Spread (bps)"] = ig_now
        drivers.append(f"IG OAS spread: {ig_now:.0f}bps ({'elevated' if ig_now > 150 else 'normal'})")

    # ── HYG/LQD Ratio ──────────────────────────────────────────────────────────
    hyg_lqd = ratio_series(hyg, lqd)
    if len(hyg_lqd) >= 20:
        available += 1
        hyg_lqd_20 = hyg_lqd.rolling(20).mean()
        current = hyg_lqd.iloc[-1]
        sma20 = hyg_lqd_20.iloc[-1]
        if not np.isnan(sma20):
            ratio_score = 70 if current > sma20 else 35
            component_scores.append(("HYG/LQD", ratio_score, 0.25))
            sub_scores["HYG/LQD Ratio"] = round(current, 4)
            direction_str = "above" if current > sma20 else "below"
            drivers.append(f"HYG/LQD ratio {direction_str} 20DMA ({'bullish credit' if current > sma20 else 'credit stress'})")

    # ── KRE/SPY Ratio ──────────────────────────────────────────────────────────
    kre_spy = ratio_series(kre, spy)
    if len(kre_spy) >= 20:
        available += 1
        kre_spy_20 = kre_spy.rolling(20).mean()
        current_kre = kre_spy.iloc[-1]
        sma20_kre = kre_spy_20.iloc[-1]
        if not np.isnan(sma20_kre):
            kre_score = 65 if current_kre > sma20_kre else 35
            component_scores.append(("KRE/SPY", kre_score, 0.20))
            sub_scores["KRE/SPY"] = round(current_kre, 4)
            direction_str = "above" if current_kre > sma20_kre else "BELOW"
            drivers.append(f"KRE/SPY {direction_str} 20DMA ({'healthy' if current_kre > sma20_kre else 'bank/credit stress warning'})")

    # ── Composite ───────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight
    score = clamp(score)

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)
    explanation = _build_explanation(score, hy_now)

    return SignalResult(
        name="Credit",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 3 else ("Partial" if available >= 1 else "No Data"),
    )


def _spread_to_score(spread: float, normal: float, wide: float) -> float:
    """Map spread level to 0–100 score. Tighter = higher score."""
    if spread < normal * 0.7:
        return 90
    elif spread < normal:
        return 75
    elif spread < (normal + wide) / 2:
        return 55
    elif spread < wide:
        return 35
    else:
        return 15


def _build_explanation(score: float, hy: float) -> str:
    if np.isnan(hy):
        return "Credit signal is running on limited data. Using ETF proxies only."
    if score >= 70:
        return f"Credit conditions healthy. HY spreads at {hy:.0f}bps — no stress signals."
    elif score >= 55:
        return f"Credit OK. HY spreads at {hy:.0f}bps — watching for widening."
    elif score >= 40:
        return f"Credit caution. Spreads at {hy:.0f}bps. Some stress indicators active."
    else:
        return f"Credit stress. HY spreads at {hy:.0f}bps. Systemic risk indicators elevated."


def get_hy_widening_veto(fred_data: dict) -> bool:
    """Returns True if HY spreads have widened sharply over 20 days."""
    hy = fred_data.get("hy_spread", pd.Series(dtype=float)).dropna()
    if len(hy) < 21:
        return False
    change_20d = float(hy.iloc[-1]) - float(hy.iloc[-21])
    return change_20d > HY_SPIKE_20D
