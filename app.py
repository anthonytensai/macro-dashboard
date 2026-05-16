"""
app.py — Macro Regime Dashboard
Run with: python -m streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

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

# ── Claude API ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

@st.cache_data(ttl=14400, show_spinner=False)
def generate_macro_summary(composite, regime, conviction, action,
                            n_bull, n_neut, n_bear,
                            hard_vetoes, soft_vetoes,
                            signal_scores: dict) -> str:
    """Generate a plain English AI summary of current macro conditions."""
    if not ANTHROPIC_API_KEY:
        return ""
    try:
        scores_str = "\n".join([
            f"- {k.title()}: {v:.0f}/100" for k, v in signal_scores.items()
        ])
        veto_str = ", ".join(hard_vetoes) if hard_vetoes else "None"
        soft_str = ", ".join(soft_vetoes) if soft_vetoes else "None"

        prompt = f"""You are a macro market analyst. Write a 4-5 sentence plain English summary of current US market conditions for a discretionary global growth equity investor.

CURRENT DATA (today is {datetime.now().strftime('%B %Y')}):
- Composite Score: {composite:.0f}/100
- Regime: {regime}
- Conviction: {conviction}
- Signal alignment: {n_bull} Bullish, {n_neut} Neutral, {n_bear} Bearish
- Recommended action: {action}
- Hard vetoes active: {veto_str}
- Soft warnings: {soft_str}
- Individual signal scores:
{scores_str}

Rules:
- Be direct and practical, no fluff
- Mention the regime and what it means
- Note the biggest risk or opportunity right now
- End with one sentence on what the investor should focus on
- No bullet points, just flowing prose
- Max 5 sentences"""

        resp = requests.post(
            CLAUDE_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        return ""
    except Exception:
        return ""

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

# ── STAT BAR ─────────────────────────────────────────────────────────────────
from data.market_data import latest
import pandas as pd

spy   = prices.get("SPY", pd.Series(dtype=float)).dropna()
vix   = prices.get("^VIX", pd.Series(dtype=float)).dropna()
hy    = fred_data.get("hy_spread", pd.Series(dtype=float)).dropna()
ry    = fred_data.get("real_yield_10y", pd.Series(dtype=float)).dropna()
uup   = prices.get("UUP", pd.Series(dtype=float)).dropna()

vix_now  = float(vix.iloc[-1])  if not vix.empty  else float("nan")
hy_now   = float(hy.iloc[-1])   if not hy.empty   else float("nan")
ry_now   = float(ry.iloc[-1])   if not ry.empty   else float("nan")
spy_now  = float(spy.iloc[-1])  if not spy.empty  else float("nan")
spy_200  = float(spy.rolling(200).mean().iloc[-1]) if len(spy) >= 200 else float("nan")
spy_1m   = float((spy.iloc[-1]/spy.iloc[-21]-1)*100) if len(spy) >= 22 else float("nan")
uup_1m   = float((uup.iloc[-1]/uup.iloc[-21]-1)*100) if len(uup) >= 22 else float("nan")

above_200 = spy_now > spy_200 if not np.isnan(spy_200) else None

st.markdown("---")
sb1, sb2, sb3, sb4, sb5, sb6, sb7 = st.columns(7)
with sb1:
    st.metric("Composite", f"{composite:.0f}/100")
with sb2:
    action_short = sizing.action.split()[0]
    st.metric("Action", action_short)
with sb3:
    st.metric("VIX", f"{vix_now:.1f}" if not np.isnan(vix_now) else "—",
              delta=None)
with sb4:
    spy_vs = f"{'↑' if above_200 else '↓'} 200DMA" if above_200 is not None else "—"
    st.metric("SPY", f"${spy_now:,.0f}" if not np.isnan(spy_now) else "—",
              delta=f"{spy_1m:+.1f}% 1M" if not np.isnan(spy_1m) else None)
with sb5:
    st.metric("HY Spread", f"{hy_now:.0f}bps" if not np.isnan(hy_now) else "—")
with sb6:
    st.metric("Real Yield", f"{ry_now:+.2f}%" if not np.isnan(ry_now) else "—")
with sb7:
    st.metric("DXY (UUP)", f"{uup_1m:+.1f}% 1M" if not np.isnan(uup_1m) else "—",
              delta_color="inverse")
st.markdown("---")

# ── AI NARRATIVE SUMMARY ──────────────────────────────────────────────────────
signal_scores = {k: v.score for k, v in signals.items()}
with st.spinner("Generating AI summary..."):
    ai_summary = generate_macro_summary(
        composite=composite,
        regime=regime,
        conviction=conviction,
        action=sizing.action,
        n_bull=n_bull,
        n_neut=n_neut,
        n_bear=n_bear,
        hard_vetoes=hard_vetoes,
        soft_vetoes=soft_vetoes,
        signal_scores=signal_scores,
    )

if ai_summary:
    regime_colors = {
        "Goldilocks Risk-On": "success",
        "AI/Liquidity Melt-Up": "info",
        "Inflation Scare": "warning",
        "Growth Scare": "warning",
        "Crisis Deleveraging": "error",
        "Late-Cycle Narrow Rally": "warning",
        "Neutral/Transition": "info",
    }
    box = regime_colors.get(regime, "info")
    getattr(st, box)(f"**🧠 AI Summary — {regime}**\n\n{ai_summary}")
    st.caption(f"Generated by Claude · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.markdown("---")

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
