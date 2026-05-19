import numpy as np
import pytest

from conftest import make_ohlcv
from strategy.rsi_signal import get_rsi_value, rsi_signal


def test_rsi_buy_signal():
    # Pure downtrend: avg_gain=0 → RSI≈0 → 'buy'
    df = make_ohlcv(np.linspace(100, 50, 50))
    assert rsi_signal(df) == "buy"
    val = get_rsi_value(df)
    assert val is not None and val < 30


def test_rsi_sell_signal():
    # Pure uptrend: avg_loss=0 → RSI≈100 → 'sell'
    df = make_ohlcv(np.linspace(50, 100, 50))
    assert rsi_signal(df) == "sell"
    val = get_rsi_value(df)
    assert val is not None and val > 70


def test_rsi_neutral():
    # Insufficient data: returns 'neutral' and get_rsi_value returns None
    df_tiny = make_ohlcv(np.full(5, 100.0))
    assert rsi_signal(df_tiny) == "neutral"
    assert get_rsi_value(df_tiny) is None

    # Alternating prices → avg_gain ≈ avg_loss → RSI ≈ 50 → 'neutral'
    prices = np.array([100.0 + (i % 2) for i in range(50)])
    df = make_ohlcv(prices)
    assert rsi_signal(df) == "neutral"
    val = get_rsi_value(df)
    assert val is not None and 30 <= val <= 70
