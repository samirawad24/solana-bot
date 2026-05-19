import pandas as pd
from ta.volatility import BollingerBands


def bollinger_signal(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    volume_multiplier: float = 1.5,
) -> str:
    """Return 'buy', 'sell', or 'neutral' based on Bollinger Band touches with volume confirmation.

    'buy'  — latest close <= lower band AND volume > volume_multiplier × rolling average.
    'sell' — latest close >= upper band AND volume > volume_multiplier × rolling average.

    Volume rolling average uses the same window as the BB period.
    Returns 'neutral' if volume confirmation fails or data is insufficient.
    """
    if len(df) < period:
        return "neutral"

    bb = BollingerBands(close=df["close"], window=period, window_dev=std_dev)
    lower = bb.bollinger_lband().iloc[-1]
    upper = bb.bollinger_hband().iloc[-1]

    if pd.isna(lower) or pd.isna(upper):
        return "neutral"

    latest_close = df["close"].iloc[-1]
    latest_vol = df["volume"].iloc[-1]
    avg_vol = df["volume"].rolling(period).mean().iloc[-1]

    if pd.isna(avg_vol) or avg_vol == 0:
        return "neutral"

    vol_confirmed = latest_vol > volume_multiplier * avg_vol

    if latest_close <= lower and vol_confirmed:
        return "buy"
    if latest_close >= upper and vol_confirmed:
        return "sell"
    return "neutral"


def get_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> tuple[float | None, float | None, float | None]:
    """Return (lower_band, middle_band, upper_band) for the latest candle."""
    if len(df) < period:
        return None, None, None
    bb = BollingerBands(close=df["close"], window=period, window_dev=std_dev)
    lo = bb.bollinger_lband().iloc[-1]
    mid = bb.bollinger_mavg().iloc[-1]
    hi = bb.bollinger_hband().iloc[-1]
    return (
        None if pd.isna(lo) else float(lo),
        None if pd.isna(mid) else float(mid),
        None if pd.isna(hi) else float(hi),
    )
