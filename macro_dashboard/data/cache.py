"""
data/cache.py — Local CSV cache to avoid repeated API calls.
Data is stored in data/cache/ directory with TTL checking.
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(key: str) -> Path:
    safe_key = key.replace("/", "_").replace(".", "_").replace("^", "")
    return CACHE_DIR / f"{safe_key}.csv"


def load_cache(key: str, ttl_hours: float = 4.0) -> Optional[pd.DataFrame]:
    """
    Load cached data if it exists and is not stale.
    Returns None if cache miss or expired.
    """
    path = _cache_path(key)
    if not path.exists():
        return None

    # Check age
    mtime = path.stat().st_mtime
    age_hours = (time.time() - mtime) / 3600
    if age_hours > ttl_hours:
        return None

    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df if not df.empty else None
    except Exception:
        return None


def save_cache(key: str, df: pd.DataFrame) -> None:
    """Persist a DataFrame to the local cache."""
    if df is None or df.empty:
        return
    path = _cache_path(key)
    try:
        df.to_csv(path)
    except Exception as e:
        print(f"[cache] Failed to write {key}: {e}")


def clear_cache() -> None:
    """Remove all cached files."""
    for f in CACHE_DIR.glob("*.csv"):
        f.unlink()
    print("[cache] Cleared all cached files.")


def cache_info() -> dict:
    """Return summary of cached files and their ages."""
    info = {}
    for f in CACHE_DIR.glob("*.csv"):
        age_h = (time.time() - f.stat().st_mtime) / 3600
        info[f.stem] = {"age_hours": round(age_h, 2), "size_kb": round(f.stat().st_size / 1024, 1)}
    return info
