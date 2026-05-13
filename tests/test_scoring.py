"""
tests/test_scoring.py — Unit tests for scoring and sizing logic.
Run with: python -m pytest tests/
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np
import pandas as pd

from signals.base import direction_from_score, confidence_from_data_count, clamp, SignalResult
from engine.scoring import compute_composite_score
from engine.conviction import compute_conviction
from engine.sizing import compute_sizing, _get_band
from config import SIGNAL_WEIGHTS


# ── Helper: build a dummy SignalResult ────────────────────────────────────────
def make_signal(name: str, score: float, data_quality: str = "OK") -> SignalResult:
    return SignalResult(
        name=name,
        score=score,
        direction=direction_from_score(score),
        confidence="High",
        explanation="Test signal",
        drivers=["driver 1", "driver 2"],
        data_quality=data_quality,
    )


# ── direction_from_score ──────────────────────────────────────────────────────
class TestDirectionFromScore:
    def test_bullish(self):
        assert direction_from_score(70) == "Bullish"
        assert direction_from_score(60) == "Bullish"
        assert direction_from_score(100) == "Bullish"

    def test_neutral(self):
        assert direction_from_score(50) == "Neutral"
        assert direction_from_score(40) == "Neutral"
        assert direction_from_score(59) == "Neutral"

    def test_bearish(self):
        assert direction_from_score(39) == "Bearish"
        assert direction_from_score(0) == "Bearish"
        assert direction_from_score(20) == "Bearish"


# ── clamp ─────────────────────────────────────────────────────────────────────
class TestClamp:
    def test_clamp_normal(self):
        assert clamp(50) == 50
        assert clamp(0) == 0
        assert clamp(100) == 100

    def test_clamp_overflow(self):
        assert clamp(150) == 100
        assert clamp(-10) == 0

    def test_clamp_nan(self):
        # NaN should return neutral 50
        assert clamp(float("nan")) == 50.0


# ── compute_composite_score ───────────────────────────────────────────────────
class TestCompositeScore:
    def test_all_bullish(self):
        signals = {k: make_signal(k, 80) for k in SIGNAL_WEIGHTS}
        score = compute_composite_score(signals)
        assert 79 <= score <= 81

    def test_all_bearish(self):
        signals = {k: make_signal(k, 20) for k in SIGNAL_WEIGHTS}
        score = compute_composite_score(signals)
        assert 19 <= score <= 21

    def test_neutral(self):
        signals = {k: make_signal(k, 50) for k in SIGNAL_WEIGHTS}
        score = compute_composite_score(signals)
        assert 49 <= score <= 51

    def test_missing_signals_excluded(self):
        # Signals with no data should be excluded from weight average
        signals = {k: make_signal(k, 80) for k in SIGNAL_WEIGHTS}
        signals["trend"] = make_signal("trend", 0, data_quality="No Data")
        score = compute_composite_score(signals)
        # Should be >= 80 since zero-score trend is excluded (remaining signals all score 80)
        assert score >= 80

    def test_weights_sum_to_one(self):
        total = sum(SIGNAL_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_empty_signals_returns_50(self):
        score = compute_composite_score({})
        assert score == 50.0


# ── compute_conviction ────────────────────────────────────────────────────────
class TestConviction:
    def test_all_bullish_high_conviction(self):
        signals = {k: make_signal(k, 75) for k in SIGNAL_WEIGHTS}
        conviction, n_bull, n_neut, n_bear = compute_conviction(signals)
        assert conviction == "High"
        assert n_bull == 8
        assert n_bear == 0

    def test_all_bearish_high_conviction(self):
        signals = {k: make_signal(k, 25) for k in SIGNAL_WEIGHTS}
        conviction, n_bull, n_neut, n_bear = compute_conviction(signals)
        assert conviction == "High"
        assert n_bear == 8

    def test_split_low_conviction(self):
        keys = list(SIGNAL_WEIGHTS.keys())
        signals = {}
        for i, k in enumerate(keys):
            signals[k] = make_signal(k, 75 if i < 4 else 25)
        conviction, n_bull, n_neut, n_bear = compute_conviction(signals)
        assert conviction == "Low"
        assert n_bull == 4
        assert n_bear == 4


# ── sizing bands ─────────────────────────────────────────────────────────────
class TestSizingBands:
    @pytest.mark.parametrize("score,expected_posture", [
        (90,  "Full Risk-On"),
        (70,  "Lean Risk-On"),
        (50,  "Neutral"),
        (30,  "Defensive"),
        (10,  "Risk-Off"),
    ])
    def test_band_lookup(self, score, expected_posture):
        band = _get_band(score)
        assert band["posture"] == expected_posture

    def test_gross_bounds_logical(self):
        for score in [10, 30, 50, 70, 90]:
            band = _get_band(score)
            assert band["gross_low"] < band["gross_high"]
            assert 0.5 < band["gross_low"] < 2.0
            assert 0.5 < band["gross_high"] < 2.0


# ── compute_sizing ────────────────────────────────────────────────────────────
class TestComputeSizing:
    def test_full_risk_on_no_vetoes(self):
        result = compute_sizing(85, "High", 1.40, [], [])
        assert result.action == "Add"
        assert result.final_gross_high <= 1.40
        assert result.posture == "Full Risk-On"

    def test_low_conviction_caps_at_neutral(self):
        # High composite but low conviction → should cap at Neutral
        result = compute_sizing(82, "Low", 1.40, [], [])
        assert result.posture == "Neutral"
        assert result.action == "Hold"

    def test_hard_veto_caps_gross(self):
        result = compute_sizing(85, "High", 1.15, ["SPY below 200DMA"], [])
        assert result.final_gross_high <= 1.15
        assert result.max_gross == 1.15

    def test_risk_off_posture(self):
        # Score of 10 + hard veto = Risk-Off. Low conviction doesn't upgrade bearish bands.
        result = compute_sizing(10, "High", 1.10, ["Composite score below 20"], [])
        assert result.posture == "Risk-Off"
        assert result.action == "Deleverage"
        assert result.final_gross_high <= 1.10

    def test_rationale_not_empty(self):
        result = compute_sizing(55, "Medium", 1.35, [], [])
        assert len(result.rationale) > 20

    def test_what_would_change_has_items(self):
        result = compute_sizing(55, "Medium", 1.35, [], [])
        assert len(result.what_would_change) >= 3


# ── confidence_from_data_count ────────────────────────────────────────────────
class TestConfidence:
    def test_high_confidence(self):
        assert confidence_from_data_count(8, 8) == "High"
        assert confidence_from_data_count(9, 10) == "High"

    def test_medium_confidence(self):
        assert confidence_from_data_count(5, 8) == "Medium"

    def test_low_confidence(self):
        assert confidence_from_data_count(2, 8) == "Low"
        assert confidence_from_data_count(0, 8) == "Low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
