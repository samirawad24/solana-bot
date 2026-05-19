import argparse
import sys
from datetime import date

sys.path.insert(0, "src")


# ── Paper trading loop ────────────────────────────────────────────────────────

def _run_paper_loop(config: dict, executor_cls=None) -> None:
    """Block until Ctrl-C or the daily loss limit is hit.

    executor_cls: optional executor class to use instead of PaperExecutor.
                  Must implement the same buy() / sell() interface.
    """
    from loguru import logger

    from src.data.price_feed import get_latest_candles, wait_for_next_candle
    from src.execution.paper_executor import PaperExecutor
    from src.portfolio.db import PortfolioDB
    from src.portfolio.state import Portfolio
    from src.reporting.daily_summary import print_daily_summary
    from src.reporting.logger import log_candle, log_fill, log_halt, setup_logger
    from src.risk.daily_limit import DailyLimitBreached, DailyLimitGuard
    from src.risk.position_sizer import calculate_position_size
    from src.risk.stops import calculate_stops
    from src.strategy.combiner import evaluate_signals_detail

    setup_logger()

    sym      = config["trading"]["symbol"]
    tf       = config["trading"]["timeframe"]
    exchange = config["trading"]["exchange"]
    max_pos  = config["portfolio"]["max_open_positions"]

    # ── Portfolio (resumes from portfolio.db if it exists) ────────────────────
    db        = PortfolioDB("portfolio.db")
    portfolio = Portfolio(config["portfolio"]["initial_balance"], db)
    _Executor = executor_cls or PaperExecutor
    executor  = _Executor(config, portfolio)
    guard     = DailyLimitGuard(
        opening_value=portfolio.total_value,
        limit_pct=config["portfolio"]["daily_loss_limit"],
    )

    logger.info(
        f"Paper loop started | {sym} {tf} | "
        f"portfolio=${portfolio.total_value:,.2f} | "
        f"open positions: {len(portfolio.open_positions)}"
    )

    today_fills: list[dict] = []
    last_date:   date | None = None

    try:
        while True:
            # ── Wait for the current candle to close ──────────────────────────
            wait_for_next_candle(tf)

            # ── Fetch latest closed candles ───────────────────────────────────
            try:
                df = get_latest_candles(sym, tf, limit=100, exchange_id=exchange)
            except Exception as exc:
                logger.warning(f"Candle fetch failed: {exc} — skipping bar")
                continue

            if df.empty:
                logger.warning("Empty candle response — skipping bar")
                continue

            latest_ts    = df.index[-1]
            latest_close = float(df["close"].iloc[-1])
            candle_high  = float(df["high"].iloc[-1])
            candle_low   = float(df["low"].iloc[-1])
            current_date = latest_ts.date()

            # ── Daily reset (midnight UTC) ────────────────────────────────────
            if last_date is not None and current_date != last_date:
                logger.info("New trading day — printing daily summary")
                print_daily_summary(portfolio, today_fills)
                guard.reset(portfolio.total_value)
                today_fills = []
            last_date = current_date

            # ── Refresh unrealised PnL ────────────────────────────────────────
            portfolio.update_prices(latest_close)

            # ── Daily loss limit ──────────────────────────────────────────────
            try:
                guard.check(portfolio.total_value)
            except DailyLimitBreached as exc:
                log_halt(str(exc))
                print_daily_summary(portfolio, today_fills)
                break

            # ── SL / TP check on every open position ──────────────────────────
            # SL takes priority when both are touched in the same candle.
            for pos_id, pos in list(portfolio.open_positions.items()):
                sl = pos["stop_loss"]
                tp = pos["take_profit"]
                close_price  = None
                close_reason = None

                if candle_low <= sl:
                    close_price, close_reason = sl, "closed_sl"
                elif candle_high >= tp:
                    close_price, close_reason = tp, "closed_tp"

                if close_price is not None:
                    fill = executor.sell(
                        symbol=sym,
                        units=pos["units"],
                        market_price=close_price,
                        position_id=pos_id,
                        signal="sl_tp",
                        close_reason=close_reason,
                    )
                    log_fill(fill)
                    today_fills.append(fill)

            # ── Evaluate confluence signals ───────────────────────────────────
            detail    = evaluate_signals_detail(df, config)
            direction = detail["direction"]
            log_candle(latest_ts, latest_close, direction, detail=detail)

            # ── Open a new position on buy signal ─────────────────────────────
            if direction == "buy" and portfolio.can_open_position(max_pos):
                try:
                    sl, tp = calculate_stops(
                        df,
                        entry_price=latest_close,
                        direction="buy",
                        atr_period=config["stops"]["atr_period"],
                        sl_atr=config["stops"]["stop_loss_atr"],
                        tp_atr=config["stops"]["take_profit_atr"],
                    )
                    units = calculate_position_size(
                        portfolio_value=portfolio.total_value,
                        entry_price=latest_close,
                        stop_price=sl,
                        risk_pct=config["portfolio"]["risk_per_trade"],
                        available_cash=portfolio.cash,
                    )
                    if units > 0:
                        triggered  = [k for k, v in detail["signals"].items() if v == "buy"]
                        fill = executor.buy(
                            symbol=sym,
                            units=units,
                            market_price=latest_close,
                            stop_loss=sl,
                            take_profit=tp,
                            signal=",".join(triggered),
                        )
                        log_fill(fill)
                        today_fills.append(fill)
                except ValueError as exc:
                    logger.warning(f"Could not size position: {exc}")

            # ── Close all open positions on sell signal ────────────────────────
            elif direction == "sell" and portfolio.open_positions:
                triggered = [k for k, v in detail["signals"].items() if v == "sell"]
                for pos_id, pos in list(portfolio.open_positions.items()):
                    fill = executor.sell(
                        symbol=sym,
                        units=pos["units"],
                        market_price=latest_close,
                        position_id=pos_id,
                        signal=",".join(triggered),
                        close_reason="closed_signal",
                    )
                    log_fill(fill)
                    today_fills.append(fill)

    except KeyboardInterrupt:
        logger.info("Interrupt received — shutting down gracefully")
    finally:
        print_daily_summary(portfolio, today_fills)
        db.close()
        logger.info("Shutdown complete")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Solana Paper Trading Bot")
    parser.add_argument(
        "--mode", choices=["paper", "sandbox", "backtest"], required=True,
        help=(
            "'paper'   — local simulation (no exchange account needed); "
            "'sandbox' — real orders on Coinbase sandbox (requires .env API keys); "
            "'backtest'— run strategy against historical data"
        ),
    )
    parser.add_argument(
        "--months", type=int, default=0,
        help="Backtest lookback in months (default: value from config.yaml)",
    )
    args = parser.parse_args()

    from src.config import load_config
    config = load_config()

    if args.mode == "backtest":
        from src.data.historical import fetch_historical_candles
        from src.reporting.backtest_report import run_backtest

        months = args.months or config["backtest"]["months"]
        df = fetch_historical_candles(
            symbol=config["trading"]["symbol"],
            timeframe=config["trading"]["timeframe"],
            months=months,
            exchange_id=config["trading"]["exchange"],
        )
        run_backtest(df, config, output_dir=config["backtest"]["report_dir"])

    elif args.mode == "paper":
        _run_paper_loop(config)

    elif args.mode == "sandbox":
        from src.execution.coinbase_executor import CoinbaseSandboxExecutor
        _run_paper_loop(config, executor_cls=CoinbaseSandboxExecutor)


if __name__ == "__main__":
    main()
