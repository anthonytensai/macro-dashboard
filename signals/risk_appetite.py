"""
signals/risk_appetite.py — Risk Appetite signal layer.

BTC, semis vs utilities, and discretionary vs staples are classic
risk-on/risk-off thermometers. Gold/SPY rising = defensive rotation.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import compute_dma, latest, ratio_series


def score_risk_appetite(prices: dict) -> SignalResult:
    """
    Inputs:
    - BTC-USD vs 50/200 DMA
    - Gold/SPY ratio (GLD/SPY)
    - Semis vs utilities: SMH/XLU
    - Consumer discretionary vs staples: XLY/XLP
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 6
    component_scores = []

    btc = prices.get("BTC-USD", pd.Series(dtype=float)).dropna()
    gld = prices.get("GLD", pd.Series(dtype=float)).dropna()
    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    smh = prices.get("SMH", pd.Series(dtype=float)).dropna()
    xlu = prices.get("XLU", pd.Series(dtype=float)).dropna()
    xly = prices.get("XLY", pd.Series(dtype=float)).dropna()
    xlp = prices.get("XLP", pd.Series(dtype=float)).dropna()

    # ── BTC vs 50DMA ─────────────────────────────────────────────────────────────
    if len(btc) >= 50:
        available += 1
        dma50 = compute_dma(btc, 50).iloc[-1]
        btc_now = btc.iloc[-1]
        above = btc_now > dma50
        btc_50_score = 70 if above else 30
        component_scores.append(("BTC 50DMA", btc_50_score, 0.15))
        sub_scores["BTC vs 50DMA"] = "above" if above else "below"
        drivers.append(f"BTC {'above' if above else 'BELOW'} 50DMA (${btc_now:,.0f} vs ${dma50:,.0f})")

    # ── BTC vs 200DMA ────────────────────────────────────────────────────────────
    if len(btc) >= 200:
        available += 1
        dma200 = compute_dma(btc, 200).iloc[-1]
        btc_now = btc.iloc[-1]
        above = btc_now > dma200
        btc_200_score = 75 if above else 25
        component_scores.append(("BTC 200DMA", btc_200_score, 0.15))
        sub_scores["BTC vs 200DMA"] = "above" if above else "below"
        drivers.append(f"BTC {'above' if above else 'BELOW'} 200DMA (${dma200:,.0f})")

    # ── Gold/SPY Ratio ────────────────────────────────────────────────────────────
    gld_spy = ratio_series(gld, spy)
    if len(gld_spy) >= 20:
        available += 1
        gld_spy_20 = gld_spy.rolling(20).mean()
        current_ratio = gld_spy.iloc[-1]
        sma20 = gld_spy_20.iloc[-1]
        if not np.isnan(sma20):
            # Gold outperforming = defensive rotation = bearish risk appetite
            gold_rising = current_ratio > sma20
            gold_score = 30 if gold_rising else 70  # inverse signal
            component_scores.append(("GLD/SPY", gold_score, 0.25))
            sub_scores["GLD/SPY Ratio"] = round(current_ratio, 4)
            drivers.append(
                f"Gold/SPY ratio {'rising' if gold_rising else 'falling'} "
                f"({'defensive rotation — caution' if gold_rising else 'equities preferred over gold'})"
            )

    # ── SMH/XLU Ratio ─────────────────────────────────────────────────────────────
    smh_xlu = ratio_series(smh, xlu)
    if len(smh_xlu) >= 20:
        available += 1
        current_smh_xlu = smh_xlu.iloc[-1]
        sma20_smh_xlu = smh_xlu.rolling(20).mean().iloc[-1]
        if not np.isnan(sma20_smh_xlu):
            outperform = current_smh_xlu > sma20_smh_xlu
            smh_score = 75 if outperform else 30
            component_scores.append(("SMH/XLU", smh_score, 0.20))
            sub_scores["SMH/XLU"] = round(current_smh_xlu, 4)
            drivers.append(
                f"Semis/Utilities: {'Semis outperforming (risk-on)' if outperform else 'Utilities outperforming (defensive)'}"
            )

    # ── XLY/XLP Ratio ──────────────────────────────────────────────────────────────
    xly_xlp = ratio_series(xly, xlp)
    if len(xly_xlp) >= 20:
        available += 1
        current_xly = xly_xlp.iloc[-1]
        sma20_xly = xly_xlp.rolling(20).mean().iloc[-1]
        if not np.isnan(sma20_xly):
            outperform = current_xly > sma20_xly
            xly_score = 72 if outperform else 32
            component_scores.append(("XLY/XLP", xly_score, 0.25))
            sub_scores["XLY/XLP"] = round(current_xly, 4)
            drivers.append(
                f"Discretionary/Staples: {'Discretionary leading (consumer risk-on)' if outperform else 'Staples outperforming (defensive)'}"
            )

    # ── Composite ────────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight
    score = clamp(score)

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)
    explanation = _build_explanation(score)

    return SignalResult(
        name="Risk Appetite",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 4 else ("Partial" if available >= 2 else "No Data"),
    )


def _build_explanation(score: float) -> str:
    if score >= 70:
        return "Risk appetite is strong. BTC + semis + discretionary all confirming risk-on."
    elif score >= 55:
        return "Risk appetite is positive but mixed. Some defensive signals persisting."
    elif score >= 40:
        return "Risk appetite is neutral. Cross-asset signals not clearly aligned."
    else:
        return "Risk appetite is declining. Defensives outperforming; gold elevated."
