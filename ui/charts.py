"""
ui/charts.py — Plotly chart generators for the dashboard.
Dark theme, clean, minimal chart decorations.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional

# ── Dark theme template ──────────────────────────────────────────────────────
DARK_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8", family="SF Mono, Fira Code, monospace", size=11),
        xaxis=dict(gridcolor="#1e293b", zeroline=False, showgrid=True),
        yaxis=dict(gridcolor="#1e293b", zeroline=False, showgrid=True),
        margin=dict(l=40, r=20, t=30, b=30),
    )
)


def _base_fig(height: int = 280) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=height,
        **DARK_TEMPLATE["layout"],
        showlegend=True,
        legend=dict(
            orientation="h",
            y=1.05,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
        ),
    )
    return fig


def chart_spy_dmas(spy: pd.Series) -> go.Figure:
    """SPY price with 50DMA and 200DMA."""
    fig = _base_fig(height=300)
    spy_clean = spy.dropna().tail(252)

    fig.add_trace(go.Scatter(
        x=spy_clean.index, y=spy_clean.values,
        name="SPY", line=dict(color="#f1f5f9", width=1.5),
    ))

    for window, color, name in [(50, "#3b82f6", "50DMA"), (200, "#f59e0b", "200DMA")]:
        dma = spy_clean.rolling(window).mean()
        fig.add_trace(go.Scatter(
            x=dma.index, y=dma.values,
            name=name, line=dict(color=color, width=1, dash="dot"),
        ))

    fig.update_layout(title_text="SPY + Moving Averages", title_font_size=12)
    return fig


def chart_vix(vix: pd.Series, vix3m: Optional[pd.Series] = None) -> go.Figure:
    """VIX level with optional VIX3M overlay."""
    fig = _base_fig(height=260)
    vix_clean = vix.dropna().tail(252)

    fig.add_trace(go.Scatter(
        x=vix_clean.index, y=vix_clean.values,
        name="VIX", line=dict(color="#ef4444", width=1.5),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.05)",
    ))

    if vix3m is not None and not vix3m.empty:
        v3 = vix3m.dropna().tail(252)
        fig.add_trace(go.Scatter(
            x=v3.index, y=v3.values,
            name="VIX3M", line=dict(color="#f97316", width=1, dash="dot"),
        ))

    # Reference lines
    for level, color in [(18, "#22c55e"), (25, "#f59e0b"), (35, "#ef4444")]:
        fig.add_hline(y=level, line_dash="dot", line_color=color, opacity=0.4,
                      annotation_text=str(level), annotation_font_size=10)

    fig.update_layout(title_text="VIX + Term Structure", title_font_size=12)
    return fig


def chart_hy_spread(hy_spread: pd.Series) -> go.Figure:
    """HY credit spread over time."""
    fig = _base_fig(height=260)
    hy = hy_spread.dropna().tail(504)

    fig.add_trace(go.Scatter(
        x=hy.index, y=hy.values,
        name="HY OAS (bps)", line=dict(color="#f59e0b", width=1.5),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.05)",
    ))

    for level, color in [(350, "#22c55e"), (500, "#ef4444")]:
        fig.add_hline(y=level, line_dash="dot", line_color=color, opacity=0.4,
                      annotation_text=f"{level}bps", annotation_font_size=10)

    fig.update_layout(title_text="HY Credit Spread (OAS)", title_font_size=12, yaxis_title="bps")
    return fig


def chart_dxy(uup: pd.Series) -> go.Figure:
    """DXY proxy (UUP) with 50DMA."""
    fig = _base_fig(height=260)
    uup_clean = uup.dropna().tail(252)

    fig.add_trace(go.Scatter(
        x=uup_clean.index, y=uup_clean.values,
        name="DXY (UUP)", line=dict(color="#a855f7", width=1.5),
    ))
    dma50 = uup_clean.rolling(50).mean()
    fig.add_trace(go.Scatter(
        x=dma50.index, y=dma50.values,
        name="50DMA", line=dict(color="#a855f7", width=1, dash="dot"), opacity=0.5,
    ))

    fig.update_layout(title_text="DXY Proxy (UUP)", title_font_size=12)
    return fig


def chart_real_yield(real10y: pd.Series) -> go.Figure:
    """10Y real yield (TIPS)."""
    fig = _base_fig(height=260)
    ry = real10y.dropna().tail(504)

    color_line = "#ef4444" if (not ry.empty and ry.iloc[-1] > 0) else "#22c55e"
    fig.add_trace(go.Scatter(
        x=ry.index, y=ry.values,
        name="10Y Real Yield (%)", line=dict(color=color_line, width=1.5),
        fill="tozeroy", fillcolor=f"rgba({'239,68,68' if color_line == '#ef4444' else '34,197,94'},0.05)",
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="#64748b", opacity=0.6)

    fig.update_layout(title_text="10Y Real Yield (TIPS)", title_font_size=12, yaxis_title="%")
    return fig


def chart_btc_dmas(btc: pd.Series) -> go.Figure:
    """BTC with 50DMA and 200DMA."""
    fig = _base_fig(height=260)
    btc_clean = btc.dropna().tail(365)

    fig.add_trace(go.Scatter(
        x=btc_clean.index, y=btc_clean.values,
        name="BTC", line=dict(color="#f97316", width=1.5),
    ))
    for window, color, name in [(50, "#3b82f6", "50DMA"), (200, "#f59e0b", "200DMA")]:
        dma = btc_clean.rolling(window).mean()
        fig.add_trace(go.Scatter(
            x=dma.index, y=dma.values,
            name=name, line=dict(color=color, width=1, dash="dot"),
        ))

    fig.update_layout(title_text="BTC + Moving Averages", title_font_size=12)
    return fig


def chart_rsp_spy(rsp: pd.Series, spy: pd.Series) -> go.Figure:
    """RSP/SPY ratio (breadth indicator)."""
    fig = _base_fig(height=260)
    if rsp.empty or spy.empty:
        fig.add_annotation(text="RSP/SPY: no data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    df = pd.DataFrame({"rsp": rsp, "spy": spy}).dropna()
    ratio = (df["rsp"] / df["spy"]).tail(252)

    fig.add_trace(go.Scatter(
        x=ratio.index, y=ratio.values,
        name="RSP/SPY", line=dict(color="#22c55e", width=1.5),
    ))
    sma20 = ratio.rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=sma20.index, y=sma20.values,
        name="20DMA", line=dict(color="#22c55e", width=1, dash="dot"), opacity=0.5,
    ))

    fig.update_layout(title_text="RSP/SPY (Breadth)", title_font_size=12)
    return fig


def chart_smh_xlu(smh: pd.Series, xlu: pd.Series) -> go.Figure:
    """SMH/XLU ratio (risk appetite: semis vs utilities)."""
    fig = _base_fig(height=260)
    if smh.empty or xlu.empty:
        fig.add_annotation(text="SMH/XLU: no data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    df = pd.DataFrame({"smh": smh, "xlu": xlu}).dropna()
    ratio = (df["smh"] / df["xlu"]).tail(252)

    color = "#3b82f6"
    fig.add_trace(go.Scatter(
        x=ratio.index, y=ratio.values,
        name="SMH/XLU", line=dict(color=color, width=1.5),
    ))
    sma50 = ratio.rolling(50).mean()
    fig.add_trace(go.Scatter(
        x=sma50.index, y=sma50.values,
        name="50DMA", line=dict(color=color, width=1, dash="dot"), opacity=0.5,
    ))

    fig.update_layout(title_text="SMH/XLU (Semis vs Utilities)", title_font_size=12)
    return fig


def chart_composite_gauge(score: float) -> go.Figure:
    """Gauge chart for composite score."""
    # Color based on score
    if score >= 65:
        color = "#22c55e"
    elif score >= 45:
        color = "#f59e0b"
    else:
        color = "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        number={"font": {"size": 40, "color": color, "family": "SF Mono, monospace"}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#334155",
                "tickvals": [0, 20, 40, 60, 80, 100],
                "tickfont": {"size": 10, "color": "#64748b"},
            },
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#1e293b",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 20],  "color": "#3b0f0f"},
                {"range": [20, 40], "color": "#2d1b00"},
                {"range": [40, 60], "color": "#1a1f2e"},
                {"range": [60, 80], "color": "#0f2a1a"},
                {"range": [80, 100],"color": "#0a1f12"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))

    fig.update_layout(
        height=220,
        paper_bgcolor="#0f172a",
        font=dict(color="#94a3b8", family="SF Mono, monospace"),
        margin=dict(l=20, r=20, t=20, b=10),
    )
    return fig
