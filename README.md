# SOL BOT — Solana Paper Trading Bot

Automated SOL/USD paper trading bot running on 15-minute candles. Combines four technical signals with a confluence filter, manages risk with ATR-based stop-loss and take-profit levels, and persists all trades to a local SQLite database. Comes with a live web dashboard and a full backtesting engine with an interactive HTML chart.

## How it works

1. **Wait** — sleeps until the current 15-minute candle closes
2. **Fetch** — pulls the latest 100 candles from Coinbase via ccxt
3. **Signal** — evaluates RSI, EMA crossover, Bollinger Band breakout, and ADX filter; requires at least 2 agreeing signals to enter
4. **Size** — calculates position size using 2% fixed-risk per trade, capped at available cash
5. **Execute** — opens a long position with ATR-derived SL/TP levels; closes on signal reversal, SL hit, or TP hit
6. **Guard** — halts all trading for the day if the portfolio drops more than 5%

Starts automatically on Windows login via a Startup folder shortcut.

## Setup

**1. Clone and install dependencies**
```
git clone https://github.com/samirawad24/solana-bot.git
cd solana-bot
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

**2. Configure**
```
copy .env.example .env
```
No API keys are needed for paper mode — live prices are fetched from Coinbase's public feed.

**3. Run**
```
start.bat
```
Opens the paper trader in its own console window and launches the dashboard at `http://localhost:8081` automatically.

**Or run individually**
```
python main.py --mode paper          # paper trading loop
python main.py --mode backtest       # backtest on 12 months of history
python main.py --mode backtest --months 6   # custom lookback
python dashboard.py                  # dashboard only
```

## Dashboard

```
python dashboard.py
```

Opens `http://localhost:8081` automatically with:

- **Header** — live equity, cash, unrealized and realized P&L
- **Stats row** — total P&L, win rate, trade count, avg P&L/trade, open positions
- **Equity curve** — Chart.js line chart built from portfolio snapshots
- **SOL/USD candlestick** — 200-bar Lightweight Charts chart with buy markers (▲ green = win, ▲ yellow = open, ▲ red = loss)
- **Trade history** — every trade with entry, exit, P&L, signal, and status

Auto-refreshes every 60 seconds.

## Configuration

All parameters are in `config.yaml`.

| Setting | Default | Description |
|---|---|---|
| `trading.symbol` | `SOL/USD` | CCXT market symbol |
| `trading.timeframe` | `15m` | Candle interval |
| `trading.exchange` | `coinbase` | CCXT exchange ID |
| `portfolio.initial_balance` | `10000` | Starting USD balance |
| `portfolio.risk_per_trade` | `0.02` | Fraction of portfolio risked per trade |
| `portfolio.max_open_positions` | `3` | Maximum concurrent positions |
| `portfolio.daily_loss_limit` | `0.05` | Portfolio drawdown that triggers a trading halt |
| `portfolio.slippage` | `0.003` | Simulated slippage per fill (0.3%) |
| `portfolio.fee` | `0.0025` | Simulated fee per trade (0.25%) |
| `stops.stop_loss_atr` | `2.0` | Stop loss distance in ATR multiples |
| `stops.take_profit_atr` | `3.0` | Take profit distance in ATR multiples |
| `strategy.min_signals` | `2` | Minimum agreeing signals required to enter |

## Signals

| Signal | Buy condition | Sell condition |
|---|---|---|
| RSI (14) | RSI < 30 (oversold) | RSI > 70 (overbought) |
| EMA crossover (9/21) | Fast EMA crosses above slow EMA | Fast EMA crosses below slow EMA |
| Bollinger breakout (20, 2σ) | Close below lower band + volume spike | Close above upper band + volume spike |
| ADX filter (14) | ADX > 25 (trending market required) | ADX > 25 (trending market required) |

At least `min_signals` indicators must agree before a position opens. The ADX filter acts as a gate — if ADX ≤ 25 no trade fires regardless of other signals.

## Backtesting

```
python main.py --mode backtest
python main.py --mode backtest --months 6
```

Generates an interactive HTML report in `reports/` with a dark-theme Bokeh chart: OHLCV candlesticks, volume, RSI, ADX, equity curve, and buy/sell markers coloured by outcome.

## Coinbase sandbox (optional)

To route orders through the real Coinbase Advanced Trade sandbox instead of the local paper simulator:

```
# fill in CB_SANDBOX_KEY_FILE or CB_SANDBOX_API_KEY + CB_SANDBOX_API_SECRET in .env
python main.py --mode sandbox
```

Sandbox keys can be created at [portal.cdp.coinbase.com](https://portal.cdp.coinbase.com) — no real money is used.

## Running tests

```
.venv\Scripts\pytest tests/ -v
```

21 tests across 8 modules: RSI signal, EMA signal, Bollinger signal, ADX filter, strategy combiner, position sizer, ATR stops, and daily loss limit.

## Project structure

```
solana-bot/
├── main.py                  # CLI entry point (paper / sandbox / backtest)
├── dashboard.py             # Live web dashboard (port 8081)
├── start.bat                # Launcher: starts bot + dashboard together
├── config.yaml              # All tunable parameters
├── requirements.txt
├── .env.example
└── src/
    ├── config.py
    ├── data/
    │   ├── price_feed.py    # Live candle fetching + candle-close waiter
    │   └── historical.py    # Historical OHLCV download for backtesting
    ├── strategy/
    │   ├── rsi_signal.py
    │   ├── ema_signal.py
    │   ├── bollinger_signal.py
    │   ├── adx_filter.py
    │   └── combiner.py      # Confluence logic
    ├── risk/
    │   ├── position_sizer.py
    │   ├── stops.py         # ATR-based SL/TP calculator
    │   └── daily_limit.py   # Daily drawdown guard
    ├── execution/
    │   ├── paper_executor.py       # Local paper fills with slippage + fees
    │   └── coinbase_executor.py    # Coinbase Advanced Trade sandbox executor
    ├── portfolio/
    │   ├── state.py         # In-memory portfolio (cash, positions, P&L)
    │   └── db.py            # SQLite persistence (trades + snapshots tables)
    └── reporting/
        ├── logger.py        # Structured candle + fill logging
        ├── daily_summary.py
        └── backtest_report.py  # Bokeh HTML chart generator
```
