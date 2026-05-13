"""
engine/veto.py — Veto engine: hard and soft override rules.

Hard vetoes cap maximum gross leverage regardless of composite score.
Soft vetoes flag warnings and reduce sizing by one band.
"""

from typing import Dict, List, Tuple
from signals.base import SignalResult
from config import HARD_VETO_RULES, SOFT_VETO_RULES


def evaluate_vetoes(
    composite: float,
    prices: dict,
    fred_data: dict,
    signals: Dict[str, SignalResult],
) -> Tuple[float, List[str], List[str]]:
    """
    Evaluate all hard and soft veto conditions.

    Returns:
    - max_gross: float — the strictest (lowest) veto cap across active hard vetoes
    - hard_vetoes: list of active hard veto descriptions
    - soft_vetoes: list of active soft veto warnings
    """
    hard_vetoes: List[str] = []
    soft_vetoes: List[str] = []
    max_gross = 1.40  # default ceiling

    # ── Evaluate hard veto conditions ────────────────────────────────────────────
    conditions = _check_conditions(composite, prices, fred_data, signals)

    for rule in HARD_VETO_RULES:
        if conditions.get(rule["key"], False):
            hard_vetoes.append(rule["description"])
            max_gross = min(max_gross, rule["max_gross"])

    # ── Evaluate soft veto conditions ─────────────────────────────────────────────
    soft_conditions = _check_soft_conditions(prices, fred_data, signals)
    for rule in SOFT_VETO_RULES:
        if soft_conditions.get(rule["key"], False):
            soft_vetoes.append(rule["description"])

    return round(max_gross, 2), hard_vetoes, soft_vetoes


def _check_conditions(
    composite: float,
    prices: dict,
    fred_data: dict,
    signals: Dict[str, SignalResult],
) -> dict:
    """Evaluate each hard veto condition. Return dict of condition_key → bool."""
    from signals.trend import get_spy_below_200dma
    from signals.volatility import get_vix_backwardation
    from signals.credit import get_hy_widening_veto
    from signals.rates import get_real_yield_dxy_veto

    return {
        "spy_below_200dma":       get_spy_below_200dma(prices),
        "vix_backwardation":      get_vix_backwardation(prices),
        "hy_widening_sharply":    get_hy_widening_veto(fred_data),
        "real_yield_dxy_rising":  get_real_yield_dxy_veto(fred_data, prices),
        "composite_below_40":     composite < 40,
        "composite_below_20":     composite < 20,
    }


def _check_soft_conditions(prices: dict, fred_data: dict, signals: Dict[str, SignalResult]) -> dict:
    """Evaluate soft veto conditions."""
    from signals.breadth import get_breadth_divergence
    import pandas as pd
    import numpy as np
    from data.market_data import latest, ratio_series

    btc = prices.get("BTC-USD", pd.Series(dtype=float)).dropna()
    gld = prices.get("GLD", pd.Series(dtype=float)).dropna()
    spy = prices.get("SPY", pd.Series(dtype=float)).dropna()
    qqq = prices.get("QQQ", pd.Series(dtype=float)).dropna()
    kre = prices.get("KRE", pd.Series(dtype=float)).dropna()

    # BTC below 200DMA while equities rising
    btc_below_200 = False
    if len(btc) >= 200 and len(spy) >= 21:
        from data.market_data import compute_dma, compute_roc
        btc_200 = compute_dma(btc, 200).iloc[-1]
        btc_below_200 = btc.iloc[-1] < btc_200
        spy_1m = compute_roc(spy, 21)
        btc_below_200 = btc_below_200 and (not np.isnan(spy_1m) and spy_1m > 0)

    # Gold/SPY rising while QQQ rising
    gold_spy_rising = False
    gld_spy = ratio_series(gld, spy)
    if len(gld_spy) >= 21 and len(qqq) >= 21:
        from data.market_data import compute_roc
        gld_spy_roc = compute_roc(gld_spy, 21) if len(gld_spy) >= 22 else float("nan")
        qqq_roc = compute_roc(qqq, 21)
        if not np.isnan(gld_spy_roc) and not np.isnan(qqq_roc):
            gold_spy_rising = gld_spy_roc > 1.0 and qqq_roc > 0

    # KRE/SPY breakdown
    kre_breakdown = False
    kre_spy = ratio_series(kre, spy)
    if len(kre_spy) >= 20:
        current = kre_spy.iloc[-1]
        sma20 = kre_spy.rolling(20).mean().iloc[-1]
        if not np.isnan(sma20):
            kre_breakdown = current < sma20 * 0.97  # 3% below 20DMA

    return {
        "breadth_weakening_spy_rising": get_breadth_divergence(prices),
        "btc_below_200dma_equities_rising": btc_below_200,
        "gold_spy_rising_qqq_rising": gold_spy_rising,
        "kre_spy_breakdown": kre_breakdown,
    }
