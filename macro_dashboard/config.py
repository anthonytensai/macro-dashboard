"""
config.py — Central configuration for the Macro Regime Dashboard.
All scoring thresholds, weights, and sizing bands are defined here.
"""

# ─── API Keys ────────────────────────────────────────────────────────────────
# Set in .env file or environment variables.
FRED_API_KEY = ""  # Optional: set via .env; falls back to pandas_datareader

# ─── Data Refresh ────────────────────────────────────────────────────────────
CACHE_TTL_HOURS = 4          # How long to use cached data before re-fetching
LOOKBACK_DAYS   = 504        # ~2 years of daily data for moving averages

# ─── Signal Weights (must sum to 1.0) ────────────────────────────────────────
SIGNAL_WEIGHTS = {
    "trend":        0.20,
    "momentum":     0.15,
    "volatility":   0.15,
    "credit":       0.15,
    "liquidity":    0.10,
    "rates":        0.10,
    "risk_appetite":0.10,
    "breadth":      0.05,
}

# ─── Score Thresholds ────────────────────────────────────────────────────────
BULLISH_THRESHOLD = 60   # score >= this → Bullish
BEARISH_THRESHOLD = 40   # score < this → Bearish

# ─── Conviction Thresholds ───────────────────────────────────────────────────
CONVICTION_LEVELS = {
    8: "High",
    7: "High",
    6: "Medium-High",
    5: "Medium",
    4: "Low",
}
CONVICTION_DEFAULT = "Low"

# ─── Hard Veto Rules ─────────────────────────────────────────────────────────
# Each rule: {description, condition_key, max_gross}
HARD_VETO_RULES = [
    {
        "key": "spy_below_200dma",
        "description": "SPY below 200DMA",
        "max_gross": 1.15,
    },
    {
        "key": "vix_backwardation",
        "description": "VIX backwardation (front > back)",
        "max_gross": 1.20,
    },
    {
        "key": "hy_widening_sharply",
        "description": "HY spreads widening sharply (20-day)",
        "max_gross": 1.20,
    },
    {
        "key": "real_yield_dxy_rising",
        "description": "Real yields + DXY both rising sharply",
        "max_gross": 1.25,
    },
    {
        "key": "composite_below_40",
        "description": "Composite score below 40",
        "max_gross": 1.20,
    },
    {
        "key": "composite_below_20",
        "description": "Composite score below 20",
        "max_gross": 1.10,
    },
]

# ─── Soft Veto / Warning Rules ───────────────────────────────────────────────
SOFT_VETO_RULES = [
    {
        "key": "breadth_weakening_spy_rising",
        "description": "Breadth weakening while SPY rising — reduce one band",
    },
    {
        "key": "btc_below_200dma_equities_rising",
        "description": "BTC below 200DMA while equities rising — caution flag",
    },
    {
        "key": "gold_spy_rising_qqq_rising",
        "description": "Gold/SPY rising alongside QQQ — hidden defensive rotation",
    },
    {
        "key": "kre_spy_breakdown",
        "description": "KRE/SPY breaking down — credit/liquidity stress",
    },
]

# ─── Sizing Bands ─────────────────────────────────────────────────────────────
SIZING_BANDS = [
    {
        "min_score": 80,
        "max_score": 100,
        "posture":   "Full Risk-On",
        "action":    "Add",
        "gross_low": 1.35,
        "gross_high":1.40,
        "description": "Add high-beta. Full conviction.",
    },
    {
        "min_score": 60,
        "max_score": 79,
        "posture":   "Lean Risk-On",
        "action":    "Add (selective)",
        "gross_low": 1.30,
        "gross_high":1.35,
        "description": "Selective adds. Lean into strength.",
    },
    {
        "min_score": 40,
        "max_score": 59,
        "posture":   "Neutral",
        "action":    "Hold",
        "gross_low": 1.25,
        "gross_high":1.30,
        "description": "No new risk. Manage existing book.",
    },
    {
        "min_score": 20,
        "max_score": 39,
        "posture":   "Defensive",
        "action":    "Trim",
        "gross_low": 1.15,
        "gross_high":1.20,
        "description": "Reduce beta. Trim weaker positions.",
    },
    {
        "min_score": 0,
        "max_score": 19,
        "posture":   "Risk-Off",
        "action":    "Deleverage",
        "gross_low": 0.80,
        "gross_high":1.10,
        "description": "Raise cash. Significant deleveraging.",
    },
]

# ─── Regime Classifier ───────────────────────────────────────────────────────
REGIMES = [
    "Goldilocks Risk-On",
    "AI/Liquidity Melt-Up",
    "Inflation Scare",
    "Growth Scare",
    "Crisis Deleveraging",
    "Late-Cycle Narrow Rally",
    "Neutral/Transition",
]

# ─── Volatility Thresholds ───────────────────────────────────────────────────
VIX_LOW        = 18   # Below → bullish
VIX_ELEVATED   = 25   # Above → bearish
VIX_SPIKE_5D   = 3    # 5-day VIX change that triggers warning

# ─── Credit Spread Thresholds ────────────────────────────────────────────────
HY_SPREAD_WIDE   = 500   # bps — elevated stress
HY_SPREAD_NORMAL = 350   # bps — normal
HY_SPIKE_20D     = 75    # bps — sharp widening over 20 days

# ─── Real Yield Thresholds ───────────────────────────────────────────────────
REAL_YIELD_SPIKE = 0.30  # 20-day change in % — "rapid spike"

# ─── DXY Thresholds ──────────────────────────────────────────────────────────
DXY_STRONG_20D = 2.5   # % change — "sharply rising"
