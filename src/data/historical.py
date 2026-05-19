import time
from datetime import datetime, timedelta, timezone

import ccxt
import pandas as pd
from loguru import logger

_REQUEST_LIMIT = 1000  # asked-for candles per request; exchange may return fewer


def _build_exchange(exchange_id: str) -> ccxt.Exchange:
    cls = getattr(ccxt, exchange_id)
    return cls({"enableRateLimit": True})


def _raw_to_df(raw: list) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df.astype(float)


def fetch_historical_candles(
    symbol: str,
    timeframe: str,
    months: int,
    exchange_id: str = "coinbase",
) -> pd.DataFrame:
    """Fetch `months` of historical OHLCV candles, paginating through API limits.

    Pagination stops when the last returned candle is within one candle-period of
    now, not when a batch is smaller than the request limit — this handles
    exchanges (e.g. Coinbase) that cap responses below the requested limit.

    Uses 31-day months for the lookback window (conservative).

    Returns a DataFrame: columns open/high/low/close/volume, index UTC timestamp,
    no duplicates, sorted ascending.
    """
    exchange = _build_exchange(exchange_id)

    since_dt = datetime.now(timezone.utc) - timedelta(days=months * 31)
    since_ms = int(since_dt.timestamp() * 1000)

    all_candles: list = []
    batch_num = 0

    # We stop fetching once the last candle timestamp is within one period of now.
    from data.price_feed import timeframe_to_seconds
    period_ms = timeframe_to_seconds(timeframe) * 1000

    logger.info(f"Fetching {months}mo of {symbol} {timeframe} candles from {exchange_id}…")

    while True:
        batch_num += 1
        candles = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=_REQUEST_LIMIT)

        if not candles:
            break

        all_candles.extend(candles)
        newest_ms = candles[-1][0]
        newest_ts = datetime.fromtimestamp(newest_ms / 1000, tz=timezone.utc)
        logger.info(
            f"  Batch {batch_num}: +{len(candles)} candles "
            f"(total {len(all_candles)}, up to {newest_ts:%Y-%m-%d %H:%M})"
        )

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        if newest_ms >= now_ms - period_ms:
            break  # reached the present

        since_ms = newest_ms + 1  # next batch starts right after the last candle
        time.sleep(exchange.rateLimit / 1000)

    if not all_candles:
        raise RuntimeError(
            f"No historical candles returned for {symbol} {timeframe} on {exchange_id}. "
            "Check the symbol name and exchange."
        )

    df = _raw_to_df(all_candles)
    df = df[~df.index.duplicated(keep="first")]
    df.sort_index(inplace=True)

    logger.success(
        f"Loaded {len(df):,} candles: {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}"
    )
    return df
