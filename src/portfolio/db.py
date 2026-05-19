import json
import sqlite3


class PortfolioDB:
    """Persists the trade log and portfolio snapshots to a local SQLite database.

    Schema
    ------
    trades:    one row per opened position; updated in-place on close.
    snapshots: append-only point-in-time state; last row is current state.
    """

    _DDL = """
    CREATE TABLE IF NOT EXISTS trades (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp     TEXT    NOT NULL,
        symbol        TEXT    NOT NULL,
        direction     TEXT    NOT NULL,
        units         REAL    NOT NULL,
        entry_price   REAL    NOT NULL,
        fill_price    REAL    NOT NULL,
        exit_price    REAL,
        stop_loss     REAL    NOT NULL,
        take_profit   REAL    NOT NULL,
        signal        TEXT    NOT NULL,
        slippage_cost REAL    NOT NULL,
        fees          REAL    NOT NULL,
        pnl           REAL,
        status        TEXT    NOT NULL DEFAULT 'open'
    );

    CREATE TABLE IF NOT EXISTS snapshots (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp           TEXT    NOT NULL,
        cash                REAL    NOT NULL,
        open_positions_json TEXT    NOT NULL,
        realized_pnl        REAL    NOT NULL,
        unrealized_pnl      REAL    NOT NULL
    );
    """

    def __init__(self, db_path: str = "portfolio.db") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self._DDL)
        self._conn.commit()

    def log_trade(self, trade: dict) -> int:
        """Insert an open trade record and return its auto-assigned row id."""
        cur = self._conn.execute(
            """INSERT INTO trades
               (timestamp, symbol, direction, units, entry_price, fill_price,
                stop_loss, take_profit, signal, slippage_cost, fees, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
            (
                trade["timestamp"],
                trade["symbol"],
                trade["direction"],
                trade["units"],
                trade["market_price"],
                trade["fill_price"],
                trade["stop_loss"],
                trade["take_profit"],
                trade["signal"],
                trade["slippage_cost"],
                trade["fees"],
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_trade(
        self, trade_id: int, exit_price: float, pnl: float, status: str
    ) -> None:
        """Record exit price, realised PnL, and final status for a closed trade."""
        self._conn.execute(
            "UPDATE trades SET exit_price=?, pnl=?, status=? WHERE id=?",
            (exit_price, pnl, status, trade_id),
        )
        self._conn.commit()

    def save_snapshot(self, snapshot: dict) -> None:
        """Append a portfolio state snapshot (timestamp, cash, positions, PnL)."""
        self._conn.execute(
            """INSERT INTO snapshots
               (timestamp, cash, open_positions_json, realized_pnl, unrealized_pnl)
               VALUES (?, ?, ?, ?, ?)""",
            (
                snapshot["timestamp"],
                snapshot["cash"],
                json.dumps(snapshot["open_positions"]),
                snapshot["realized_pnl"],
                snapshot["unrealized_pnl"],
            ),
        )
        self._conn.commit()

    def load_latest_snapshot(self) -> dict | None:
        """Return the most recent snapshot, or None if the database is empty."""
        row = self._conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return {
            "timestamp":      row["timestamp"],
            "cash":           row["cash"],
            "open_positions": json.loads(row["open_positions_json"]),
            "realized_pnl":   row["realized_pnl"],
            "unrealized_pnl": row["unrealized_pnl"],
        }

    def all_trades(self) -> list[dict]:
        """Return every trade row as a list of dicts (used by reporting)."""
        rows = self._conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
