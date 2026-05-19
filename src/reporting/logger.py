import sys

from loguru import logger
from rich.console import Console
from rich.panel import Panel

_console = Console(stderr=True)

_LEVEL_COLORS = {
    "DEBUG":    "dim",
    "INFO":     "white",
    "SUCCESS":  "green",
    "WARNING":  "yellow",
    "ERROR":    "bold red",
    "CRITICAL": "bold red on white",
}

_SIGNAL_COLORS = {
    "buy":     "bold green",
    "sell":    "bold red",
    "neutral": "dim",
}


def _rich_sink(message: object) -> None:
    """Route loguru records through Rich so all output shares one console."""
    rec   = message.record  # type: ignore[attr-defined]
    level = rec["level"].name
    color = _LEVEL_COLORS.get(level, "white")
    ts    = rec["time"].strftime("%H:%M:%S")
    _console.print(
        f"[dim]{ts}[/dim] [{color}]{level:<8}[/{color}] {rec['message']}",
        highlight=False,
    )


def setup_logger(log_level: str = "INFO") -> None:
    """Configure loguru to route through Rich. Call once at startup."""
    logger.remove()
    logger.add(_rich_sink, level=log_level, format="{message}", colorize=False)


def log_candle(
    timestamp: object,
    price: float,
    signal: str,
    detail: dict | None = None,
) -> None:
    """Log a single candle close with signal direction and optional breakdown."""
    color   = _SIGNAL_COLORS.get(signal, "white")
    ts_str  = str(timestamp)[:16]

    extra = ""
    if detail:
        adx_val    = detail.get("adx_value")
        adx_passed = detail.get("adx_passed", True)
        if adx_val is not None:
            gate = "open" if adx_passed else "blocked"
            extra += f"  ADX={adx_val:.1f}({gate})"
        sigs = detail.get("signals", {})
        if sigs:
            parts = [f"{k}:{v}" for k, v in sigs.items() if v != "neutral"]
            if parts:
                extra += "  sigs=[" + ",".join(parts) + "]"

    _console.print(
        f"[dim]{ts_str}[/dim]  {price:.4f}"
        f"  [{color}]{signal}[/{color}]{extra}",
        highlight=False,
    )


def log_fill(fill: dict) -> None:
    """Log a buy or sell fill with price, fees, and PnL."""
    direction = fill.get("direction", "?")
    symbol    = fill.get("symbol", "?")
    units     = fill.get("units", 0)
    fp        = fill.get("fill_price", 0)
    fees      = fill.get("fees", 0)
    sig       = fill.get("signal", "?")

    if direction == "buy":
        sl = fill.get("stop_loss", 0)
        tp = fill.get("take_profit", 0)
        msg = (
            f"[bold green]BUY [/bold green]{symbol}  "
            f"{units:.4f} @ {fp:.4f}  "
            f"SL={sl:.4f}  TP={tp:.4f}  "
            f"fees={fees:.4f}  signal={sig}"
        )
    else:
        pnl    = fill.get("pnl", 0.0)
        reason = fill.get("close_reason", "?")
        pnl_color = "green" if pnl >= 0 else "red"
        msg = (
            f"[bold red]SELL[/bold red] {symbol}  "
            f"{units:.4f} @ {fp:.4f}  "
            f"fees={fees:.4f}  "
            f"pnl=[{pnl_color}]{pnl:+.4f}[/{pnl_color}]  "
            f"reason={reason}"
        )

    _console.print(msg, highlight=False)


def log_halt(reason: str) -> None:
    """Display a prominent halt banner and log it as a warning."""
    _console.print(
        Panel(
            f"[bold red]{reason}[/bold red]",
            title="[bold red]TRADING HALTED[/bold red]",
            border_style="red",
        )
    )
    logger.warning(f"HALTED: {reason}")
