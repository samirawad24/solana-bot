import pandas as pd

from strategy.rsi_signal import rsi_signal
from strategy.ema_signal import ema_signal
from strategy.bollinger_signal import bollinger_signal
from strategy.adx_filter import adx_filter, get_adx_value

# Maps signal name -> callable(df, signal_config_dict) -> 'buy'|'sell'|'neutral'
_SIGNAL_FNS = {
    "rsi": lambda df, c: rsi_signal(
        df, period=c["period"], oversold=c["oversold"], overbought=c["overbought"]
    ),
    "ema": lambda df, c: ema_signal(
        df, fast=c["fast"], slow=c["slow"]
    ),
    "bollinger": lambda df, c: bollinger_signal(
        df, period=c["period"], std_dev=c["std_dev"], volume_multiplier=c["volume_multiplier"]
    ),
}


def evaluate_signals_detail(df: pd.DataFrame, config: dict) -> dict:
    """Evaluate all enabled signals and return a full breakdown dict.

    Keys:
        direction   — 'buy', 'sell', or 'neutral'
        signals     — {name: signal_str} for each enabled directional signal
        adx_passed  — bool (True when ADX gate is disabled or ADX > threshold)
        adx_value   — float | None
        buy_count   — number of directional signals returning 'buy'
        sell_count  — number of directional signals returning 'sell'
        min_required — threshold from config

    Decision rules:
        1. If ADX gate is enabled and ADX <= threshold → neutral (market ranging).
        2. 'buy'  requires buy_count  >= min_required AND sell_count == 0.
        3. 'sell' requires sell_count >= min_required AND buy_count  == 0.
        4. Mixed or insufficient signals → neutral.
    """
    sig_cfg     = config["signals"]
    min_signals = config["strategy"]["min_signals"]

    # ── ADX gate ──────────────────────────────────────────────────────────────
    adx_passed = True
    adx_value  = None
    if sig_cfg["adx"]["enabled"]:
        adx_cfg   = sig_cfg["adx"]
        adx_value = get_adx_value(df, period=adx_cfg["period"])
        adx_passed = adx_value is not None and adx_value > adx_cfg["threshold"]

    # ── Directional signals ───────────────────────────────────────────────────
    signals: dict[str, str] = {}
    for name, fn in _SIGNAL_FNS.items():
        if sig_cfg[name]["enabled"]:
            signals[name] = fn(df, sig_cfg[name])

    buy_count  = sum(1 for v in signals.values() if v == "buy")
    sell_count = sum(1 for v in signals.values() if v == "sell")

    # ── Confluence decision ───────────────────────────────────────────────────
    if not adx_passed:
        direction = "neutral"
    elif buy_count >= min_signals and sell_count == 0:
        direction = "buy"
    elif sell_count >= min_signals and buy_count == 0:
        direction = "sell"
    else:
        direction = "neutral"

    return {
        "direction":    direction,
        "signals":      signals,
        "adx_passed":   adx_passed,
        "adx_value":    adx_value,
        "buy_count":    buy_count,
        "sell_count":   sell_count,
        "min_required": min_signals,
    }


def evaluate_signals(df: pd.DataFrame, config: dict) -> str:
    """Return 'buy', 'sell', or 'neutral' — thin wrapper around evaluate_signals_detail."""
    return evaluate_signals_detail(df, config)["direction"]
