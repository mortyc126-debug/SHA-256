"""Intuition + trailing-stop demo: aim for high win rate via locked profit.

Strategy:
1. Wait for σ-conviction from intuition engine.
2. Enter with leverage scaled by σ (capped at MAX_LEV).
3. Use TrailingStopState:
    - Initial SL at -30 bps.
    - On +5 bps profit: move SL to entry + 1 bp (lock).
    - Then trail SL 5 bps behind best price.
4. Exit on stop hit OR session reversal.

Conjecture being tested: trailing converts most trades into wins
(or tiny losses), pushing win rate above the 50% line that symmetric
SL/TP gives.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scalping_bot.backtest.engine import BacktestEngine, FeeModel, Side
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.features import load_trades_range
from scalping_bot.features.flow import aggregate_trades_to_bars
from scalping_bot.intuition import (
    IntuitionConfig,
    IntuitionEngine,
    TrailingStopConfig,
    TrailingStopState,
)
from scalping_bot.live.bar_builder import OneSecondBar


SYMBOL = "BTCUSDT"
TEST_DATE = date(2025, 12, 30)
STARTING_CAPITAL = 100.0
MAX_LEVERAGE = 10.0
MAX_HOLD_BARS = 600  # 10 minutes


def bars_from_polars(df) -> list[OneSecondBar]:
    return [
        OneSecondBar(
            ts_bar=row["ts_bar"], open=row["open"], high=row["high"], low=row["low"],
            close=row["close"], vwap=row["vwap"], volume=row["volume"],
            buy_volume=row["buy_volume"], sell_volume=row["sell_volume"],
            trade_count=row["trade_count"],
        )
        for row in df.iter_rows(named=True)
    ]


def run(
    bars: list[OneSecondBar],
    *,
    sigma_enter: float,
    confirm_bars: int,
    trailing: TrailingStopConfig,
    leverage_min: float,
    leverage_max: float,
    use_taker: bool,
) -> dict:
    engine = BacktestEngine(
        starting_capital_usd=STARTING_CAPITAL,
        leverage=leverage_max,
        fee_model=FeeModel(),
        use_taker=use_taker,
    )
    intuition = IntuitionEngine(
        IntuitionConfig(
            confirm_bars=confirm_bars,
            sigma_enter=sigma_enter,
            sigma_exit=sigma_enter * 0.5,
            cooldown_bars=60,
        )
    )

    stop_state: TrailingStopState | None = None
    bars_in_pos = 0

    for i in range(1, len(bars) + 1):
        window = bars[:i]
        bar = bars[i - 1]
        engine.mark_to_market(bar.close)
        state = intuition.evaluate(window)

        if engine.position is not None and stop_state is not None:
            bars_in_pos += 1
            stop_hit = stop_state.update(bar.close, trailing)
            if stop_hit:
                # Determine reason: locked profit or initial SL?
                realized_bps = stop_state.realized_profit_bps_if_stopped()
                reason = (
                    "trail_lock_profit"
                    if stop_state.breakeven_triggered and realized_bps > 0
                    else ("trail_breakeven" if stop_state.breakeven_triggered else "initial_sl")
                )
                engine.close_position(bar.ts_bar, bar.close, reason)
                intuition.cooldown_after_trade()
                stop_state = None
                bars_in_pos = 0
            elif bars_in_pos >= MAX_HOLD_BARS:
                engine.close_position(bar.ts_bar, bar.close, "time_exit")
                intuition.cooldown_after_trade()
                stop_state = None
                bars_in_pos = 0
        elif engine.position is None and state.is_convicted:
            # σ → leverage scaling within [min, max]
            sigma_abs = abs(state.sigma)
            lev = leverage_min + (leverage_max - leverage_min) * sigma_abs
            size_fraction = (lev / leverage_max) * 0.20  # base 20% kelly

            side = Side.LONG if state.direction > 0 else Side.SHORT
            opened = engine.open_position(side, bar.ts_bar, bar.close, size_fraction)
            if opened:
                stop_state = TrailingStopState.open(side, bar.close, trailing)
                bars_in_pos = 0

    if engine.position is not None:
        engine.close_position(bars[-1].ts_bar, bars[-1].close, "session_end")

    summary = summarize_trades(engine.trades, starting_capital_usd=STARTING_CAPITAL)

    # Reason breakdown
    reasons: dict[str, int] = {}
    for t in engine.trades:
        reasons[t.reason_close] = reasons.get(t.reason_close, 0) + 1

    return {
        "trades": summary.n_trades,
        "win_rate": summary.win_rate,
        "return_pct": summary.total_return_pct,
        "max_dd": summary.max_drawdown_pct,
        "fees": summary.total_fees_usd,
        "final": summary.final_equity_usd,
        "reasons": reasons,
    }


def main() -> None:
    print(f"\n=== TRAILING-STOP DEMO on {TEST_DATE} ===\n")
    trades = load_trades_range(Path("data/raw"), SYMBOL, TEST_DATE, TEST_DATE)
    bars_df = aggregate_trades_to_bars(trades, bar_seconds=1.0)
    bars = bars_from_polars(bars_df)
    print(f"Loaded {len(bars):,} bars\n")

    # Grid: trailing aggressiveness × confirm bars
    configs = [
        # name, breakeven_bps, lock_bps, trail_bps, sigma_enter, confirm_bars
        ("baseline (no trail)", 999, 0, 999, 0.40, 5),  # never triggers trail
        ("aggressive 3/1/3", 3, 1, 3, 0.40, 5),
        ("standard 5/1/5",   5, 1, 5, 0.40, 5),
        ("loose 8/2/8",      8, 2, 8, 0.40, 5),
        ("very loose 15/5/10", 15, 5, 10, 0.40, 5),
        ("std + selective 5/1/5 σ=0.30 conf=20", 5, 1, 5, 0.30, 20),
        ("std + very selective σ=0.50 conf=10", 5, 1, 5, 0.50, 10),
    ]

    print(f"{'Config':45s}  {'Trades':>6}  {'Win%':>6}  {'Return':>8}  "
          f"{'MaxDD':>7}  {'Final $':>9}")
    print("-" * 100)

    all_results = []
    for name, be, lock, trail, sigma, confirm in configs:
        cfg = TrailingStopConfig(
            initial_sl_bps=30.0,
            breakeven_trigger_bps=be,
            trail_distance_bps=trail,
            initial_lock_bps=lock,
        )
        r = run(
            bars,
            sigma_enter=sigma,
            confirm_bars=confirm,
            trailing=cfg,
            leverage_min=1.0,
            leverage_max=MAX_LEVERAGE,
            use_taker=False,  # maker
        )
        all_results.append((name, r))
        marker = ""
        if r["win_rate"] >= 0.85 and r["trades"] >= 10:
            marker = " ★ HIGH WR"
        elif r["return_pct"] > 0.005 and r["trades"] >= 10:
            marker = " ✓"
        print(
            f"{name:45s}  {r['trades']:>6}  {r['win_rate']*100:>5.1f}%  "
            f"{r['return_pct']*100:>+7.3f}%  {r['max_dd']*100:>6.2f}%  "
            f"{r['final']:>9.3f}{marker}"
        )

    # Show close-reason breakdown for the best one
    print("\n=== CLOSE REASONS — best by return ===\n")
    best = max(all_results, key=lambda x: x[1]["return_pct"])
    print(f"Config: {best[0]}")
    print(f"Return: {best[1]['return_pct']*100:+.3f}%, Win rate: {best[1]['win_rate']*100:.1f}%")
    print(f"Reasons:")
    for r, c in sorted(best[1]["reasons"].items(), key=lambda x: -x[1]):
        print(f"  {r:24}  {c:>4}")

    print("\n=== CLOSE REASONS — best by win rate (10+ trades) ===\n")
    eligible = [r for r in all_results if r[1]["trades"] >= 10]
    if eligible:
        best_wr = max(eligible, key=lambda x: x[1]["win_rate"])
        print(f"Config: {best_wr[0]}")
        print(f"Win rate: {best_wr[1]['win_rate']*100:.1f}%, Return: {best_wr[1]['return_pct']*100:+.3f}%")
        print(f"Reasons:")
        for r, c in sorted(best_wr[1]["reasons"].items(), key=lambda x: -x[1]):
            print(f"  {r:24}  {c:>4}")


if __name__ == "__main__":
    main()
