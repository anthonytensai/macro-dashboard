"""
signals/liquidity.py — Liquidity signal layer.

DXY direction and Fed balance sheet are the primary global liquidity proxies.
Falling DXY + expanding Fed = most bullish liquidity environment.
"""

import numpy as np
import pandas as pd
from signals.base import SignalResult, direction_from_score, confidence_from_data_count, clamp
from data.market_data import compute_roc, latest
from config import DXY_STRONG_20D


def score_liquidity(prices: dict, fred_data: dict) -> SignalResult:
    """
    Inputs:
    - DXY proxy: UUP ETF
    - Fed balance sheet: WALCL (FRED)
    - Reverse repo: RRPONTSYD (FRED)
    """
    drivers = []
    sub_scores = {}
    available = 0
    total = 4
    component_scores = []

    uup = prices.get("UUP", pd.Series(dtype=float)).dropna()
    fed_bs = fred_data.get("fed_balance", pd.Series(dtype=float)).dropna()
    rrp = fred_data.get("rrp", pd.Series(dtype=float)).dropna()

    # ── DXY / UUP Proxy ─────────────────────────────────────────────────────────
    uup_now = latest(uup)
    uup_1m = compute_roc(uup, 21) if len(uup) >= 22 else float("nan")
    uup_20d = compute_roc(uup, 20) if len(uup) >= 21 else float("nan")

    if not np.isnan(uup_1m):
        available += 1
        # Rising dollar = tighter liquidity = bearish for risk assets
        dxy_score = clamp(60 - uup_1m * 6)
        component_scores.append(("DXY", dxy_score, 0.45))
        sub_scores["DXY (UUP) 1M ROC"] = round(uup_1m, 2)
        direction_str = "rising (liquidity tightening)" if uup_1m > 0 else "falling (supportive)"
        drivers.append(f"DXY proxy (UUP) 1M: {uup_1m:+.1f}% — {direction_str}")

    # ── Fed Balance Sheet ────────────────────────────────────────────────────────
    fed_now = latest(fed_bs)
    if not np.isnan(fed_now) and len(fed_bs) >= 5:
        available += 1
        fed_5w_ago = fed_bs.iloc[-5]  # ~5 weeks of weekly data
        fed_change_pct = (fed_now - fed_5w_ago) / fed_5w_ago * 100 if fed_5w_ago else 0
        # Expanding balance sheet = bullish
        fed_score = clamp(60 + fed_change_pct * 10)
        component_scores.append(("Fed BS", fed_score, 0.30))
        sub_scores["Fed Balance Sheet ($T)"] = round(fed_now / 1e6, 2)
        direction_str = "expanding (bullish)" if fed_change_pct > 0 else "contracting (QT headwind)"
        drivers.append(f"Fed balance sheet: ${fed_now/1e6:.2f}T ({direction_str})")
    else:
        drivers.append("Fed balance sheet: no data")

    # ── Reverse Repo (RRP) ────────────────────────────────────────────────────────
    rrp_now = latest(rrp)
    if not np.isnan(rrp_now) and len(rrp) >= 21:
        available += 1
        rrp_prev = rrp.iloc[-21] if len(rrp) >= 21 else rrp.iloc[0]
        rrp_change = rrp_now - float(rrp_prev)
        # Falling RRP can be neutral to supportive if reserves are stable
        # Large RRP decline can signal reserves flowing into markets
        rrp_score = 60 if rrp_change < 0 else 50
        component_scores.append(("RRP", rrp_score, 0.25))
        sub_scores["Reverse Repo ($B)"] = round(rrp_now, 1)
        drivers.append(
            f"Reverse repo: ${rrp_now:.0f}B "
            f"({'falling — reserves potentially freeing up' if rrp_change < 0 else 'rising — money staying at Fed'})"
        )
    else:
        drivers.append("Reverse repo: no data")

    # ── Composite ────────────────────────────────────────────────────────────────
    if not component_scores:
        score = 50.0
    else:
        total_weight = sum(w for _, _, w in component_scores)
        score = sum(s * w for _, s, w in component_scores) / total_weight
    score = clamp(score)

    direction = direction_from_score(score)
    confidence = confidence_from_data_count(available, total)
    explanation = _build_explanation(score, uup_1m)

    return SignalResult(
        name="Liquidity",
        score=score,
        direction=direction,
        confidence=confidence,
        explanation=explanation,
        drivers=drivers[:5],
        sub_scores=sub_scores,
        data_quality="OK" if available >= 2 else ("Partial" if available >= 1 else "No Data"),
    )


def _build_explanation(score: float, dxy_1m: float) -> str:
    if np.isnan(dxy_1m):
        return "Liquidity signal running on limited data."
    if score >= 70:
        return "Liquidity conditions are supportive. Dollar weakening; Fed balance sheet holding."
    elif score >= 55:
        return "Liquidity is adequate but not expansionary. Dollar relatively flat."
    elif score >= 40:
        return "Liquidity tightening at the margin. Rising dollar pressuring risk assets."
    else:
        return "Liquidity conditions are restrictive. Strong dollar + balance sheet pressure."


def get_dxy_rising_sharply(prices: dict) -> bool:
    """Returns True if DXY proxy (UUP) has risen sharply over 20 days."""
    uup = prices.get("UUP", pd.Series(dtype=float)).dropna()
    roc_20d = compute_roc(uup, 20) if len(uup) >= 21 else float("nan")
    return not np.isnan(roc_20d) and roc_20d > DXY_STRONG_20D
