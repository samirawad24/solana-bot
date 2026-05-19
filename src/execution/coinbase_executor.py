"""Executor that places real orders against the Coinbase Advanced Trade Sandbox.

Mirrors the PaperExecutor buy() / sell() interface exactly so it can be
swapped in without changing the main trading loop.

Setup
-----
1. Register at https://public.sandbox.coinbase.com
2. Go to Settings → API and create a new API key.
3. Download the JSON key file (recommended) OR copy the key name + secret.
4. In .env set either:
      CB_SANDBOX_KEY_FILE=coinbase_sandbox_key.json   # path to downloaded file
   or:
      CB_SANDBOX_API_KEY=organizations/.../apiKeys/...
      CB_SANDBOX_API_SECRET=-----BEGIN EC PRIVATE KEY-----\\n...
"""
import os
import time
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

_SANDBOX_URL    = "https://api-sandbox.coinbase.com"
_FILL_TIMEOUT   = 15      # seconds to wait for a market order to fill
_POLL_INTERVAL  = 0.5     # seconds between status polls
_MIN_SOL        = 0.001   # Coinbase minimum order size for SOL


class CoinbaseSandboxExecutor:
    """Execute orders on the Coinbase Advanced Trade Sandbox.

    Uses real order placement so fill prices come from the exchange.
    Stop-loss / take-profit are still enforced in software by the main loop,
    not as exchange-native bracket orders.
    """

    def __init__(self, config: dict, portfolio: object) -> None:
        from coinbase.rest import RESTClient

        key_file   = os.getenv("CB_SANDBOX_KEY_FILE")
        api_key    = os.getenv("CB_SANDBOX_API_KEY")
        api_secret = os.getenv("CB_SANDBOX_API_SECRET")

        if key_file:
            self._client = RESTClient(key_file=key_file, base_url=_SANDBOX_URL)
            logger.info(f"Coinbase sandbox: authenticating via key file {key_file!r}")
        elif api_key and api_secret:
            # .env may store newlines as literal \n — restore them
            secret = api_secret.replace("\\n", "\n")
            self._client = RESTClient(
                api_key=api_key,
                api_secret=secret,
                base_url=_SANDBOX_URL,
            )
            logger.info("Coinbase sandbox: authenticating via CB_SANDBOX_API_KEY")
        else:
            raise RuntimeError(
                "Coinbase sandbox credentials not found. "
                "Set CB_SANDBOX_KEY_FILE or "
                "CB_SANDBOX_API_KEY + CB_SANDBOX_API_SECRET in .env"
            )

        self._portfolio = portfolio
        self._product   = config["trading"]["symbol"].replace("/", "-")  # SOL-USD
        self._fee_rate  = config["portfolio"]["fee"]

        self._log_sandbox_balance()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _log_sandbox_balance(self) -> None:
        """Log the sandbox USD and SOL balances at startup for reference."""
        try:
            resp = self._client.get_accounts()
            for acct in resp.get("accounts", []):
                ccy = acct.get("currency", "")
                if ccy in ("USD", "SOL"):
                    val = acct.get("available_balance", {}).get("value", "?")
                    logger.info(f"Sandbox {ccy} balance: {val}")
        except Exception as exc:
            logger.warning(f"Could not fetch sandbox balances: {exc}")

    def _wait_for_fill(self, order_id: str) -> dict:
        """Poll until the order reaches a terminal state; return the order dict."""
        deadline = time.monotonic() + _FILL_TIMEOUT
        while time.monotonic() < deadline:
            resp   = self._client.get_order(order_id)
            order  = resp.get("order", {})
            status = order.get("status", "")
            if status in ("FILLED", "CANCELLED", "FAILED", "EXPIRED"):
                if status != "FILLED":
                    raise RuntimeError(
                        f"Order {order_id} ended with status={status!r} — "
                        f"reason: {order.get('reject_message') or order.get('cancel_message')}"
                    )
                return order
            time.sleep(_POLL_INTERVAL)
        raise TimeoutError(
            f"Order {order_id} did not fill within {_FILL_TIMEOUT}s"
        )

    def _extract_fill(self, order: dict, fallback_price: float, fallback_units: float) -> tuple:
        """Return (fill_price, filled_qty, fees) from a filled order dict."""
        fill_price = float(order.get("average_filled_price") or fallback_price)
        filled_qty = float(order.get("filled_size")          or fallback_units)
        fees       = float(order.get("total_fees")           or 0.0)
        if fees == 0.0:
            fees = fill_price * filled_qty * self._fee_rate
        return fill_price, filled_qty, fees

    # ── Public interface (matches PaperExecutor) ──────────────────────────────

    def buy(
        self,
        symbol: str,
        units: float,
        market_price: float,
        stop_loss: float,
        take_profit: float,
        signal: str,
    ) -> dict:
        """Place a market buy order and return a fill dict."""
        units = max(units, _MIN_SOL)
        client_order_id = str(uuid.uuid4())

        resp = self._client.market_order_buy(
            client_order_id=client_order_id,
            product_id=self._product,
            base_size=f"{units:.6f}",
        )

        if not resp.get("success"):
            msg = resp.get("error_response", {}).get("message", "unknown error")
            raise RuntimeError(f"Coinbase BUY rejected: {msg}")

        order_id  = resp["success_response"]["order_id"]
        order     = self._wait_for_fill(order_id)
        fp, qty, fees = self._extract_fill(order, market_price, units)

        fill = {
            "position_id":  client_order_id,
            "type":         "open",
            "symbol":       symbol,
            "direction":    "buy",
            "units":        qty,
            "market_price": market_price,
            "fill_price":   round(fp,    8),
            "stop_loss":    stop_loss,
            "take_profit":  take_profit,
            "signal":       signal,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "fees":         round(fees,  6),
            "slippage_cost":round(fp - market_price, 6) * qty,
            "total_cost":   round(fp * qty + fees,   6),
            "order_id":     order_id,
        }
        self._portfolio.open_position(fill)
        logger.debug(f"Sandbox BUY filled: {qty:.4f} {self._product} @ {fp:.4f}")
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
        """Place a market sell order and return a fill dict with realised PnL."""
        position = self._portfolio.get_position(position_id)
        if position is None:
            raise ValueError(f"No open position with id={position_id!r}")

        units = max(units, _MIN_SOL)
        client_order_id = str(uuid.uuid4())

        resp = self._client.market_order_sell(
            client_order_id=client_order_id,
            product_id=self._product,
            base_size=f"{units:.6f}",
        )

        if not resp.get("success"):
            msg = resp.get("error_response", {}).get("message", "unknown error")
            raise RuntimeError(f"Coinbase SELL rejected: {msg}")

        order_id  = resp["success_response"]["order_id"]
        order     = self._wait_for_fill(order_id)
        fp, qty, fees = self._extract_fill(order, market_price, units)

        pnl = (fp - position["fill_price"]) * qty - position["fees"] - fees

        fill = {
            "position_id":  position_id,
            "trade_id":     position.get("trade_id"),
            "type":         "close",
            "symbol":       symbol,
            "direction":    "sell",
            "units":        qty,
            "market_price": market_price,
            "fill_price":   round(fp,   8),
            "signal":       signal,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "fees":         round(fees, 6),
            "slippage_cost":round(market_price - fp, 6) * qty,
            "pnl":          round(pnl,  6),
            "close_reason": close_reason,
            "order_id":     order_id,
        }
        self._portfolio.close_position(fill)
        logger.debug(f"Sandbox SELL filled: {qty:.4f} {self._product} @ {fp:.4f}  pnl={pnl:+.4f}")
        return fill
