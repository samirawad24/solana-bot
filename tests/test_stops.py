import numpy as np
import pytest

from conftest import make_ohlcv
from risk.stops import calculate_stops, get_atr_value


# flat_df: 50 bars, close=100, high=100.1, low=99.9
# TR = max(0.2, 0.1, 0.1) = 0.2 → ATR = 0.2 (constant)


def test_stops_buy_direction(flat_df):
    # sl = 100 - 2*0.2 = 99.6 ; tp = 100 + 3*0.2 = 100.6
    atr = get_atr_value(flat_df)
    assert atr == pytest.approx(0.2)

    sl, tp = calculate_stops(flat_df, entry_price=100.0, direction="buy")
    assert sl == pytest.approx(99.6)
    assert tp == pytest.approx(100.6)


def test_stops_sell_direction(flat_df):
    # sl = 100 + 2*0.2 = 100.4 ; tp = 100 - 3*0.2 = 99.4
    sl, tp = calculate_stops(flat_df, entry_price=100.0, direction="sell")
    assert sl == pytest.approx(100.4)
    assert tp == pytest.approx(99.4)

    # Insufficient data (need atr_period+1 = 15 bars, tiny_df has 5)
    tiny = make_ohlcv(np.full(5, 100.0))
    with pytest.raises(ValueError, match="rows"):
        calculate_stops(tiny, entry_price=100.0, direction="buy")

    # Invalid direction → ValueError
    with pytest.raises(ValueError, match="direction"):
        calculate_stops(flat_df, entry_price=100.0, direction="long")
