"""
app.py — Macro Regime Dashboard
Run with: python -m streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Macro Regime Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from data.market_data import get_all_prices
from data.fred_data import fetch_all_fred
from signals.trend import score_trend
from signals.momentum import score_momentum
from signals.volatility import score_volatility
from signals.credit import score_credit
from signals.liquidity import score_liquidity
from signals.rates import score_rates
from signals.risk_appetite import score_risk_appetite
from signals.breadth import score_breadth
from engine.scoring import compute_composite_score
from engine.conviction import compute_conviction, conviction_note
from engine.veto import evaluate_vetoes
from engine.sizing import compute_sizing
from engine.regime import classify_regime, get_regime_description
from ui.layout import (
    render_header, render_signal_cards, render_alerts_panel,
    render_charts_panel, render_portfolio_action, render_signal_table,
)
from data.cache import clear_cache, cache_info

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Macro Dashboard")
    st.caption("Local-first macro regime overlay")
    if st.button("🔄 Refresh All Data", use_container_width=True):
        clear_cache()
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown("**Signal Weights**")
    st.caption("Trend: 20% · Momentum: 15%\nVolatility: 15% · Credit: 15%\nLiquidity: 10% · Rates: 10%\nRisk Appetite: 10% · Breadth: 5%")
    st.markdown("---")
    show_table = st.checkbox("Show signal table", value=False)

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("📊 Macro Regime Dashboard")

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=14400, show_spinner=False)
def load_market_data():
    return get_all_prices()

@st.cache_data(ttl=14400, show_spinner=False)
def load_fred_data():
    return fetch_all_fred()

with st.spinner("Fetching market data..."):
    prices = load_market_data()

with st.spinner("Fetching FRED macro data..."):
    fred_data = load_fred_data()

# ── Signals ───────────────────────────────────────────────────────────────────
with st.spinner("Computing signals..."):
    signals = {
        "trend":         score_trend(prices),
        "momentum":      score_momentum(prices),
        "volatility":    score_volatility(prices),
        "credit":        score_credit(prices, fred_data),
        "liquidity":     score_liquidity(prices, fred_data),
        "rates":         score_rates(fred_data),
        "risk_appetite": score_risk_appetite(prices),
        "breadth":       score_breadth(prices),
    }
    composite = compute_composite_score(signals)
    conviction, n_bull, n_neut, n_bear = compute_conviction(signals)
    max_gross, hard_vetoes, soft_vetoes = evaluate_vetoes(composite, prices, fred_data, signals)
    sizing = compute_sizing(composite, conviction, max_gross, hard_vetoes, soft_vetoes)
    regime = classify_regime(signals, composite)

# ── Render ────────────────────────────────────────────────────────────────────
render_header(composite, regime, conviction, sizing)

st.caption(f"Signal Agreement: ▲ {n_bull} Bullish · ◆ {n_neut} Neutral · ▼ {n_bear} Bearish")

render_signal_cards(signals)

if show_table:
    st.markdown("### Signal Table")
    render_signal_table(signals)

render_alerts_panel(hard_vetoes, soft_vetoes, signals)
render_charts_panel(prices, fred_data)
render_portfolio_action(sizing, regime, conviction, composite)

with st.expander(f"About this regime: {regime}"):
    st.write(get_regime_description(regime))
