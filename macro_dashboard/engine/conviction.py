"""
engine/conviction.py — Conviction meter: how aligned are the 8 signals?

We count directional agreement, not just average score.
A high score with low conviction → capped at Neutral sizing.
"""

from typing import Dict, Tuple
from signals.base import SignalResult
from config import BULLISH_THRESHOLD, BEARISH_THRESHOLD, CONVICTION_LEVELS, CONVICTION_DEFAULT


def compute_conviction(signals: Dict[str, SignalResult]) -> Tuple[str, int, int, int]:
    """
    Returns:
    - conviction label: "High", "Medium-High", "Medium", "Low"
    - n_bullish: count of Bullish signals
    - n_neutral: count of Neutral signals
    - n_bearish: count of Bearish signals
    """
    n_bullish = 0
    n_neutral = 0
    n_bearish = 0

    for signal in signals.values():
        if signal.data_quality == "No Data":
            continue
        if signal.score >= BULLISH_THRESHOLD:
            n_bullish += 1
        elif signal.score < BEARISH_THRESHOLD:
            n_bearish += 1
        else:
            n_neutral += 1

    # Agreement = majority direction count
    majority = max(n_bullish, n_bearish)
    total_valid = n_bullish + n_neutral + n_bearish

    if total_valid == 0:
        return CONVICTION_DEFAULT, 0, 0, 0

    conviction = CONVICTION_LEVELS.get(majority, CONVICTION_DEFAULT)

    # Special case: 4/4 split → force Low
    if n_bullish == n_bearish and total_valid >= 6:
        conviction = "Low"

    return conviction, n_bullish, n_neutral, n_bearish


def conviction_note(conviction: str, composite: float) -> str:
    """Return a short note about conviction vs composite consistency."""
    if conviction == "Low" and composite >= 60:
        return "⚠ High composite score but low conviction — signals not aligned. Cap at Neutral."
    elif conviction == "Low" and composite < 40:
        return "⚠ Low conviction + bearish composite — risk-off leaning confirmed by disagreement."
    elif conviction in ("High", "Medium-High") and composite >= 60:
        return "✓ High conviction + bullish composite — strong signal quality."
    elif conviction in ("High", "Medium-High") and composite < 40:
        return "✓ High conviction + bearish composite — clear risk-off signal."
    else:
        return "Signal environment is mixed. Exercise discretion."
