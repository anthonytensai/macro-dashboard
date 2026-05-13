"""
engine/regime.py — Macro regime classifier.

Maps signal profile to one of 7 named regimes.
Uses rule-based logic, not ML.
"""

from typing import Dict
from signals.base import SignalResult


REGIME_DESCRIPTIONS = {
    "Goldilocks Risk-On": "Strong trend + momentum + low vol + broad breadth. Best environment for full risk-on.",
    "AI/Liquidity Melt-Up": "Strong large-cap trend + momentum but narrow breadth. Semis + QQQ leading. Technicals supportive but fragile.",
    "Inflation Scare": "Rising real yields + strong DXY + falling breadth. Rate-sensitive equities under pressure.",
    "Growth Scare": "Widening credit spreads + falling yields + rising VIX. Markets pricing recession risk.",
    "Crisis Deleveraging": "VIX elevated/inverted + HY widening sharply + SPY below 200DMA. Maximum caution.",
    "Late-Cycle Narrow Rally": "High SPY/QQQ but weak RSP/SPY + weak small caps. Participation narrowing. Late-cycle warning.",
    "Neutral/Transition": "Mixed signals across layers. No clear regime dominance. Wait for confirmation.",
}


def classify_regime(signals: Dict[str, SignalResult], composite: float) -> str:
    """
    Rule-based regime classification.
    Scores are compared against thresholds to identify dominant conditions.
    """
    t   = signals.get("trend",        None)
    m   = signals.get("momentum",     None)
    v   = signals.get("volatility",   None)
    c   = signals.get("credit",       None)
    l   = signals.get("liquidity",    None)
    r   = signals.get("rates",        None)
    ra  = signals.get("risk_appetite",None)
    b   = signals.get("breadth",      None)

    def s(sig) -> float:
        return sig.score if sig else 50.0

    trend_score     = s(t)
    mom_score       = s(m)
    vol_score       = s(v)
    credit_score    = s(c)
    liq_score       = s(l)
    rates_score     = s(r)
    risk_a_score    = s(ra)
    breadth_score   = s(b)

    # ── Crisis Deleveraging: worst conditions across board ────────────────────
    if (
        vol_score < 30
        and credit_score < 35
        and trend_score < 35
    ):
        return "Crisis Deleveraging"

    # ── Growth Scare: credit stress + rate relief + vol rising ───────────────
    if (
        credit_score < 40
        and rates_score >= 55        # falling yields = rate relief
        and vol_score < 45
        and trend_score < 55
    ):
        return "Growth Scare"

    # ── Inflation Scare: high rates + strong DXY + weak breadth ─────────────
    if (
        rates_score < 40
        and liq_score < 40           # rising DXY
        and breadth_score < 45
    ):
        return "Inflation Scare"

    # ── Goldilocks: everything aligned ───────────────────────────────────────
    if (
        trend_score >= 65
        and mom_score >= 65
        and vol_score >= 65
        and breadth_score >= 60
        and credit_score >= 60
    ):
        return "Goldilocks Risk-On"

    # ── AI/Liquidity Melt-Up: large-cap momentum but narrow breadth ──────────
    if (
        trend_score >= 65
        and mom_score >= 65
        and risk_a_score >= 60        # semis leading
        and breadth_score < 50        # but breadth weak
    ):
        return "AI/Liquidity Melt-Up"

    # ── Late-Cycle Narrow Rally: SPY/QQQ fine but breadth poor ──────────────
    if (
        trend_score >= 60
        and breadth_score < 45
        and composite >= 50
    ):
        return "Late-Cycle Narrow Rally"

    # ── Neutral/Transition: everything else ───────────────────────────────────
    return "Neutral/Transition"


def get_regime_description(regime: str) -> str:
    return REGIME_DESCRIPTIONS.get(regime, "No description available.")


REGIME_COLORS = {
    "Goldilocks Risk-On":     "#22c55e",   # green
    "AI/Liquidity Melt-Up":  "#3b82f6",   # blue
    "Inflation Scare":        "#f59e0b",   # amber
    "Growth Scare":           "#f97316",   # orange
    "Crisis Deleveraging":    "#ef4444",   # red
    "Late-Cycle Narrow Rally":"#a855f7",   # purple
    "Neutral/Transition":     "#6b7280",   # gray
}
