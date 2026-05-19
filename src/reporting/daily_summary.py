from rich.console import Console
from rich.table import Table

_console = Console()


def print_daily_summary(portfolio: object, fills: list[dict]) -> None:
    """Print a formatted end-of-day (or on-demand) summary table.

    Args:
        portfolio: A Portfolio instance (reads cash, total_value, realized/unrealized PnL).
        fills:     List of fill dicts accumulated during the period.
                   Buys have direction='buy'; closes have direction='sell' and a 'pnl' key.
    """
    closes      = [f for f in fills if f.get("direction") == "sell"]
    opens_today = [f for f in fills if f.get("direction") == "buy"]
    wins        = [f for f in closes if f.get("pnl", 0) > 0]
    losses      = [f for f in closes if f.get("pnl", 0) <= 0]
    day_pnl     = sum(f.get("pnl", 0) for f in closes)
    win_rate    = (len(wins) / len(closes) * 100) if closes else 0.0

    pnl_color       = "green" if day_pnl >= 0 else "red"
    realized_color  = "green" if portfolio.realized_pnl >= 0 else "red"  # type: ignore[attr-defined]
    unrealized_color = "green" if portfolio.unrealized_pnl >= 0 else "red"  # type: ignore[attr-defined]

    table = Table(
        title="Portfolio Summary",
        header_style="bold cyan",
        show_lines=False,
        min_width=42,
    )
    table.add_column("Metric", style="dim", min_width=22)
    table.add_column("Value",  justify="right", min_width=16)

    table.add_row("Portfolio Value",      f"${portfolio.total_value:>12,.2f}")  # type: ignore[attr-defined]
    table.add_row("Cash Balance",         f"${portfolio.cash:>12,.2f}")  # type: ignore[attr-defined]
    table.add_row("Open Positions",       str(len(portfolio.open_positions)))  # type: ignore[attr-defined]
    table.add_row(
        "Realized PnL (all-time)",
        f"[{realized_color}]${portfolio.realized_pnl:>+12,.4f}[/{realized_color}]",  # type: ignore[attr-defined]
    )
    table.add_row(
        "Unrealized PnL",
        f"[{unrealized_color}]${portfolio.unrealized_pnl:>+12,.4f}[/{unrealized_color}]",  # type: ignore[attr-defined]
    )
    table.add_row("", "")  # spacer
    table.add_row("Positions Opened",     str(len(opens_today)))
    table.add_row("Positions Closed",     str(len(closes)))
    table.add_row("  Wins",               str(len(wins)))
    table.add_row("  Losses",             str(len(losses)))
    table.add_row("Win Rate",             f"{win_rate:.1f}%")
    table.add_row(
        "Period PnL",
        f"[{pnl_color}]${day_pnl:>+12,.4f}[/{pnl_color}]",
    )

    _console.print(table)
