import pandas as pd
from ta.momentum import RSIIndicator


def rsi_signal(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> str:
    """Return 'buy', 'sell', or 'neutral' based on the latest RSI value.

    Requires at least period+1 rows. Returns 'neutral' when there is not
    enough data or when the RSI value is between the two thresholds.
    """
    if len(df) < period + 1:
        return "neutral"

    rsi = RSIIndicator(close=df["close"], window=period).rsi()
    latest = rsi.iloc[-1]

    if pd.isna(latest):
        return "neutral"
    if latest < oversold:
        return "buy"
    if latest > overbought:
        return "sell"
    return "neutral"


def get_rsi_value(df: pd.DataFrame, period: int = 14) -> float | None:
    """Return the latest RSI value, or None if insufficient data."""
    if len(df) < period + 1:
        return None
    rsi = RSIIndicator(close=df["close"], window=period).rsi()
    val = rsi.iloc[-1]
    return None if pd.isna(val) else float(val)
