"""
ui/cards.py — Render individual signal cards using native Streamlit components.
"""

import streamlit as st
from signals.base import SignalResult

DIRECTION_ICONS = {
    "Bullish": "▲",
    "Neutral": "◆",
    "Bearish": "▼",
}


def render_signal_card(signal: SignalResult) -> None:
    """Render a signal card using native Streamlit components."""
    icon = DIRECTION_ICONS.get(signal.direction, "◆")

    with st.container():
        st.markdown(f"**{signal.name}** — {icon} {signal.direction}")
        st.progress(int(signal.score) / 100)
        st.caption(f"Score: {signal.score:.0f} | Confidence: {signal.confidence}")
        st.caption(signal.explanation)
        for d in signal.drivers[:3]:
            st.caption(f"· {d}")
        if signal.data_quality != "OK":
            st.warning(f"Data: {signal.data_quality}")
        st.divider()


def render_metric_card(label: str, value: str, delta: str = "", color: str = "#f1f5f9") -> None:
    st.metric(label=label, value=value, delta=delta if delta else None)


def render_veto_alert(text: str, is_hard: bool = True) -> None:
    if is_hard:
        st.error(f"🔴 HARD VETO: {text}")
    else:
        st.warning(f"🟡 SOFT WARNING: {text}")
