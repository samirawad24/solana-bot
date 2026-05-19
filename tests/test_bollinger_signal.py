import numpy as np
import pytest

from conftest import make_ohlcv
from strategy.bollinger_signal import bollinger_signal


def _make_bollinger_df(last_close: float, last_volume: float) -> object:
    """25 bars: first 24 at close=100/vol=1000, last bar customised."""
    prices = np.array([100.0] * 24 + [last_close])
    volume = np.array([1000.0] * 24 + [last_volume])
    return make_ohlcv(prices, volume)


def test_bollinger_buy_with_volume():
    # Close well below lower band + large volume spike → 'buy'
    # avg_vol = (19*1000 + 5000)/20 = 1200; 5000 > 1.5*1200 ✓
    df = _make_bollinger_df(last_close=50.0, last_volume=5000.0)
    assert bollinger_signal(df) == "buy"


def test_bollinger_buy_without_volume_confirmation():
    # Close below lower band but volume too low → 'neutral'
    # avg_vol = (19*1000 + 1400)/20 = 1020; 1400 < 1.5*1020=1530
    df = _make_bollinger_df(last_close=50.0, last_volume=1400.0)
    assert bollinger_signal(df) == "neutral"


def test_bollinger_sell():
    # Close well above upper band + large volume spike → 'sell'
    df = _make_bollinger_df(last_close=150.0, last_volume=5000.0)
    assert bollinger_signal(df) == "sell"

    # Insufficient data (need period=20 bars, only 10)
    df_short = make_ohlcv(np.full(10, 100.0))
    assert bollinger_signal(df_short) == "neutral"
