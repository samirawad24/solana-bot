import numpy as np
import pytest

from conftest import make_ohlcv
from strategy.adx_filter import adx_filter, get_adx_value


def test_adx_trending():
    # Strong monotone uptrend: all +DM, no -DM → ADX >> 25
    df = make_ohlcv(np.linspace(50, 200, 60))
    assert adx_filter(df) is True
    val = get_adx_value(df)
    assert val is not None and val > 25

    # Insufficient data (need period*2 = 28 bars)
    df_short = make_ohlcv(np.linspace(50, 200, 20))
    assert adx_filter(df_short) is False
    assert get_adx_value(df_short) is None


def test_adx_ranging():
    # Alternating ±10 prices: +DM ≈ -DM → ADX << 25
    prices = np.array([100.0 + (10 if i % 2 == 0 else -10) for i in range(60)])
    df = make_ohlcv(prices)
    assert adx_filter(df) is False
    val = get_adx_value(df)
    assert val is not None and val < 25
