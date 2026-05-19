from datetime import datetime, timezone

from portfolio.db import PortfolioDB


class Portfolio:
    """Tracks cash balance, open positions, realised PnL, and unrealised PnL.

    Initialises from the latest DB snapshot (resumable across restarts).
    Falls back to initial_balance when no snapshot exists.
    """

    def __init__(self, initial_balance: float, db: PortfolioDB) -> None:
        self._db               = db
        self._initial_balance  = initial_balance

        snapshot = db.load_latest_snapshot()
        if snapshot:
            self._cash             = snapshot["cash"]
            self._realized_pnl     = snapshot["realized_pnl"]
            self._unrealized_pnl   = snapshot["unrealized_pnl"]
            # Rebuild position dict keyed by position_id
            self._open_positions: dict[str, dict] = {
                p["position_id"]: p for p in snapshot["open_positions"]
            }
            # Ensure current_price exists for every loaded position
            for pos in self._open_positions.values():
                pos.setdefault("current_price", pos["fill_price"])
        else:
            self._cash             = initial_balance
            self._realized_pnl     = 0.0
            self._unrealized_pnl   = 0.0
            self._open_positions   = {}

    # ── Read-only properties ─────────────────────────────────────────────────

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def unrealized_pnl(self) -> float:
        return self._unrealized_pnl

    @property
    def open_positions(self) -> dict[str, dict]:
        return dict(self._open_positions)

    @property
    def total_value(self) -> float:
        """Cash + market value of all open positions at their last known price."""
        positions_value = sum(
            pos["units"] * pos.get("current_price", pos["fill_price"])
            for pos in self._open_positions.values()
        )
        return self._cash + positions_value

    # ── Mutations ────────────────────────────────────────────────────────────

    def get_position(self, position_id: str) -> dict | None:
        return self._open_positions.get(position_id)

    def open_position(self, fill: dict) -> None:
        """Deduct cost from cash, record position, persist to DB.

        Mutates `fill` in-place to add the DB-assigned `trade_id`.
        """
        self._cash -= fill["total_cost"]

        trade_id = self._db.log_trade(fill)
        fill["trade_id"] = trade_id

        pos = dict(fill)
        pos["current_price"] = fill["fill_price"]
        self._open_positions[fill["position_id"]] = pos

        self._save_snapshot()

    def close_position(self, fill: dict) -> None:
        """Add sale proceeds to cash, realise PnL, remove position, update DB."""
        position = self._open_positions.pop(fill["position_id"])

        # Proceeds = what we receive from the sale (after fees already deducted by executor)
        proceeds = fill["fill_price"] * fill["units"] - fill["fees"]
        self._cash      += proceeds
        self._realized_pnl += fill["pnl"]

        self._db.update_trade(
            trade_id=position["trade_id"],
            exit_price=fill["fill_price"],
            pnl=fill["pnl"],
            status=fill.get("close_reason", "closed"),
        )

        self._recalc_unrealized()
        self._save_snapshot()

    def update_prices(self, current_price: float) -> None:
        """Refresh unrealised PnL for all open positions at current_price."""
        for pos in self._open_positions.values():
            pos["current_price"] = current_price
        self._recalc_unrealized()
        self._save_snapshot()

    def can_open_position(self, max_positions: int) -> bool:
        return len(self._open_positions) < max_positions

    # ── Private helpers ──────────────────────────────────────────────────────

    def _recalc_unrealized(self) -> None:
        self._unrealized_pnl = sum(
            (pos["current_price"] - pos["fill_price"]) * pos["units"] - pos["fees"]
            for pos in self._open_positions.values()
        )

    def _save_snapshot(self) -> None:
        self._db.save_snapshot({
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "cash":           self._cash,
            "open_positions": list(self._open_positions.values()),
            "realized_pnl":   self._realized_pnl,
            "unrealized_pnl": self._unrealized_pnl,
        })
