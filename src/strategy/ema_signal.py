import pandas as pd
from ta.trend import EMAIndicator


def ema_signal(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> str:
    """Return 'buy', 'sell', or 'neutral' based on EMA crossover on the last two candles.

    'buy'  — fast EMA crossed above slow EMA (golden cross).
    'sell' — fast EMA crossed below slow EMA (death cross).
    'neutral' — no crossover on the most recent candle, or insufficient data.

    Requires at least slow+1 rows for two consecutive valid EMA values.
    """
    if len(df) < slow + 1:
        return "neutral"

    fast_ema = EMAIndicator(close=df["close"], window=fast).ema_indicator()
    slow_ema = EMAIndicator(close=df["close"], window=slow).ema_indicator()

    prev_fast, curr_fast = fast_ema.iloc[-2], fast_ema.iloc[-1]
    prev_slow, curr_slow = slow_ema.iloc[-2], slow_ema.iloc[-1]

    if pd.isna(prev_fast) or pd.isna(prev_slow):
        return "neutral"

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "buy"   # golden cross
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "sell"  # death cross
    return "neutral"


def get_ema_values(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> tuple[float | None, float | None]:
    """Return (latest_fast_ema, latest_slow_ema), or (None, None) if insufficient data."""
    if len(df) < slow:
        return None, None
    fast_val = EMAIndicator(close=df["close"], window=fast).ema_indicator().iloc[-1]
    slow_val = EMAIndicator(close=df["close"], window=slow).ema_indicator().iloc[-1]
    return (
        None if pd.isna(fast_val) else float(fast_val),
        None if pd.isna(slow_val) else float(slow_val),
    )
