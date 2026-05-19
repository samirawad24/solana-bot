"""Shared fixtures and helpers for the test suite.

Path setup is done here once so individual test files don't need sys.path manipulation.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_HERE = Path(__file__).parent
# Add src/ to path so all strategy/risk/portfolio imports resolve
sys.path.insert(0, str(_HERE.parent / "src"))
# Add tests/ to path so test files can do `from conftest import make_ohlcv`
sys.path.insert(0, str(_HERE))


# ── DataFrame factory ─────────────────────────────────────────────────────────

def make_ohlcv(
    close,
    volume=None,
    spread_pct: float = 0.001,
    freq: str = "15min",
) -> pd.DataFrame:
    """Build an OHLCV DataFrame from a sequence of close prices.

    high = close × (1 + spread_pct)
    low  = close × (1 − spread_pct)
    open = previous close (first bar: same as close)
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    if volume is None:
        volume = np.full(n, 1000.0)
    else:
        volume = np.asarray(volume, dtype=float)

    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]          # realistic: open = prev close

    return pd.DataFrame(
        {
            "open":   open_,
            "high":   close * (1.0 + spread_pct),
            "low":    close * (1.0 - spread_pct),
            "close":  close,
            "volume": volume,
        },
        index=pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC"),
    )


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def simple_df() -> pd.DataFrame:
    """50-bar OHLCV with gently oscillating prices — neither buy nor sell signal."""
    t = np.arange(50)
    prices = 50.0 + 3.0 * np.sin(2 * np.pi * t / 20)
    return make_ohlcv(prices)


@pytest.fixture()
def flat_df() -> pd.DataFrame:
    """50-bar OHLCV at a constant price of 100 — deterministic ATR = 0.1."""
    return make_ohlcv(np.full(50, 100.0), spread_pct=0.001)


@pytest.fixture()
def tiny_df() -> pd.DataFrame:
    """5-bar OHLCV — too short for any indicator to produce a valid value."""
    return make_ohlcv(np.full(5, 100.0))
