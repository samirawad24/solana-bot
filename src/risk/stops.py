import pandas as pd
from ta.volatility import AverageTrueRange


def get_atr_value(df: pd.DataFrame, period: int = 14) -> float | None:
    """Return the latest ATR value, or None if insufficient data."""
    if len(df) < period + 1:
        return None
    atr = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=period
    ).average_true_range()
    val = atr.iloc[-1]
    return None if pd.isna(val) else float(val)


def calculate_stops(
    df: pd.DataFrame,
    entry_price: float,
    direction: str,
    atr_period: int = 14,
    sl_atr: float = 2.0,
    tp_atr: float = 3.0,
) -> tuple[float, float]:
    """Return (stop_loss_price, take_profit_price) based on ATR multiples.

    For 'buy':
        stop_loss   = entry - sl_atr × ATR
        take_profit = entry + tp_atr × ATR

    For 'sell':
        stop_loss   = entry + sl_atr × ATR
        take_profit = entry - tp_atr × ATR

    Raises:
        ValueError: If direction is not 'buy' or 'sell'.
        ValueError: If there is insufficient data to compute ATR.
        ValueError: If the computed ATR is zero or NaN.
    """
    if direction not in ("buy", "sell"):
        raise ValueError(f"direction must be 'buy' or 'sell', got {direction!r}")

    if len(df) < atr_period + 1:
        raise ValueError(
            f"Need at least {atr_period + 1} rows to compute ATR(period={atr_period}), "
            f"got {len(df)}."
        )

    atr_series = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=atr_period
    ).average_true_range()

    atr = atr_series.iloc[-1]
    if pd.isna(atr) or atr <= 0:
        raise ValueError(
            f"ATR could not be computed from the provided data (raw value={atr})."
        )

    if direction == "buy":
        stop_loss   = entry_price - sl_atr * atr
        take_profit = entry_price + tp_atr * atr
    else:
        stop_loss   = entry_price + sl_atr * atr
        take_profit = entry_price - tp_atr * atr

    return stop_loss, take_profit
