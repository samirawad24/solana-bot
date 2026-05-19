import pandas as pd
from ta.trend import ADXIndicator


def adx_filter(df: pd.DataFrame, period: int = 14, threshold: float = 25.0) -> bool:
    """Return True if the latest ADX > threshold (market is trending).

    ADX requires high, low, and close columns. Wilder smoothing means the
    indicator needs roughly 2×period rows to produce a stable value; returns
    False if data is insufficient or the value is NaN.
    """
    if len(df) < period * 2:
        return False

    adx = ADXIndicator(
        high=df["high"], low=df["low"], close=df["close"], window=period
    ).adx()

    latest = adx.iloc[-1]
    if pd.isna(latest):
        return False
    return float(latest) > threshold


def get_adx_value(df: pd.DataFrame, period: int = 14) -> float | None:
    """Return the latest ADX value, or None if insufficient data."""
    if len(df) < period * 2:
        return None
    adx = ADXIndicator(
        high=df["high"], low=df["low"], close=df["close"], window=period
    ).adx()
    val = adx.iloc[-1]
    return None if pd.isna(val) else float(val)
