# scalping-bot

BTC perpetual scalping bot on Bybit. Risk-first architecture,
5s–10min timeframe. Python 3.12 + pybit + uv.

> Status: **Phase 1** — risk framework + market data collector (live WebSocket
> ingest → Parquet). No trading logic yet.

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

## Running the data collector

```bash
# Mainnet public streams (no credentials needed)
uv run python -m scalping_bot collect --duration 3600

# Custom symbol and depth
uv run python -m scalping_bot collect --symbol BTCUSDT --depth 50

# Testnet (lower activity; not representative of real microstructure)
uv run python -m scalping_bot collect --testnet
```

Data layout:

```
data/raw/
├── trades/date=YYYY-MM-DD/BTCUSDT_HH.parquet
├── orderbook/date=YYYY-MM-DD/BTCUSDT_HH.parquet                (deltas)
├── orderbook_snapshots/date=YYYY-MM-DD/BTCUSDT_HH.parquet
└── tickers/date=YYYY-MM-DD/BTCUSDT_HH.parquet
```

Compressed with snappy. Approx storage for BTCUSDT mainnet:
~10 MB/hour, ~240 MB/day, ~7 GB/month at depth=50.

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
