# Solana Paper Trading Bot

An autonomous paper trading bot for SOL/USDT built in Python. Simulates real trades against live price data using a multi-signal confluence strategy. Designed so the execution layer can be swapped to live Jupiter/Raydium trading by replacing one module.

---

## Setup

### 1. Prerequisites

- Python 3.11+
- `pip` or a virtual environment manager

### 2. Install dependencies

```bash
cd solana-bot
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if you want to override defaults
```

### 4. Review `config.yaml`

All strategy parameters, risk limits, and signal toggles live in `config.yaml`. You do not need to touch `.env` for most tuning — `config.yaml` is the primary knob.

---

## Running the bot

### Paper trading (live loop)

```bash
python main.py --mode paper
```

The bot polls live 15-minute candles from Binance (no API key required), evaluates signals on each new candle close, and simulates fills. State is persisted to `portfolio.db` so you can stop and restart freely.

### Backtesting

```bash
python main.py --mode backtest --months 12
```

Fetches 12 months of historical SOL/USDT candles and runs the full strategy against them. Outputs an HTML report to `reports/backtest_<timestamp>.html` with:
- Equity curve chart
- Total return, win rate, Sharpe ratio, max drawdown, trade count

You can change the lookback with `--months N`.

---

## Tuning the config

| Key | What it controls |
|-----|-----------------|
| `trading.timeframe` | Candle interval — try `5m`, `15m`, `1h` |
| `strategy.min_signals` | How many signals must agree to enter (1–4) |
| `signals.<name>.enabled` | Toggle individual signals on/off |
| `portfolio.risk_per_trade` | Fraction of portfolio risked per trade (e.g. `0.01` = 1%) |
| `portfolio.daily_loss_limit` | Halt threshold (e.g. `0.05` = 5%) |
| `stops.stop_loss_atr` | ATR multiplier for stop loss |
| `stops.take_profit_atr` | ATR multiplier for take profit |

After changing config, re-run backtest to see the impact before running paper mode.

---

## Reading the reports

**Console output** — each candle evaluation prints a status line. Trade fills show entry price, signal triggers, position size, SL/TP levels, and fees paid.

**Daily summary** — printed at midnight (UTC) and on clean shutdown. Shows: starting balance, ending balance, realized PnL, number of trades, win rate for the day.

**Backtest HTML report** — open the file in any browser. The equity curve shows portfolio value over time. The stats table at the top summarizes key metrics. Individual trade markers are plotted on the price chart.

---

## Project structure

```
solana-bot/
├── config.yaml          # all tunable parameters
├── .env                 # secrets / overrides (not committed)
├── main.py              # entry point (--mode paper | backtest)
├── src/
│   ├── data/            # price feed + historical loader
│   ├── strategy/        # one file per signal + confluence combiner
│   ├── risk/            # position sizing, ATR stops, daily limits
│   ├── execution/       # paper_executor.py (swap this for live)
│   ├── portfolio/       # in-memory state + SQLite persistence
│   └── reporting/       # rich logs, daily summary, HTML report
└── tests/               # pytest unit tests
```

---

## How to switch to live trading

This section documents exactly what would need to change to go live. **No live-trading code exists in this repo.**

1. **Create `src/execution/live_executor.py`** implementing the same `BaseExecutor` interface as `paper_executor.py`. Inside, call Jupiter or Raydium swap APIs using your wallet's private key.

2. **Add secrets to `.env`**:
   - `SOLANA_PRIVATE_KEY` — your wallet private key (never commit this)
   - `RPC_URL` — a Solana RPC endpoint (e.g. Helius, QuickNode)

3. **Swap the executor in `main.py`**: change the import from `PaperExecutor` to `LiveExecutor`. The rest of the pipeline (signals, risk, portfolio tracking) is unchanged.

4. **Adjust fees/slippage in `config.yaml`** to match real Jupiter routing fees (currently estimated at 0.25%).

5. **Test on devnet first** — Jupiter and Raydium both support Solana devnet. Run against devnet with a throwaway wallet before mainnet.

6. **Harden the daily loss limit** — the paper engine halts by stopping the loop; a live engine must also cancel any open limit orders via the Solana program.

> The paper bot deliberately has no private key handling, no wallet imports, and no on-chain transaction code.

---

## Running tests

```bash
pytest tests/ -v
```

Tests cover: RSI signal, EMA signal, Bollinger signal, ADX filter, strategy combiner, position sizer, ATR stops, and daily loss limit logic.
