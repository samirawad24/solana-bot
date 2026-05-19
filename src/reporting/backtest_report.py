from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy
from bokeh.io import output_file, save
from bokeh.layouts import column
from bokeh.models import (
    BoxAnnotation,
    ColumnDataSource,
    CrosshairTool,
    DatetimeTickFormatter,
    HoverTool,
    Range1d,
    Span,
)
from bokeh.plotting import figure
from loguru import logger
from rich.console import Console
from rich.table import Table
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands


# ── Strategy factory ──────────────────────────────────────────────────────────

def _make_strategy(config: dict) -> type:
    sig   = config["signals"]
    stops = config["stops"]
    port  = config["portfolio"]
    strat = config["strategy"]

    class SolanaStrategy(Strategy):
        def init(self) -> None:
            c  = self.data.Close
            h  = self.data.High
            lo = self.data.Low
            v  = self.data.Volume

            def _s(arr): return pd.Series(arr)
            def _rsi(c):       return RSIIndicator(_s(c), window=sig["rsi"]["period"]).rsi().values
            def _ema(c, w):    return EMAIndicator(_s(c), window=w).ema_indicator().values
            def _bb_lo(c):     return BollingerBands(_s(c), window=sig["bollinger"]["period"], window_dev=sig["bollinger"]["std_dev"]).bollinger_lband().values
            def _bb_hi(c):     return BollingerBands(_s(c), window=sig["bollinger"]["period"], window_dev=sig["bollinger"]["std_dev"]).bollinger_hband().values
            def _vol_avg(v):   return _s(v).rolling(sig["bollinger"]["period"]).mean().values
            def _adx(h,l,c):   return ADXIndicator(_s(h), _s(l), _s(c), window=sig["adx"]["period"]).adx().values
            def _atr(h,l,c):   return AverageTrueRange(_s(h), _s(l), _s(c), window=stops["atr_period"]).average_true_range().values

            self._rsi      = self.I(_rsi,    c,       name="RSI",      overlay=False)
            self._ema_fast = self.I(_ema,    c, sig["ema"]["fast"], name="EMA_fast", overlay=True,  color="blue")
            self._ema_slow = self.I(_ema,    c, sig["ema"]["slow"], name="EMA_slow", overlay=True,  color="orange")
            self._bb_lo    = self.I(_bb_lo,  c,       name="BB_lower", overlay=True,  color="gray")
            self._bb_hi    = self.I(_bb_hi,  c,       name="BB_upper", overlay=True,  color="gray")
            self._vol_avg  = self.I(_vol_avg, v,      name="Vol_avg",  overlay=False)
            self._adx      = self.I(_adx,    h, lo, c, name="ADX",    overlay=False)
            self._atr      = self.I(_atr,    h, lo, c, name="ATR",    overlay=False)

        def next(self) -> None:
            c  = float(self.data.Close[-1])
            vo = float(self.data.Volume[-1])
            if any(np.isnan(x) for x in (self._rsi[-1], self._adx[-1], self._atr[-1], self._bb_lo[-1], self._bb_hi[-1], self._vol_avg[-1])):
                return
            atr = float(self._atr[-1])
            if atr <= 0:
                return
            if sig["adx"]["enabled"] and float(self._adx[-1]) <= sig["adx"]["threshold"]:
                return
            buy = sell = 0
            if sig["rsi"]["enabled"]:
                rv = float(self._rsi[-1])
                if rv < sig["rsi"]["oversold"]:   buy  += 1
                elif rv > sig["rsi"]["overbought"]: sell += 1
            if sig["ema"]["enabled"] and not np.isnan(self._ema_fast[-2]):
                pf, cf = float(self._ema_fast[-2]), float(self._ema_fast[-1])
                ps, cs = float(self._ema_slow[-2]), float(self._ema_slow[-1])
                if pf <= ps and cf > cs: buy  += 1
                elif pf >= ps and cf < cs: sell += 1
            if sig["bollinger"]["enabled"]:
                vol_ok = vo > sig["bollinger"]["volume_multiplier"] * float(self._vol_avg[-1])
                if c <= float(self._bb_lo[-1]) and vol_ok: buy  += 1
                elif c >= float(self._bb_hi[-1]) and vol_ok: sell += 1
            min_s = strat["min_signals"]
            if not self.position:
                if buy >= min_s and sell == 0:
                    sl  = c - stops["stop_loss_atr"] * atr
                    tp  = c + stops["take_profit_atr"] * atr
                    rpu = c - sl
                    if rpu > 0:
                        size = min(1.0, (port["risk_per_trade"] * c) / rpu)
                        self.buy(size=size, sl=sl, tp=tp)
            else:
                if sell >= min_s and buy == 0:
                    self.position.close()

    return SolanaStrategy


# ── Chart helpers ─────────────────────────────────────────────────────────────

_BG   = "#0d1117"   # panel background
_BORDER = "#161b22" # border / axis area
_GRID = "#21262d"   # grid line colour
_TEXT = "#c9d1d9"   # axis label / title text
_UP   = "#3fb950"   # bullish candle / win
_DOWN = "#f85149"   # bearish candle / loss
_EMA_F = "#79c0ff"  # fast EMA line
_EMA_S = "#ffa657"  # slow EMA line
_BB   = "#8b949e"   # bollinger band lines
_RSI  = "#d2a8ff"   # RSI line
_ADX  = "#ffd700"   # ADX line
_EQ   = "#58a6ff"   # equity curve
_VOL_U = "#3fb950"
_VOL_D = "#f85149"


def _style(p: object, x_visible: bool = True) -> None:
    """Apply dark-theme styling to a Bokeh figure."""
    p.background_fill_color  = _BG
    p.border_fill_color      = _BORDER
    p.outline_line_color      = "#30363d"
    p.grid.grid_line_color    = _GRID
    p.grid.grid_line_alpha    = 0.5
    p.axis.axis_label_text_color = _TEXT
    p.axis.major_label_text_color = _TEXT
    p.axis.axis_line_color    = "#30363d"
    p.axis.major_tick_line_color = "#30363d"
    p.axis.minor_tick_line_color = None
    p.title.text_color        = _TEXT
    p.title.text_font_size    = "13pt"
    p.title.text_font         = "monospace"
    if not x_visible:
        p.xaxis.visible = False

    dt_fmt = DatetimeTickFormatter(
        hours="%d %b %H:%M",
        days="%d %b",
        months="%b %Y",
    )
    p.xaxis.formatter = dt_fmt


def _build_html_chart(
    df: pd.DataFrame,
    stats: pd.Series,
    config: dict,
    report_path: Path,
) -> None:
    """Write a standalone dark-theme Bokeh chart to report_path."""
    sig  = config["signals"]

    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    opn   = df["open"]
    vol   = df["volume"]
    x     = df.index  # DatetimeIndex (tz-naive UTC)

    # ── Indicators ────────────────────────────────────────────────────────────
    rsi_s   = RSIIndicator(close=close, window=sig["rsi"]["period"]).rsi()
    ema_f   = EMAIndicator(close=close, window=sig["ema"]["fast"]).ema_indicator()
    ema_s   = EMAIndicator(close=close, window=sig["ema"]["slow"]).ema_indicator()
    _bb     = BollingerBands(close=close, window=sig["bollinger"]["period"],
                              window_dev=sig["bollinger"]["std_dev"])
    bb_hi   = _bb.bollinger_hband()
    bb_lo   = _bb.bollinger_lband()
    bb_mid  = _bb.bollinger_mavg()
    adx_s   = ADXIndicator(high=high, low=low, close=close,
                            window=sig["adx"]["period"]).adx()
    vol_avg = vol.rolling(sig["bollinger"]["period"]).mean()
    equity  = stats._equity_curve["Equity"]

    # ── Trades ────────────────────────────────────────────────────────────────
    trades    = stats._trades.copy() if len(stats._trades) > 0 else pd.DataFrame()
    win_mask  = trades["PnL"] > 0  if not trades.empty else pd.Series(dtype=bool)
    loss_mask = ~win_mask           if not trades.empty else pd.Series(dtype=bool)

    # ── Candle bar width (80 % of timeframe in ms) ────────────────────────────
    if len(df) > 1:
        bar_ms = (df.index[1] - df.index[0]).total_seconds() * 1000 * 0.8
    else:
        bar_ms = 900_000 * 0.8

    candle_top = np.maximum(opn.values, close.values)
    candle_bot = np.minimum(opn.values, close.values)
    is_up      = close.values >= opn.values
    c_color    = [_UP if u else _DOWN for u in is_up]
    v_color    = [_VOL_U if u else _VOL_D for u in is_up]

    # ── Shared data sources ───────────────────────────────────────────────────
    ohlcv_src = ColumnDataSource({
        "x":      x,
        "open":   opn.values,
        "high":   high.values,
        "low":    low.values,
        "close":  close.values,
        "volume": vol.values,
        "top":    candle_top,
        "bot":    candle_bot,
        "color":  c_color,
        "vcol":   v_color,
        "ema_f":  ema_f.values,
        "ema_s":  ema_s.values,
        "bb_hi":  bb_hi.values,
        "bb_lo":  bb_lo.values,
        "bb_mid": bb_mid.values,
        "rsi":    rsi_s.values,
        "adx":    adx_s.values,
        "vol_avg":vol_avg.values,
    })

    x_range = Range1d(x[0], x[-1])
    TOOLS   = "pan,box_zoom,wheel_zoom,reset,save"

    # ── Panel 1: OHLCV ────────────────────────────────────────────────────────
    p1 = figure(
        width=1440, height=460,
        x_axis_type="datetime", x_range=x_range,
        tools=TOOLS, title="SOL/USD — Strategy Backtest",
    )
    # Wicks
    p1.segment("x", "high", "x", "low", color="color", source=ohlcv_src, line_width=1)
    # Bodies
    p1.vbar("x", top="top", bottom="bot", width=bar_ms,
            fill_color="color", line_color="color", source=ohlcv_src)
    # EMAs
    p1.line("x", "ema_f", source=ohlcv_src, color=_EMA_F, line_width=1.8,
            legend_label=f"EMA {sig['ema']['fast']}")
    p1.line("x", "ema_s", source=ohlcv_src, color=_EMA_S, line_width=1.8,
            legend_label=f"EMA {sig['ema']['slow']}")
    # Bollinger Bands
    p1.line("x", "bb_hi",  source=ohlcv_src, color=_BB, line_width=1,
            line_dash="dashed", legend_label="BB")
    p1.line("x", "bb_lo",  source=ohlcv_src, color=_BB, line_width=1,
            line_dash="dashed")
    p1.line("x", "bb_mid", source=ohlcv_src, color=_BB, line_width=0.8,
            line_dash="dotted", line_alpha=0.5)
    p1.varea("x", "bb_lo", "bb_hi", source=ohlcv_src,
             fill_color=_BB, fill_alpha=0.06)

    # Buy / sell markers
    if not trades.empty:
        buys = trades
        wins = trades[win_mask]
        loss = trades[loss_mask]

        p1.scatter(
            x=list(buys["EntryTime"]),
            y=list(buys["EntryPrice"] * 0.997),
            marker="triangle", size=13, color=_UP,
            line_color="#1a4731", line_width=1.5,
            legend_label="Entry",
        )
        if not wins.empty:
            p1.scatter(
                x=list(wins["ExitTime"]),
                y=list(wins["ExitPrice"] * 1.003),
                marker="inverted_triangle", size=13, color=_UP,
                line_color="#1a4731", line_width=1.5,
                legend_label="Exit (win)",
            )
        if not loss.empty:
            p1.scatter(
                x=list(loss["ExitTime"]),
                y=list(loss["ExitPrice"] * 1.003),
                marker="inverted_triangle", size=13, color=_DOWN,
                line_color="#6b1a1a", line_width=1.5,
                legend_label="Exit (loss)",
            )

    p1.add_tools(HoverTool(
        tooltips=[
            ("Date",   "@x{%F %H:%M}"),
            ("O/H/L/C","@open{0.2f} / @high{0.2f} / @low{0.2f} / @close{0.2f}"),
            ("Volume", "@volume{0,0}"),
        ],
        formatters={"@x": "datetime"},
        mode="vline",
    ))
    p1.add_tools(CrosshairTool(line_color="#444", line_alpha=0.6))
    _style(p1, x_visible=False)
    p1.legend.location         = "top_left"
    p1.legend.background_fill_color = _BG
    p1.legend.background_fill_alpha = 0.85
    p1.legend.label_text_color = _TEXT
    p1.legend.border_line_color = "#30363d"
    p1.legend.label_text_font_size = "9pt"
    p1.legend.click_policy     = "hide"

    # ── Panel 2: Volume ───────────────────────────────────────────────────────
    p2 = figure(
        width=1440, height=110,
        x_axis_type="datetime", x_range=x_range,
        tools=TOOLS,
    )
    p2.vbar("x", top="volume", width=bar_ms,
            fill_color="vcol", line_color="vcol",
            fill_alpha=0.7, source=ohlcv_src)
    p2.line("x", "vol_avg", source=ohlcv_src,
            color="#ffffff", line_width=1, line_alpha=0.5,
            line_dash="dashed")
    p2.yaxis.axis_label = "Volume"
    _style(p2, x_visible=False)

    # ── Panel 3: RSI ──────────────────────────────────────────────────────────
    p3 = figure(
        width=1440, height=110,
        x_axis_type="datetime", x_range=x_range,
        y_range=Range1d(0, 100), tools=TOOLS,
    )
    p3.add_layout(BoxAnnotation(top=70, bottom=30,
                                fill_color=_RSI, fill_alpha=0.06))
    p3.add_layout(Span(location=70, dimension="width",
                       line_color=_RSI, line_dash="dashed",
                       line_width=1, line_alpha=0.5))
    p3.add_layout(Span(location=30, dimension="width",
                       line_color=_RSI, line_dash="dashed",
                       line_width=1, line_alpha=0.5))
    p3.add_layout(Span(location=50, dimension="width",
                       line_color="#555", line_dash="dotted",
                       line_width=1, line_alpha=0.4))
    p3.line("x", "rsi", source=ohlcv_src, color=_RSI, line_width=1.5)
    p3.yaxis.axis_label = "RSI"
    _style(p3, x_visible=False)

    # ── Panel 4: ADX ──────────────────────────────────────────────────────────
    p4 = figure(
        width=1440, height=110,
        x_axis_type="datetime", x_range=x_range,
        tools=TOOLS,
    )
    threshold = sig["adx"]["threshold"]
    p4.add_layout(Span(location=threshold, dimension="width",
                       line_color=_ADX, line_dash="dashed",
                       line_width=1, line_alpha=0.6))
    p4.add_layout(BoxAnnotation(bottom=threshold,
                                fill_color=_ADX, fill_alpha=0.04))
    p4.line("x", "adx", source=ohlcv_src, color=_ADX, line_width=1.5)
    p4.yaxis.axis_label = "ADX"
    _style(p4, x_visible=False)

    # ── Panel 5: Equity curve ─────────────────────────────────────────────────
    eq_src = ColumnDataSource({
        "x":      equity.index,
        "equity": equity.values,
    })
    p5 = figure(
        width=1440, height=130,
        x_axis_type="datetime", x_range=x_range,
        tools=TOOLS,
    )
    p5.line("x", "equity", source=eq_src, color=_EQ, line_width=2)
    p5.varea("x", y1=float(equity.iloc[0]), y2="equity",
             source=eq_src, fill_color=_EQ, fill_alpha=0.12)
    p5.add_layout(Span(
        location=float(equity.iloc[0]),
        dimension="width",
        line_color="#555", line_dash="dashed",
        line_width=1, line_alpha=0.5,
    ))
    p5.add_tools(HoverTool(
        tooltips=[("Date", "@x{%F}"), ("Equity", "$@equity{0,0.00}")],
        formatters={"@x": "datetime"},
        mode="vline",
    ))
    p5.yaxis.axis_label = "Equity ($)"
    _style(p5, x_visible=True)

    # ── Assemble and save ─────────────────────────────────────────────────────
    layout = column(p1, p2, p3, p4, p5, sizing_mode="stretch_width")
    output_file(str(report_path), title="SOL Backtest")
    save(layout)


# ── Stats display ─────────────────────────────────────────────────────────────

def _fmt(val: object, fmt: str = ".2f", suffix: str = "") -> str:
    if val is None:
        return "n/a"
    try:
        if np.isnan(float(val)):
            return "n/a"
    except (TypeError, ValueError):
        return str(val)
    return f"{val:{fmt}}{suffix}"


def _print_stats(stats: pd.Series) -> None:
    console = Console()
    table = Table(title="Backtest Results", header_style="bold cyan", show_lines=False)
    table.add_column("Metric",  style="dim",   min_width=16)
    table.add_column("Value",   justify="right", min_width=12)
    rows = [
        ("Total Return",  _fmt(stats.get("Return [%]"),       fmt=".2f", suffix=" %")),
        ("Win Rate",      _fmt(stats.get("Win Rate [%]"),      fmt=".1f", suffix=" %")),
        ("Sharpe Ratio",  _fmt(stats.get("Sharpe Ratio"),      fmt=".3f")),
        ("Max Drawdown",  _fmt(stats.get("Max. Drawdown [%]"), fmt=".2f", suffix=" %")),
        ("# Trades",      str(int(stats.get("# Trades", 0)))),
        ("Avg Trade",     _fmt(stats.get("Avg. Trade [%]"),    fmt=".3f", suffix=" %")),
        ("Final Equity",  _fmt(stats.get("Equity Final [$]"),  fmt=",.2f", suffix=" USD")),
        ("Best Trade",    _fmt(stats.get("Best Trade [%]"),    fmt=".2f", suffix=" %")),
        ("Worst Trade",   _fmt(stats.get("Worst Trade [%]"),   fmt=".2f", suffix=" %")),
    ]
    for label, value in rows:
        table.add_row(label, value)
    console.print(table)


# ── Public entry point ────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, config: dict, output_dir: str = "reports") -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    bt_df = df.rename(columns={
        "open": "Open", "high": "High",
        "low":  "Low",  "close": "Close", "volume": "Volume",
    })
    if bt_df.index.tz is not None:
        bt_df.index = bt_df.index.tz_convert("UTC").tz_localize(None)

    commission    = config["portfolio"]["slippage"] + config["portfolio"]["fee"]
    strategy_cls  = _make_strategy(config)

    bt = Backtest(
        bt_df, strategy_cls,
        cash=config["portfolio"]["initial_balance"],
        commission=commission,
        exclusive_orders=True,
    )

    logger.info(f"Running backtest on {len(bt_df):,} candles "
                f"({bt_df.index[0]:%Y-%m-%d} to {bt_df.index[-1]:%Y-%m-%d})…")

    stats = bt.run()
    _print_stats(stats)

    ts          = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = out / f"backtest_{ts}.html"

    # Use the original df (tz-naive, lowercase columns) for chart indicators
    chart_df = df.copy()
    if chart_df.index.tz is not None:
        chart_df.index = chart_df.index.tz_convert("UTC").tz_localize(None)

    logger.info("Rendering HTML chart…")
    _build_html_chart(chart_df, stats, config, report_path)

    logger.success(f"Report saved: {report_path}")
    return str(report_path)
