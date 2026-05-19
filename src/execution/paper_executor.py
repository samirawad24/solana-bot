import uuid
from datetime import datetime, timezone

from portfolio.state import Portfolio


class PaperExecutor:
    """Simulates market-order fills with configurable slippage and fees.

    BUY  fill_price = market_price × (1 + slippage)   — we pay more
    SELL fill_price = market_price × (1 − slippage)   — we receive less

    Fees are charged on the fill price: fee = fill_price × units × fee_rate

    To switch to live trading: implement the same buy() / sell() interface
    in live_executor.py and swap the import in main.py.
    """

    def __init__(self, config: dict, portfolio: Portfolio) -> None:
        self._slippage  = config["portfolio"]["slippage"]
        self._fee_rate  = config["portfolio"]["fee"]
        self._portfolio = portfolio

    def buy(
        self,
        symbol: str,
        units: float,
        market_price: float,
        stop_loss: float,
        take_profit: float,
        signal: str,
    ) -> dict:
        """Simulate a market buy. Registers the position and returns the fill record."""
        fill_price    = market_price * (1.0 + self._slippage)
        fees          = fill_price * units * self._fee_rate
        slippage_cost = (fill_price - market_price) * units
        total_cost    = fill_price * units + fees

        fill = {
            "position_id":  str(uuid.uuid4()),
            "type":         "open",
            "symbol":       symbol,
            "direction":    "buy",
            "units":        units,
            "market_price": market_price,
            "fill_price":   round(fill_price,    8),
            "stop_loss":    stop_loss,
            "take_profit":  take_profit,
            "signal":       signal,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "fees":         round(fees,          6),
            "slippage_cost":round(slippage_cost, 6),
            "total_cost":   round(total_cost,    6),
        }

        self._portfolio.open_position(fill)   # mutates fill to add trade_id
        return fill

    def sell(
        self,
        symbol: str,
        units: float,
        market_price: float,
        position_id: str,
        signal: str,
        close_reason: str = "closed",
    ) -> dict:
        """Simulate closing a position. Returns the fill record with realised PnL.

        Args:
            close_reason: Label stored in the DB status column.
                          Use 'closed_sl', 'closed_tp', or 'closed_signal'.
        """
        position = self._portfolio.get_position(position_id)
        if position is None:
            raise ValueError(f"No open position with id={position_id!r}")

        fill_price    = market_price * (1.0 - self._slippage)
        fees          = fill_price * units * self._fee_rate
        slippage_cost = (market_price - fill_price) * units

        # PnL = (exit_fill − entry_fill) × units − entry_fees − exit_fees
        pnl = (fill_price - position["fill_price"]) * units - position["fees"] - fees

        fill = {
            "position_id":  position_id,
            "trade_id":     position.get("trade_id"),
            "type":         "close",
            "symbol":       symbol,
            "direction":    "sell",
            "units":        units,
            "market_price": market_price,
            "fill_price":   round(fill_price,    8),
            "signal":       signal,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "fees":         round(fees,          6),
            "slippage_cost":round(slippage_cost, 6),
            "pnl":          round(pnl,           6),
            "close_reason": close_reason,
        }

        self._portfolio.close_position(fill)
        return fill
