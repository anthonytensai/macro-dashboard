"""
ui/layout.py — Dashboard layout using native Streamlit components.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict

from signals.base import SignalResult
from engine.sizing import SizingOutput
from engine.regime import REGIME_COLORS, get_regime_description
from ui.cards import render_signal_card, render_veto_alert
from ui import charts


def render_header(composite: float, regime: str, conviction: str, sizing: SizingOutput) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Composite Score", f"{composite:.0f} / 100")
    with col2:
        st.metric("Regime", regime)
    with col3:
        st.metric("Conviction", conviction)
    with col4:
        st.metric("Target Gross", f"{sizing.gross_low:.2f}x – {sizing.final_gross_high:.2f}x",
                  delta=f"max {sizing.max_gross:.2f}x")
    with col5:
        st.metric("Action", sizing.action)
    st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Posture: {sizing.posture}")


def render_signal_cards(signals: Dict[str, SignalResult]) -> None:
    st.markdown("### Signal Layers")
    signal_order = ["trend", "momentum", "volatility", "credit", "liquidity", "rates", "risk_appetite", "breadth"]
    cols = st.columns(4)
    for i, key in enumerate(signal_order):
        signal = signals.get(key)
        if signal:
            with cols[i % 4]:
                render_signal_card(signal)


def render_alerts_panel(hard_vetoes: list, soft_vetoes: list, signals: Dict[str, SignalResult]) -> None:
    st.markdown("### Alerts & Divergences")
    if not hard_vetoes and not soft_vetoes:
        st.success("No active veto conditions. Signal environment is clean.")
        return
    for v in hard_vetoes:
        render_veto_alert(v, is_hard=True)
    for v in soft_vetoes:
        render_veto_alert(v, is_hard=False)
    bad_quality = [s.name for s in signals.values() if s.data_quality == "No Data"]
    partial = [s.name for s in signals.values() if s.data_quality == "Partial"]
    if bad_quality:
        st.warning(f"No data for: {', '.join(bad_quality)}")
    if partial:
        st.info(f"Partial data: {', '.join(partial)}")


def render_charts_panel(prices: dict, fred_data: dict) -> None:
    st.markdown("### Charts")
    col1, col2 = st.columns(2)
    spy   = prices.get("SPY", pd.Series(dtype=float))
    vix   = prices.get("^VIX", pd.Series(dtype=float))
    vix3m = prices.get("^VIX3M", pd.Series(dtype=float))
    rsp   = prices.get("RSP", pd.Series(dtype=float))
    uup   = prices.get("UUP", pd.Series(dtype=float))
    btc   = prices.get("BTC-USD", pd.Series(dtype=float))
    smh   = prices.get("SMH", pd.Series(dtype=float))
    xlu   = prices.get("XLU", pd.Series(dtype=float))
    hy_spread = fred_data.get("hy_spread", pd.Series(dtype=float))
    real10y   = fred_data.get("real_yield_10y", pd.Series(dtype=float))
    with col1:
        st.plotly_chart(charts.chart_spy_dmas(spy), use_container_width=True)
        st.plotly_chart(charts.chart_hy_spread(hy_spread), use_container_width=True)
        st.plotly_chart(charts.chart_real_yield(real10y), use_container_width=True)
        st.plotly_chart(charts.chart_rsp_spy(rsp, spy), use_container_width=True)
    with col2:
        st.plotly_chart(charts.chart_vix(vix, vix3m if not vix3m.empty else None), use_container_width=True)
        st.plotly_chart(charts.chart_dxy(uup), use_container_width=True)
        st.plotly_chart(charts.chart_btc_dmas(btc), use_container_width=True)
        st.plotly_chart(charts.chart_smh_xlu(smh, xlu), use_container_width=True)


def render_portfolio_action(sizing: SizingOutput, regime: str, conviction: str, composite: float) -> None:
    st.markdown("### Portfolio Action")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Posture", sizing.posture)
    with col2:
        st.metric("Target Gross", f"{sizing.gross_low:.2f}x – {sizing.final_gross_high:.2f}x",
                  delta=f"max {sizing.max_gross:.2f}x")
    with col3:
        st.metric("Action", sizing.action)
    st.markdown("**Rationale**")
    st.info(sizing.rationale)
    st.caption(sizing.conviction_note)
    st.markdown("**What Would Change My View**")
    for item in sizing.what_would_change:
        st.markdown(f"- {item}")


def render_signal_table(signals: Dict[str, SignalResult]) -> None:
    from engine.scoring import score_summary_table
    rows = score_summary_table(signals)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
