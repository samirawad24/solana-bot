import numpy as np
import pytest

from conftest import make_ohlcv
from strategy.ema_signal import ema_signal, get_ema_values


def test_ema_golden_cross():
    # Warmup at 100 → downtrend → spike: fast crosses above slow
    prices = np.concatenate([
        np.full(30, 100.0),
        np.linspace(100, 70, 20),
        [500.0],
    ])
    df = make_ohlcv(prices)
    assert ema_signal(df) == "buy"
    fast, slow = get_ema_values(df)
    assert fast is not None and slow is not None
    assert fast > slow


def test_ema_death_cross():
    # Warmup at 100 → uptrend → crash: fast crosses below slow
    prices = np.concatenate([
        np.full(30, 100.0),
        np.linspace(100, 130, 20),
        [1.0],
    ])
    df = make_ohlcv(prices)
    assert ema_signal(df) == "sell"
    fast, slow = get_ema_values(df)
    assert fast is not None and slow is not None
    assert fast < slow


def test_ema_no_cross():
    # Insufficient data (need slow+1 = 22 bars)
    df_short = make_ohlcv(np.full(20, 100.0))
    assert ema_signal(df_short) == "neutral"
    assert get_ema_values(df_short) == (None, None)

    # Flat prices → fast_ema == slow_ema → no crossover at any bar
    df_flat = make_ohlcv(np.full(50, 100.0))
    assert ema_signal(df_flat) == "neutral"
