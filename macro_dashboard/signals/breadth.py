"""
signals/breadth.py — Market Breadth signal layer.

Broad participation is healthy. Mega-cap-only rallies are warning signs.
RSP/SPY and IWM/SPY are the primary breadth ETF proxies.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import latest, ratio_series


def score_breadth(prices: dict) -> SignalResult:
    """
    Inputs:
    - RSP/SPY ratio (equal-weight vs cap-weight)
    - IWM/SPY ratio (small caps vs large caps)
    - Placeholders for NYSE A/D and % above 200DMA (data unavailable via free API)
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 4
    component_scores = []

    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    rsp = prices.get("RSP", pd.Series(dtype=float)).dropna()
    iwm = prices.get("IWM", pd.Series(dtype=float)).dropna()

    # ── RSP/SPY Ratio ─────────────────────────────────────────────────────────────
    rsp_spy = ratio_series(rsp, spy)
    if len(rsp_spy) >= 20:
        available += 1
        current = rsp_spy.iloc[-1]
        sma20 = rsp_spy.rolling(20).mean().iloc[-1]
        sma50 = rsp_spy.rolling(50).mean().iloc[-1] if len(rsp_spy) >= 50 else float("nan")
        if not np.isnan(sma20):
            above_20 = current > sma20
            above_50 = current > sma50 if not np.isnan(sma50) else above_20
            rsp_score = 75 if (above_20 and above_50) else 55 if above_20 else 30
            component_scores.append(("RSP/SPY", rsp_score, 0.40))
            sub_scores["RSP/SPY (equal-weight)"] = round(current, 4)

            trend = "rising (broad market)" if above_20 else "falling (narrowing)"
            drivers.append(f"RSP/SPY {trend} — {'equal-weight outperforming' if above_20 else 'cap-weight dominating'}")

    # ── IWM/SPY Ratio ─────────────────────────────────────────────────────────────
    iwm_spy = ratio_series(iwm, spy)
    if len(iwm_spy) >= 20:
        available += 1
        current_iwm = iwm_spy.iloc[-1]
        sma20_iwm = iwm_spy.rolling(20).mean().iloc[-1]
        if not np.isnan(sma20_iwm):
            above_20_iwm = current_iwm > sma20_iwm
            iwm_score = 70 if above_20_iwm else 35
            component_scores.append(("IWM/SPY", iwm_score, 0.35))
            sub_scores["IWM/SPY (small caps)"] = round(current_iwm, 4)
            drivers.append(
                f"Small caps {'outperforming' if above_20_iwm else 'underperforming'} large caps "
                f"({'healthy breadth' if above_20_iwm else 'large-cap-only rally warning'})"
            )

    # ── Breadth Divergence Check ──────────────────────────────────────────────────
    # If SPY rising but RSP/SPY falling = narrowing / cap-weighted distortion
    spy_1m = _series_roc(spy, 21)
    rsp_spy_1m = _series_roc(rsp_spy, 21) if len(rsp_spy) >= 22 else float("nan")

    breadth_divergence = False
    if not np.isnan(spy_1m) and not np.isnan(rsp_spy_1m):
        available += 1
        breadth_divergence = spy_1m > 2 and rsp_spy_1m < -1
        if breadth_divergence:
            component_scores.append(("Divergence", 20, 0.25))
            drivers.append(f"DIVERGENCE: SPY +{spy_1m:.1f}% but RSP/SPY {rsp_spy_1m:+.1f}% — narrow rally")
        else:
            component_scores.append(("Divergence", 65, 0.25))
            drivers.append(f"No breadth divergence detected — participation healthy")
        sub_scores["Breadth Divergence"] = "Yes" if breadth_divergence else "No"

    # ── % Above 200DMA Placeholder ────────────────────────────────────────────────
    drivers.append("NYSE A/D + % above 200DMA: placeholder (requires premium data feed)")

    # ── Composite ────────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight
    score = clamp(score)

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)
    explanation = _build_explanation(score, breadth_divergence)

    return SignalResult(
        name="Breadth",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 2 else ("Partial" if available >= 1 else "No Data"),
    )


def _series_roc(s: pd.Series, period: int) -> float:
    """Simple % change over period."""
    clean = s.dropna()
    if len(clean) < period + 1:
        return float("nan")
    return (clean.iloc[-1] / clean.iloc[-period - 1] - 1) * 100


def _build_explanation(score: float, divergence: bool) -> str:
    if divergence:
        return "Breadth divergence: SPY rising but equal-weight lagging. Narrow rally — late-cycle warning."
    elif score >= 65:
        return "Broad market participation. Small caps and equal-weight confirming upside."
    elif score >= 50:
        return "Breadth is acceptable but not exceptional. Some narrowing at the edges."
    elif score >= 35:
        return "Breadth deteriorating. Small caps underperforming; rally becoming concentrated."
    else:
        return "Narrow market. Only mega-caps holding up. High divergence risk."


def get_breadth_divergence(prices: dict) -> bool:
    """Returns True if SPY rising but RSP/SPY falling (breadth narrowing)."""
    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    rsp = prices.get("RSP", pd.Series(dtype=float)).dropna()
    rsp_spy = ratio_series(rsp, spy)
    spy_1m = _series_roc(spy, 21)
    rsp_spy_1m = _series_roc(rsp_spy, 21) if len(rsp_spy) >= 22 else float("nan")
    if np.isnan(spy_1m) or np.isnan(rsp_spy_1m):
        return False
    return spy_1m > 2 and rsp_spy_1m < -1
