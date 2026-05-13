"""
signals/base.py — Shared types and helper for all signal modules.
Each signal returns a SignalResult dataclass with a consistent interface.
"""

from dataclasses import dataclass, field
from typing import List
import numpy as np


@dataclass
class SignalResult:
    name: str
    score: float                    # 0–100
    direction: str                  # "Bullish" | "Neutral" | "Bearish"
    confidence: str                 # "Low" | "Medium" | "High"
    explanation: str                # 1-2 line human-readable summary
    drivers: List[str]              # 3–5 key indicator descriptions
    sub_scores: dict = field(default_factory=dict)  # optional breakdown
    data_quality: str = "OK"        # "OK" | "Partial" | "No Data"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": round(self.score, 1),
            "direction": self.direction,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "drivers": self.drivers,
            "data_quality": self.data_quality,
        }


def direction_from_score(score: float) -> str:
    """Map numeric score to directional label."""
    if score >= 60:
        return "Bullish"
    elif score >= 40:
        return "Neutral"
    else:
        return "Bearish"


def confidence_from_data_count(available: int, total: int) -> str:
    """Estimate confidence based on how many indicators are available."""
    ratio = available / max(total, 1)
    if ratio >= 0.8:
        return "High"
    elif ratio >= 0.5:
        return "Medium"
    else:
        return "Low"


def safe_div(a: float, b: float, fallback: float = float("nan")) -> float:
    """Division with zero-check."""
    try:
        return a / b if b != 0 else fallback
    except Exception:
        return fallback


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp value between lo and hi."""
    if np.isnan(x):
        return 50.0  # default to neutral if NaN
    return max(lo, min(hi, x))
