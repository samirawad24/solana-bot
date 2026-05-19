import pytest
from unittest.mock import patch

from strategy.combiner import evaluate_signals_detail


def _config(min_signals: int = 2, adx_enabled: bool = True, adx_value: float = 30.0) -> dict:
    return {
        "signals": {
            "rsi":      {"enabled": True,  "period": 14, "oversold": 30, "overbought": 70},
            "ema":      {"enabled": True,  "fast": 9, "slow": 21},
            "bollinger":{"enabled": True,  "period": 20, "std_dev": 2.0, "volume_multiplier": 1.5},
            "adx":      {"enabled": adx_enabled, "period": 14, "threshold": 25.0},
        },
        "strategy": {"min_signals": min_signals},
    }



def test_combiner_requires_min_signals(flat_df):
    cfg = _config(min_signals=2)

    # Only 1 buy signal → below min → neutral
    with patch("strategy.combiner.rsi_signal", return_value="buy"), \
         patch("strategy.combiner.ema_signal", return_value="neutral"), \
         patch("strategy.combiner.bollinger_signal", return_value="neutral"), \
         patch("strategy.combiner.get_adx_value", return_value=30.0):
        result = evaluate_signals_detail(flat_df, cfg)
    assert result["direction"] == "neutral"
    assert result["buy_count"] == 1

    # 2 buy signals → meets min → buy
    with patch("strategy.combiner.rsi_signal", return_value="buy"), \
         patch("strategy.combiner.ema_signal", return_value="buy"), \
         patch("strategy.combiner.bollinger_signal", return_value="neutral"), \
         patch("strategy.combiner.get_adx_value", return_value=30.0):
        result = evaluate_signals_detail(flat_df, cfg)
    assert result["direction"] == "buy"
    assert result["buy_count"] == 2
    assert result["sell_count"] == 0


def test_combiner_blocked_by_adx(flat_df):
    # ADX below threshold → neutral even with 3 buy signals
    with patch("strategy.combiner.rsi_signal", return_value="buy"), \
         patch("strategy.combiner.ema_signal", return_value="buy"), \
         patch("strategy.combiner.bollinger_signal", return_value="buy"), \
         patch("strategy.combiner.get_adx_value", return_value=20.0):
        result = evaluate_signals_detail(flat_df, _config())
    assert result["direction"] == "neutral"
    assert result["adx_passed"] is False
    assert result["adx_value"] == pytest.approx(20.0)


def test_combiner_conflicting_signals_neutral(flat_df):
    # 2 buy + 1 sell → mixed → neutral regardless of min_signals
    with patch("strategy.combiner.rsi_signal", return_value="buy"), \
         patch("strategy.combiner.ema_signal", return_value="buy"), \
         patch("strategy.combiner.bollinger_signal", return_value="sell"), \
         patch("strategy.combiner.get_adx_value", return_value=30.0):
        result = evaluate_signals_detail(flat_df, _config())
    assert result["direction"] == "neutral"
    assert result["buy_count"] == 2
    assert result["sell_count"] == 1
