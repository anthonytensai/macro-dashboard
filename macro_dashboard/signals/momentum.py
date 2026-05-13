"""
signals/momentum.py — Momentum signal layer.

Evaluates rate-of-change across SPY, QQQ, SMH.
Key distinction: acceleration (speed of move) matters as much as direction.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import compute_roc, latest


def score_momentum(prices: dict) -> SignalResult:
    """
    Inputs:
    - SPY 1M and 3M ROC
    - QQQ 1M and 3M ROC
    - Momentum acceleration: recent ROC vs prior ROC
    - SMH/SOXX as risk proxy

    Logic:
    - Positive + accelerating → bullish
    - Positive + decelerating → neutral/slight bullish
    - Negative + accelerating down → bearish
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 5

    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    qqq = prices.get("QQQ", pd.Series(dtype=float)).dropna()
    smh = prices.get("SMH", pd.Series(dtype=float)).dropna()

    component_scores = []

    # ── SPY momentum ──────────────────────────────────────────────────────────
    spy_1m = compute_roc(spy, 21)
    spy_3m = compute_roc(spy, 63)
    if not np.isnan(spy_1m) and not np.isnan(spy_3m):
        available += 1
        spy_score = _roc_to_score(spy_1m, spy_3m)
        component_scores.append(("SPY", spy_score, 0.35))
        accel = "accelerating" if abs(spy_1m) > abs(spy_3m / 3) else "decelerating"
        drivers.append(f"SPY 1M: {spy_1m:+.1f}%, 3M: {spy_3m:+.1f}% ({accel})")
        sub_scores["SPY"] = spy_score

    # ── QQQ momentum ──────────────────────────────────────────────────────────
    qqq_1m = compute_roc(qqq, 21)
    qqq_3m = compute_roc(qqq, 63)
    if not np.isnan(qqq_1m) and not np.isnan(qqq_3m):
        available += 1
        qqq_score = _roc_to_score(qqq_1m, qqq_3m)
        component_scores.append(("QQQ", qqq_score, 0.30))
        accel = "accelerating" if abs(qqq_1m) > abs(qqq_3m / 3) else "decelerating"
        drivers.append(f"QQQ 1M: {qqq_1m:+.1f}%, 3M: {qqq_3m:+.1f}% ({accel})")
        sub_scores["QQQ"] = qqq_score

    # ── Momentum acceleration (SPY) ───────────────────────────────────────────
    # Compare most recent 1M ROC vs prior 1M ROC (lagged by 21 days)
    if len(spy) >= 63:
        available += 1
        spy_1m_prior = compute_roc(spy.iloc[:-21], 21) if len(spy) > 42 else float("nan")
        if not np.isnan(spy_1m_prior) and not np.isnan(spy_1m):
            accel_delta = spy_1m - spy_1m_prior
            accel_score = 70 if accel_delta > 0 else 35
            component_scores.append(("Accel", accel_score, 0.15))
            sub_scores["Acceleration"] = accel_score
            drivers.append(
                f"Momentum acceleration: {accel_delta:+.1f}pp vs prior month "
                f"({'positive' if accel_delta > 0 else 'negative'})"
            )

    # ── SMH as risk appetite proxy ─────────────────────────────────────────────
    smh_1m = compute_roc(smh, 21)
    smh_3m = compute_roc(smh, 63)
    if not np.isnan(smh_1m):
        available += 1
        smh_score = _roc_to_score(smh_1m, smh_3m if not np.isnan(smh_3m) else smh_1m)
        component_scores.append(("SMH", smh_score, 0.20))
        sub_scores["SMH (Semis)"] = smh_score
        drivers.append(f"SMH semis 1M: {smh_1m:+.1f}% ({'strong risk appetite' if smh_1m > 3 else 'weak' if smh_1m < -3 else 'flat'})")

    # ── Composite ─────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight
    score = clamp(score)

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)

    explanation = _build_explanation(score, component_scores)

    return SignalResult(
        name="Momentum",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 3 else ("Partial" if available >= 1 else "No Data"),
    )


def _roc_to_score(roc_1m: float, roc_3m: float) -> float:
    """
    Convert 1M and 3M ROC to a 0–100 score.
    Both positive + 1M > 3M/3 = accelerating → high score.
    """
    base = 50.0
    # 1M ROC contribution: each +5% moves score by ~15 points
    roc_contribution = np.clip(roc_1m * 3, -40, 40)
    # Acceleration bonus/penalty
    monthly_equiv_3m = roc_3m / 3 if roc_3m != 0 else 0
    accel = roc_1m - monthly_equiv_3m
    accel_contribution = np.clip(accel * 2, -10, 10)
    return clamp(base + roc_contribution + accel_contribution)


def _build_explanation(score: float, components: list) -> str:
    if score >= 75:
        return "Momentum is strong and broad. Multiple assets showing positive, accelerating ROC."
    elif score >= 60:
        return "Momentum is positive. Some acceleration but not broad-based."
    elif score >= 45:
        return "Momentum is mixed or decelerating. No clear directional push."
    elif score >= 30:
        return "Momentum is fading. ROC turning negative across key assets."
    else:
        return "Momentum is sharply negative. Accelerating selling pressure."
