import math
import time

import ccxt
import pandas as pd
from loguru import logger

_TIMEFRAME_MULTIPLIERS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}


def timeframe_to_seconds(timeframe: str) -> int:
    """Convert a CCXT timeframe string (e.g. '15m', '1h') to seconds."""
    unit = timeframe[-1]
    count = int(timeframe[:-1])
    return count * _TIMEFRAME_MULTIPLIERS[unit]


def _build_exchange(exchange_id: str) -> ccxt.Exchange:
    cls = getattr(ccxt, exchange_id)
    return cls({"enableRateLimit": True})


def _raw_to_df(raw: list) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df.astype(float)


def get_latest_candles(
    symbol: str,
    timeframe: str,
    limit: int = 100,
    exchange_id: str = "binance",
) -> pd.DataFrame:
    """Return the most recent `limit` CLOSED candles as a DataFrame.

    Fetches limit+1 rows and drops the last (currently-forming) candle so that
    all returned rows represent fully settled price action.

    Columns: open, high, low, close, volume  (index: UTC timestamp)
    """
    exchange = _build_exchange(exchange_id)
    raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit + 1)
    df = _raw_to_df(raw)
    return df.iloc[:-1]  # drop the open/incomplete candle


def seconds_until_close(timeframe: str) -> float:
    """Return seconds remaining until the current candle closes."""
    interval = timeframe_to_seconds(timeframe)
    now = time.time()
    next_close = (math.floor(now / interval) + 1) * interval
    return next_close - now


def wait_for_next_candle(timeframe: str, buffer_seconds: int = 2) -> None:
    """Block until the current candle closes, then wait `buffer_seconds` more.

    The extra buffer ensures the exchange has settled the candle before we fetch.
    """
    wait = seconds_until_close(timeframe) + buffer_seconds
    logger.info(f"Next {timeframe} candle closes in {wait:.0f}s — sleeping")
    time.sleep(wait)
