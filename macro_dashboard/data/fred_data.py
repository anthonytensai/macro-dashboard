"""
data/fred_data.py — Fetch macro series from FRED via fredapi or pandas_datareader.
Falls back gracefully if API key is missing or series is unavailable.
"""

import pandas as pd
import numpy as np
from typing import Optional
import os
import warnings
warnings.filterwarnings("ignore")

from data.cache import load_cache, save_cache
from config import CACHE_TTL_HOURS, FRED_API_KEY

# Try to load FRED API key from environment
_api_key = os.getenv("FRED_API_KEY", FRED_API_KEY)

# FRED series IDs used in the dashboard
FRED_SERIES = {
    "hy_spread":       "BAMLH0A0HYM2",    # HY OAS spread (bps)
    "ig_spread":       "BAMLC0A0CM",       # IG OAS spread (bps)
    "fed_balance":     "WALCL",            # Fed balance sheet (millions USD)
    "rrp":             "RRPONTSYD",        # Reverse repo (billions USD)
    "us10y":           "DGS10",            # 10Y Treasury yield (%)
    "us2y":            "DGS2",             # 2Y Treasury yield (%)
    "us3m":            "DGS3MO",           # 3M Treasury yield (%)
    "real_yield_10y":  "DFII10",           # 10Y TIPS real yield (%)
}


def _fetch_via_fredapi(series_id: str, start: str = "2020-01-01") -> Optional[pd.Series]:
    """Fetch using fredapi library (requires FRED API key)."""
    try:
        from fredapi import Fred
        fred = Fred(api_key=_api_key)
        s = fred.get_series(series_id, observation_start=start)
        s.name = series_id
        return s
    except Exception as e:
        return None


def _fetch_via_datareader(series_id: str, start: str = "2020-01-01") -> Optional[pd.Series]:
    """Fetch using pandas_datareader as fallback (no key required)."""
    try:
        import pandas_datareader.data as web
        df = web.DataReader(series_id, "fred", start=start)
        return df.iloc[:, 0]
    except Exception as e:
        return None


def fetch_fred_series(key: str, start: str = "2020-01-01") -> pd.Series:
    """
    Fetch a FRED series by our internal key name.
    Tries fredapi first, then pandas_datareader, then returns empty Series.
    """
    series_id = FRED_SERIES.get(key)
    if not series_id:
        print(f"[fred_data] Unknown series key: {key}")
        return pd.Series(dtype=float, name=key)

    cache_key = f"fred_{key}"
    cached = load_cache(cache_key, CACHE_TTL_HOURS)
    if cached is not None and not cached.empty:
        col = cached.columns[0] if not cached.empty else None
        return cached[col] if col else pd.Series(dtype=float, name=key)

    # Try fredapi first, then datareader
    series = None
    if _api_key:
        series = _fetch_via_fredapi(series_id, start)
    if series is None:
        series = _fetch_via_datareader(series_id, start)
    if series is None:
        print(f"[fred_data] Warning: Could not fetch {series_id} ({key}). Using empty placeholder.")
        return pd.Series(dtype=float, name=key)

    series.name = key
    save_cache(cache_key, series.to_frame())
    return series


def fetch_all_fred() -> dict:
    """Fetch all FRED series used in the dashboard. Returns dict of key → Series."""
    data = {}
    for key in FRED_SERIES:
        data[key] = fetch_fred_series(key)
    return data


def latest_fred(key: str, data: dict) -> float:
    """Get most recent non-NaN value of a FRED series."""
    s = data.get(key, pd.Series(dtype=float))
    clean = s.dropna()
    return float(clean.iloc[-1]) if not clean.empty else float("nan")
