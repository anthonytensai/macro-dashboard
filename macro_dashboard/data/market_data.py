"""
data/market_data.py — Fetch market price data via yfinance with local CSV caching.
Handles missing tickers gracefully; never crashes the dashboard.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import warnings
warnings.filterwarnings("ignore")

from data.cache import load_cache, save_cache
from config import CACHE_TTL_HOURS, LOOKBACK_DAYS

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    print("[market_data] yfinance not installed — returning empty data.")


# All tickers used across signal layers
MARKET_TICKERS = [
    "SPY", "QQQ", "ACWI", "RSP",        # Trend / Breadth
    "SMH", "SOXX", "IWM",               # Momentum / Risk Appetite / Breadth
    "^VIX",                              # Volatility
    "HYG", "LQD", "KRE",                # Credit
    "UUP",                               # Liquidity / DXY proxy
    "GLD",                               # Risk Appetite
    "XLU", "XLY", "XLP",                # Risk Appetite
    "BTC-USD",                           # Risk Appetite
]


def fetch_prices(tickers: list, period_days: int = LOOKBACK_DAYS) -> Dict[str, pd.Series]:
    """
    Download adjusted close prices for all tickers.
    Returns dict of ticker → pd.Series indexed by date.
    Missing tickers return an empty Series with a warning.
    """
    if not YF_AVAILABLE:
        return {t: pd.Series(dtype=float, name=t) for t in tickers}

    results: Dict[str, pd.Series] = {}
    cache_key = f"market_prices_{period_days}d"
    cached = load_cache(cache_key, CACHE_TTL_HOURS)

    if cached is not None:
        for t in tickers:
            if t in cached.columns:
                results[t] = cached[t].dropna()
            else:
                results[t] = pd.Series(dtype=float, name=t)
        return results

    # Download all tickers at once (faster than individual calls)
    try:
        period_str = f"{period_days}d"
        raw = yf.download(
            tickers,
            period=period_str,
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # yfinance returns multi-level columns when multiple tickers are passed
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]].rename(columns={"Close": tickers[0]})

        save_cache(cache_key, prices)

        for t in tickers:
            if t in prices.columns:
                s = prices[t].dropna()
                results[t] = s
            else:
                print(f"[market_data] Warning: {t} not available.")
                results[t] = pd.Series(dtype=float, name=t)

    except Exception as e:
        print(f"[market_data] Download error: {e}")
        for t in tickers:
            results[t] = pd.Series(dtype=float, name=t)

    return results


def get_all_prices() -> Dict[str, pd.Series]:
    """Convenience: fetch all dashboard tickers."""
    return fetch_prices(MARKET_TICKERS)


def compute_dma(series: pd.Series, window: int) -> pd.Series:
    """Return simple moving average."""
    return series.rolling(window=window, min_periods=max(1, window // 2)).mean()


def compute_roc(series: pd.Series, period: int) -> float:
    """Rate of change over N days (%). Returns NaN if insufficient data."""
    if len(series) < period + 1:
        return float("nan")
    return (series.iloc[-1] / series.iloc[-period - 1] - 1) * 100


def latest(series: pd.Series) -> float:
    """Return the most recent non-NaN value, or NaN."""
    if series is None or series.empty:
        return float("nan")
    return series.dropna().iloc[-1] if not series.dropna().empty else float("nan")


def ratio_series(a: pd.Series, b: pd.Series) -> pd.Series:
    """Compute ratio A/B, aligned by date."""
    if a.empty or b.empty:
        return pd.Series(dtype=float)
    df = pd.DataFrame({"a": a, "b": b}).dropna()
    return df["a"] / df["b"]
