# scalping-bot

BTC perpetual scalping bot on Bybit. Risk-first architecture,
5s–10min timeframe. Python 3.12 + pybit + uv.

> Status: **Phase 1** — risk framework + live market-data collector
> + historical data downloader. No trading logic yet.

## Quick start

```bash
# From /home/user/SHA-256/scalping-bot

# 1. Install Python 3.12 and sync deps (uv does both)
uv sync --dev

# 2. Run tests
uv run pytest -v

# 3. Lint and type-check
uv run ruff check src tests
uv run mypy src

# 4. Copy env template
cp .env.example .env
# Edit .env if needed (not required for Phase 0)
```

## Architecture

Independent layers, each with its own tests:

```
scalping_bot/
├── risk/          # Hardcoded limits, kill switch, P&L accounting
├── market_data/   # WebSocket ingest, orderbook reconstruction, Parquet recorder
├── config/        # Runtime settings via pydantic-settings
├── utils/         # Structured logging (structlog JSON)
├── cli.py         # CLI dispatcher
└── __main__.py    # `python -m scalping_bot`
```

## Running the live data collector

```bash
# Mainnet public streams (no credentials needed)
uv run python -m scalping_bot collect --duration 3600

# Custom symbol and depth
uv run python -m scalping_bot collect --symbol BTCUSDT --depth 50

# Testnet (lower activity; not representative of real microstructure)
uv run python -m scalping_bot collect --testnet
```

### Running in the background on your PC

**Linux / macOS** — one-liner with `nohup`:

```bash
mkdir -p logs
nohup uv run python -m scalping_bot collect \
  > logs/collector_$(date +%Y%m%d_%H%M%S).jsonl 2>&1 &
echo $! > logs/collector.pid
```

To stop: `kill $(cat logs/collector.pid)`.

More robust: use `tmux` (survives SSH disconnects):

```bash
tmux new -d -s collector "uv run python -m scalping_bot collect"
tmux attach -t collector   # to watch
# Ctrl-b d to detach, leaves it running
```

**Windows** — PowerShell:

```powershell
Start-Process -WindowStyle Hidden -FilePath "uv" `
  -ArgumentList "run","python","-m","scalping_bot","collect" `
  -RedirectStandardOutput "logs\collector.jsonl"
```

Or Task Scheduler for autorun on boot.

## Downloading historical data

```bash
# Trades only (~33 MB/day compressed, no date limit)
uv run python -m scalping_bot download \
  --kind trades --start 2025-06-01 --end 2025-12-31

# Orderbook only (~290 MB/day zip, available since May 2025)
uv run python -m scalping_bot download \
  --kind orderbook --start 2025-06-01 --end 2025-06-30

# Both (default)
uv run python -m scalping_bot download \
  --start 2025-06-01 --end 2025-06-07
```

Files go under `data/archives/` (raw zip/csv.gz), then get converted and
written to `data/raw/` in the same hourly Parquet layout the live
collector uses. Archives are deleted after conversion unless you pass
`--keep-archives`.

Sources:
- Trades:    `public.bybit.com/trading/SYMBOL/SYMBOLYYYY-MM-DD.csv.gz`
  (from March 2020)
- Orderbook: `quote-saver.bycsi.com/orderbook/linear/SYMBOL/YYYY-MM-DD_SYMBOL_ob200.data.zip`
  (from May 2025, ~290 MB/day zipped)

## Data layout (live collector + historical downloader)

```
data/raw/
├── trades/date=YYYY-MM-DD/BTCUSDT_HH.parquet
├── orderbook/date=YYYY-MM-DD/BTCUSDT_HH.parquet           (deltas)
├── orderbook_snapshots/date=YYYY-MM-DD/BTCUSDT_HH.parquet
└── tickers/date=YYYY-MM-DD/BTCUSDT_HH.parquet
```

Compressed with snappy. Approx storage for BTCUSDT mainnet:
~10 MB/hour, ~240 MB/day, ~7 GB/month at depth=50.

## Disk budget

| Data type | Per day | 1 month | 6 months |
|---|---|---|---|
| Trades (historical) | 33 MB gz | 1 GB | 6 GB |
| Trades (Parquet) | ~15 MB | 450 MB | 2.7 GB |
| Orderbook (historical zip) | 290 MB | 8.7 GB | 52 GB |
| Orderbook (Parquet) | ~100 MB | 3 GB | 18 GB |
| Live collector | — | 7 GB | — |

Risk subsystem is the foundation. It will be extended in later phases
with pre-trade checks, but the constants in `risk/limits.py` never
become user-configurable. They require a code change.

## Phase roadmap

| Phase | Content | Gate to next phase |
|---|---|---|
| **0** | Risk framework, kill switch, accounting, tests | Tests ≥ 90% coverage, all green |
| 1 | WebSocket data collector (trades + L2 orderbook) | 30+ days of clean ticks |
| 2 | Feature engineering + EDA | Stable feature set (20-30 fields) |
| 3 | Distinguisher classifier (linear + pairwise) | AUC > 0.55 walk-forward |
| 4 | SuperBit execution layer integration | Unit tests pass |
| 5 | Realistic backtest (GARCH + costs + walk-forward) | Sharpe > 1.5 after costs |
| 6 | Paper trading on Bybit testnet | Paper matches backtest ±30% |
| 7 | Micro-live ($20-30 of $100) | Positive after 100+ trades |
| 8 | Scale and maintain | — |

Total realistic timeline to real-money trading: **4–6 months**.

## Risk parameters

Hardcoded in `src/scalping_bot/risk/limits.py`. Changing them requires
editing the source and running tests.

| Parameter | Value | Rationale |
|---|---|---|
| `MAX_LEVERAGE` | 3.0 | $100 survival; pros rarely >5x |
| `MAX_POSITION_PCT_OF_EQUITY` | 30% | Headroom + slippage buffer |
| `MAX_DAILY_LOSS_PCT` | 3% | 10 bad days = 26% DD, not ruin |
| `KILL_SWITCH_DRAWDOWN_PCT` | 10% | Forces strategy review |
| `MAX_CONSECUTIVE_LOSSES` | 3 | Regime-break detector |
| `MAX_TRADES_PER_HOUR` | 20 | Sanity cap |
| `MIN_LIQUIDATION_DISTANCE_PCT` | 10% | Oct 2025 crash lesson |

Background in `../docs/research_notes.md`.

## Philosophy

- **Risk limits are hardcoded.** Not configurable. A git diff is the
  only way to change them. This is intentional friction.
- **Kill switch is first-class.** It owns the transition graph and the
  event log. Manual reset is required after a hard kill.
- **Structured logs.** Every log line is a JSON object with ISO-8601
  UTC timestamp and arbitrary context. Parseable with `jq`.
- **Honest about limitations.** $100 on a scalping bot is mostly
  tuition. Expect to lose it learning the mechanics. Real profit
  comes later — or not at all. The bot is meant to be **survivable**,
  not magical.
