"""
signals/trend.py — Trend signal layer.

Evaluates whether major indices are above key moving averages.
Above = bullish environment; below 200DMA = major warning.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import compute_dma, latest, ratio_series


def score_trend(prices: dict) -> SignalResult:
    """
    Inputs:
    - SPY vs 20/50/200 DMA
    - QQQ vs 50/200 DMA
    - ACWI vs 200 DMA
    - RSP/SPY ratio (breadth proxy)

    Scoring logic: each condition is worth a fixed number of points.
    """
    points = 0.0
    max_points = 0.0
    drivers = []
    available = 0
    total = 7  # number of checks

    def _check(series: pd.Series, window: int, ticker: str) -> float:
        """Returns 1 if price > DMA, 0 otherwise. NaN if data missing."""
        s = series.dropna()
        if len(s) < window:
            return float("nan")
        dma = compute_dma(s, window)
        price_now = s.iloc[-1]
        dma_now = dma.iloc[-1]
        if np.isnan(dma_now):
            return float("nan")
        return 1.0 if price_now > dma_now else 0.0

    spy = prices.get("SPY", pd.Series(dtype=float))
    qqq = prices.get("QQQ", pd.Series(dtype=float))
    acwi = prices.get("ACWI", pd.Series(dtype=float))
    rsp = prices.get("RSP", pd.Series(dtype=float))

    # SPY checks — weighted higher because it's the primary index
    for window, label, weight in [(20, "20DMA", 10), (50, "50DMA", 15), (200, "200DMA", 25)]:
        result = _check(spy, window, "SPY")
        max_points += weight
        if not np.isnan(result):
            available += 1
            pts = result * weight
            points += pts
            above_below = "above" if result else "BELOW"
            drivers.append(f"SPY {above_below} {label} ({label})")
        else:
            drivers.append(f"SPY vs {label}: no data")

    # QQQ checks
    for window, label, weight in [(50, "50DMA", 10), (200, "200DMA", 15)]:
        result = _check(qqq, window, "QQQ")
        max_points += weight
        if not np.isnan(result):
            available += 1
            pts = result * weight
            points += pts
            above_below = "above" if result else "BELOW"
            drivers.append(f"QQQ {above_below} {label}")

    # ACWI check
    result_acwi = _check(acwi, 200, "ACWI")
    max_points += 15
    if not np.isnan(result_acwi):
        available += 1
        points += result_acwi * 15
        above_below = "above" if result_acwi else "BELOW"
        drivers.append(f"ACWI {above_below} 200DMA")
    else:
        drivers.append("ACWI vs 200DMA: no data")

    # RSP/SPY ratio trend (equal-weight vs cap-weight)
    rsp_spy = ratio_series(rsp, spy)
    max_points += 10
    if len(rsp_spy) >= 20:
        available += 1
        rsp_spy_20 = rsp_spy.rolling(20).mean()
        current_ratio = rsp_spy.iloc[-1]
        sma20 = rsp_spy_20.iloc[-1]
        if not np.isnan(sma20):
            is_rising = current_ratio > sma20
            points += 10 * (1 if is_rising else 0)
            drivers.append(f"RSP/SPY {'rising' if is_rising else 'falling'} (breadth healthy)" if is_rising else "RSP/SPY falling (breadth narrowing)")

    # Normalize to 0–100
    score = clamp((points / max_points) * 100 if max_points > 0 else 50)

    # SPY below 200DMA is a major drag — hard penalty
    spy_below_200 = _check(spy, 200, "SPY")
    if not np.isnan(spy_below_200) and spy_below_200 == 0:
        score = min(score, 35)  # cap trend score at 35 if SPY below 200DMA

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)

    explanation = _build_explanation(score, spy_below_200, direction)
    drivers = [d for d in drivers if "no data" not in d][:5]

    return SignalResult(
        name="Trend",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers,
        data_quality="OK" if available >= 4 else ("Partial" if available >= 2 else "No Data"),
    )


def _build_explanation(score: float, spy_below_200: float, direction: str) -> str:
    if not np.isnan(spy_below_200) and spy_below_200 == 0:
        return "SPY below 200DMA — primary trend is broken. Major caution."
    if score >= 80:
        return "All major indices trading above key moving averages. Trend is strongly intact."
    elif score >= 60:
        return "Most indices above key DMA levels. Trend is supportive but not perfect."
    elif score >= 40:
        return "Mixed trend signals. Some indices above, some below key moving averages."
    else:
        return "Trend is deteriorating. Multiple indices breaking below key moving averages."


def get_spy_below_200dma(prices: dict) -> bool:
    """Used by veto engine."""
    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    if len(spy) < 200:
        return False
    dma200 = spy.rolling(200).mean().iloc[-1]
    return bool(spy.iloc[-1] < dma200)
