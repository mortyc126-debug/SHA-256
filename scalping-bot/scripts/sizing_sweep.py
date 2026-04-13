"""Sizing × leverage × trade-rate sweep — how big can we go safely?

After the initial 10-day multi_day_demo showed +0.40% return with
very conservative sizing (5% × 10x = 50% effective leverage), this
script tests progressively more aggressive configurations:

  * Increasing base_size_fraction (5% → 30% → 50% of equity)
  * Increasing leverage cap (10x → 20x)
  * Relaxing entry gating (σ 0.50 → 0.40, confirm 10 → 5)

Results on Dec 21-30 BTCUSDT, $100 starting:

  Config                           Trades  Win%  Final  Return   MaxDD
  baseline 5% × 10x                   227  71.4 100.40  +0.40%   0.50%
  A: 30% × 10x                        227  71.4 101.19  +1.19%   1.51%
  B: 50% × 20x                        227  71.4 103.75  +3.75%   5.06%
  C: more trades (looser σ, smaller  1821  73.5 109.33  +9.33%   1.73%
     notional)
  D: maximum (C + 50% × 20x)         1821  73.5 133.10 +33.10%   6.15%

D's +33% on 10 days is IMPRESSIVE but comes with 6.15% MaxDD on a
quiet December. In a crash week this is easily 20-40%. Production
defaults unchanged — full validation needed on 30+ days across
regimes before raising MAX_LEVERAGE or size_fraction in live code.

The bot scales linearly: 8x more trades × 6x more notional = ~80x
the baseline return. Risk also scales.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from scalping_bot.backtest.engine import BacktestEngine, FeeModel
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.features import load_trades_range
from scalping_bot.features.flow import aggregate_trades_to_bars
from scalping_bot.intuition import IntuitionTrader, IntuitionTraderConfig
from scripts.multi_day_demo import bars_from_polars


SYMBOL = "BTCUSDT"
START = date(2025, 12, 21)
END = date(2025, 12, 30)
INITIAL_CAPITAL = 100.0


@dataclass
class SizingExperiment:
    name: str
    cfg: IntuitionTraderConfig
    leverage: float


EXPERIMENTS: list[SizingExperiment] = [
    SizingExperiment(
        "baseline (5% × 10x = 50% notional)",
        IntuitionTraderConfig(base_size_fraction=0.10),
        10.0,
    ),
    SizingExperiment(
        "A: 30% × 10x",
        IntuitionTraderConfig(base_size_fraction=0.30),
        10.0,
    ),
    SizingExperiment(
        "B: 50% × 20x",
        IntuitionTraderConfig(base_size_fraction=0.50),
        20.0,
    ),
    SizingExperiment(
        "C: more trades (σ=0.40, conf=5, cd=30)",
        IntuitionTraderConfig(
            base_size_fraction=0.30,
            sigma_enter=0.40,
            confirm_bars=5,
            cooldown_bars=30,
        ),
        10.0,
    ),
    SizingExperiment(
        "D: maximum (C + 50% size + 20x)",
        IntuitionTraderConfig(
            base_size_fraction=0.50,
            sigma_enter=0.40,
            confirm_bars=5,
            cooldown_bars=30,
        ),
        20.0,
    ),
]


def run_experiment(exp: SizingExperiment) -> dict:
    trader = IntuitionTrader(config=exp.cfg)
    equity = INITIAL_CAPITAL
    peak = INITIAL_CAPITAL
    cum_dd = 0.0
    total_trades = 0
    total_wins = 0
    blew_up = False

    current = START
    while current <= END:
        td = load_trades_range(Path("data/raw"), SYMBOL, current, current)
        if td.is_empty():
            current += timedelta(days=1)
            continue
        bars = bars_from_polars(aggregate_trades_to_bars(td, bar_seconds=1.0))
        engine = BacktestEngine(
            starting_capital_usd=equity,
            leverage=exp.leverage,
            fee_model=FeeModel(),
            use_taker=False,
        )
        trader.reset()
        for i in range(1, len(bars) + 1):
            trader.step(engine, bars[i - 1], bars[:i])
        if bars:
            trader.force_close(engine, bars[-1], "eod")
        s = summarize_trades(engine.trades, starting_capital_usd=equity)
        equity = s.final_equity_usd
        if equity <= 0:
            blew_up = True
            break
        peak = max(peak, equity)
        cum_dd = max(cum_dd, (peak - equity) / peak if peak > 0 else 0.0)
        total_trades += s.n_trades
        total_wins += s.n_wins
        current += timedelta(days=1)

    return {
        "name": exp.name,
        "trades": total_trades,
        "win_rate": total_wins / total_trades if total_trades else 0.0,
        "final": equity,
        "return_pct": (equity - INITIAL_CAPITAL) / INITIAL_CAPITAL,
        "max_dd": cum_dd,
        "blew_up": blew_up,
    }


def main() -> None:
    print(f"\n=== SIZING / LEVERAGE SWEEP ===")
    print(f"Period: {START} to {END}, ${INITIAL_CAPITAL:.2f} starting\n")

    print(f"{'Config':55s}  {'Trades':>6}  {'Win%':>6}  {'Final':>9}  "
          f"{'Return':>8}  {'MaxDD':>7}")
    print("-" * 110)

    for exp in EXPERIMENTS:
        r = run_experiment(exp)
        marker = " 💀 BLEW UP" if r["blew_up"] else ""
        print(
            f"{r['name']:55s}  {r['trades']:>6}  "
            f"{r['win_rate']*100:>5.1f}%  {r['final']:>9.4f}  "
            f"{r['return_pct']*100:>+7.3f}%  {r['max_dd']*100:>6.2f}%{marker}"
        )

    print("\n=== NOTES ===")
    print("1. Same trades across A/B/baseline (same entry logic, just size).")
    print("2. C/D have 8× more trades (looser σ/confirm/cooldown).")
    print("3. D's MaxDD 6% on calm December = likely 20-40% in a crash week.")
    print("4. Production defaults UNCHANGED. Validate on 30+ days first.")


if __name__ == "__main__":
    main()
