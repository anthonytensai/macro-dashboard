"""
engine/sizing.py — Portfolio sizing recommendation.

Maps composite score + conviction + vetoes → actionable sizing output.
Low conviction caps sizing at Neutral band regardless of composite score.
"""

from dataclasses import dataclass
from typing import List, Optional
from config import SIZING_BANDS


@dataclass
class SizingOutput:
    posture: str           # "Full Risk-On", "Lean Risk-On", "Neutral", "Defensive", "Risk-Off"
    action: str            # "Add", "Hold", "Trim", "Deleverage"
    gross_low: float       # lower bound of target gross exposure
    gross_high: float      # upper bound of target gross exposure
    max_gross: float       # hard veto ceiling
    final_gross_high: float  # min(gross_high, max_gross)
    rationale: str
    what_would_change: List[str]
    conviction_note: str


def compute_sizing(
    composite: float,
    conviction: str,
    max_gross: float,
    hard_vetoes: List[str],
    soft_vetoes: List[str],
) -> SizingOutput:
    """
    Core sizing logic:
    1. Find base band from composite score.
    2. If conviction is Low, cap at Neutral band.
    3. Apply hard veto ceiling.
    4. Build rationale.
    """
    # Step 1: Find base band
    band = _get_band(composite)

    # Step 2: Low conviction → cap at Neutral
    if conviction == "Low":
        neutral_band = _get_band(50)  # Neutral band
        # A lower index means more risk-on (band[0] = Full Risk-On)
        if _band_index(band) < _band_index(neutral_band):
            band = neutral_band
            conviction_note = "Low conviction overrides composite score — capped at Neutral."
        elif composite < 40:
            # Low conviction + bearish composite: keep bearish band
            conviction_note = "Low conviction confirmed by bearish composite."
        else:
            conviction_note = "Low conviction — sizing capped at Neutral."
            band = neutral_band
    elif conviction in ("High", "Medium-High"):
        conviction_note = f"{conviction} conviction supports composite signal."
    else:
        conviction_note = f"{conviction} conviction — moderate confidence in signal."

    # Step 3: Apply veto ceiling
    final_gross_high = min(band["gross_high"], max_gross)
    final_gross_low = min(band["gross_low"], max_gross - 0.05)

    # Build rationale
    rationale = _build_rationale(composite, conviction, band, hard_vetoes, soft_vetoes)
    what_changes = _build_what_changes(composite, band, hard_vetoes)

    return SizingOutput(
        posture=band["posture"],
        action=band["action"],
        gross_low=final_gross_low,
        gross_high=final_gross_high,
        max_gross=max_gross,
        final_gross_high=final_gross_high,
        rationale=rationale,
        what_would_change=what_changes,
        conviction_note=conviction_note,
    )


def _get_band(score: float) -> dict:
    """Return the sizing band for the given composite score."""
    for band in SIZING_BANDS:
        if band["min_score"] <= score <= band["max_score"]:
            return band
    return SIZING_BANDS[-1]  # default to Risk-Off if out of range


def _band_index(band: dict) -> int:
    """Return index of band in SIZING_BANDS list (higher = more risk-on)."""
    for i, b in enumerate(SIZING_BANDS):
        if b["posture"] == band["posture"]:
            return i
    return len(SIZING_BANDS) - 1


def _build_rationale(
    composite: float,
    conviction: str,
    band: dict,
    hard_vetoes: List[str],
    soft_vetoes: List[str],
) -> str:
    lines = []
    lines.append(
        f"Composite score of {composite:.0f}/100 places the environment in the "
        f"'{band['posture']}' regime with {conviction.lower()} conviction. "
        f"{band['description']}"
    )
    if hard_vetoes:
        lines.append(
            f"Active hard vetoes ({len(hard_vetoes)}): {'; '.join(hard_vetoes)}. "
            f"These override the base sizing band."
        )
    if soft_vetoes:
        lines.append(
            f"Soft warnings: {'; '.join(soft_vetoes)}. Monitor closely."
        )
    if not hard_vetoes and not soft_vetoes:
        lines.append("No veto conditions active. Sizing based purely on signal composite.")
    return " ".join(lines)


def _build_what_changes(
    composite: float,
    band: dict,
    hard_vetoes: List[str],
) -> List[str]:
    """Generate 3–5 conditions that would change the current posture."""
    changes = []

    if composite < 60:
        changes.append("Composite score rising above 65 sustained over 5+ days")
        changes.append("Credit spreads (HY) tightening back toward 300bps")
        changes.append("VIX closing below 18 and holding")
    else:
        changes.append("Composite score dropping below 50 for 3+ consecutive days")
        changes.append("VIX spiking above 25 on volume")
        changes.append("HY spreads widening sharply (+75bps in 20 days)")

    if "SPY below 200DMA" in " ".join(hard_vetoes):
        changes.append("SPY reclaiming and holding above the 200DMA")
    else:
        changes.append("SPY closing below 200DMA would trigger hard veto")

    changes.append("Real yields spiking +30bps in 20 days would cap gross to 1.25x")
    changes.append("Breadth divergence resolving (RSP/SPY and IWM/SPY confirming upside)")

    return changes[:5]
