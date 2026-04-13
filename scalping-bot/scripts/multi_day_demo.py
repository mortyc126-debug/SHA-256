"""Multi-day demo: run IntuitionTrader on all available days.

Per day:
  - Reset trader state (each day is independent — matches user's
    rule that yesterday's regime is gone)
  - Stream all bars through trader.step
  - Force-close at end of day
  - Log per-day metrics

Aggregate at the end:
  - Total trades, win rate, P&L
  - Day-by-day equity progression
  - Max drawdown across the run

Capital model: each day starts with the equity left from the
previous day. Compounded.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from scalping_bot.backtest.engine import BacktestEngine, FeeModel
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.features import load_trades_range
from scalping_bot.features.flow import aggregate_trades_to_bars
from scalping_bot.intuition import IntuitionTrader, IntuitionTraderConfig
from scalping_bot.live.bar_builder import OneSecondBar


SYMBOL = "BTCUSDT"
START_DATE = date(2025, 12, 21)
END_DATE = date(2025, 12, 30)
INITIAL_CAPITAL = 100.0


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


def run_day(
    bars: list[OneSecondBar],
    trader: IntuitionTrader,
    starting_equity: float,
) -> dict:
    engine = BacktestEngine(
        starting_capital_usd=starting_equity,
        leverage=10.0,
        fee_model=FeeModel(),
        use_taker=False,  # maker
    )
    trader.reset()
    t0 = time.time()
    for i in range(1, len(bars) + 1):
        trader.step(engine, bars[i - 1], bars[:i])

    # Force close at end of day
    if bars:
        trader.force_close(engine, bars[-1], "session_end")

    summary = summarize_trades(engine.trades, starting_capital_usd=starting_equity)
    elapsed = time.time() - t0

    reasons: dict[str, int] = {}
    for t in engine.trades:
        reasons[t.reason_close] = reasons.get(t.reason_close, 0) + 1

    return {
        "trades": summary.n_trades,
        "wins": summary.n_wins,
        "losses": summary.n_losses,
        "win_rate": summary.win_rate,
        "starting_equity": starting_equity,
        "final_equity": summary.final_equity_usd,
        "pnl_usd": summary.total_pnl_usd,
        "return_pct": summary.total_return_pct,
        "max_dd": summary.max_drawdown_pct,
        "fees": summary.total_fees_usd,
        "elapsed_sec": elapsed,
        "reasons": reasons,
    }


def main() -> None:
    print("\n=== MULTI-DAY INTUITION TRADER ===")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Symbol: {SYMBOL}, Starting capital: ${INITIAL_CAPITAL:.2f}")
    print(f"Strategy: σ-conviction (4 voters + super-state) + trailing stop")
    print(f"Leverage cap: 10x, fees: maker (-0.005% rebate)\n")

    cfg = IntuitionTraderConfig(
        sigma_enter=0.50,
        sigma_exit=0.25,
        confirm_bars=10,
        cooldown_bars=60,
        base_size_fraction=0.10,
        trailing_initial_sl_bps=30.0,
        trailing_breakeven_bps=5.0,
        trailing_distance_bps=5.0,
        trailing_initial_lock_bps=1.0,
        max_hold_bars=600,
        use_super_state=True,
        super_state_n_archetypes=12,
    )
    trader = IntuitionTrader(config=cfg)

    print(f"{'Date':12s}  {'Bars':>6}  {'Trades':>6}  {'Win%':>6}  "
          f"{'P&L $':>9}  {'Day %':>7}  {'Equity':>9}  {'MaxDD':>7}  {'Time':>6}")
    print("-" * 100)

    equity = INITIAL_CAPITAL
    peak_equity = INITIAL_CAPITAL
    all_results = []
    cumulative_max_dd = 0.0
    total_trades = 0
    total_wins = 0
    total_losses = 0

    current = START_DATE
    while current <= END_DATE:
        trades_df = load_trades_range(Path("data/raw"), SYMBOL, current, current)
        if trades_df.is_empty():
            print(f"{current.isoformat():12s}  (no data)")
            current += timedelta(days=1)
            continue

        bars_df = aggregate_trades_to_bars(trades_df, bar_seconds=1.0)
        bars = bars_from_polars(bars_df)

        result = run_day(bars, trader, starting_equity=equity)
        all_results.append((current, result))

        equity = result["final_equity"]
        peak_equity = max(peak_equity, equity)
        day_dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        cumulative_max_dd = max(cumulative_max_dd, day_dd)

        total_trades += result["trades"]
        total_wins += result["wins"]
        total_losses += result["losses"]

        print(
            f"{current.isoformat():12s}  {len(bars):>6}  {result['trades']:>6}  "
            f"{result['win_rate']*100:>5.1f}%  "
            f"{result['pnl_usd']:>+9.4f}  "
            f"{result['return_pct']*100:>+6.3f}%  "
            f"{result['final_equity']:>9.4f}  "
            f"{result['max_dd']*100:>6.2f}%  "
            f"{result['elapsed_sec']:>5.1f}s"
        )
        current += timedelta(days=1)

    # --- Aggregate ---
    total_pnl = equity - INITIAL_CAPITAL
    total_return_pct = (equity / INITIAL_CAPITAL - 1.0) if INITIAL_CAPITAL > 0 else 0
    overall_win_rate = total_wins / total_trades if total_trades > 0 else 0

    # Sum of fees and reasons
    total_fees = sum(r["fees"] for _, r in all_results)
    all_reasons: dict[str, int] = {}
    for _, r in all_results:
        for reason, count in r["reasons"].items():
            all_reasons[reason] = all_reasons.get(reason, 0) + count

    print()
    print("=" * 80)
    print(f"AGGREGATE RESULTS — {len(all_results)} days")
    print("=" * 80)
    print(f"Starting capital:    ${INITIAL_CAPITAL:.2f}")
    print(f"Final equity:        ${equity:.4f}")
    print(f"Total P&L:           ${total_pnl:+.4f}  ({total_return_pct*100:+.3f}%)")
    print(f"Total fees (rebate): ${total_fees:+.4f}  "
          f"{'(maker rebate received)' if total_fees < 0 else '(taker cost)'}")
    print(f"Total trades:        {total_trades}  ({total_wins}W / {total_losses}L)")
    print(f"Overall win rate:    {overall_win_rate*100:.1f}%")
    print(f"Cumulative max DD:   {cumulative_max_dd*100:.2f}%")
    print(f"Avg trades/day:      {total_trades / len(all_results):.1f}")
    if all_results:
        avg_daily_return = sum(r["return_pct"] for _, r in all_results) / len(all_results)
        winning_days = sum(1 for _, r in all_results if r["pnl_usd"] > 0)
        print(f"Avg daily return:    {avg_daily_return*100:+.3f}%")
        print(f"Winning days:        {winning_days}/{len(all_results)}")

    print(f"\nClose reasons across all days:")
    for r, c in sorted(all_reasons.items(), key=lambda x: -x[1]):
        print(f"  {r:24}{c:>5}")

    # Annualization estimate (only valid as ROUGH estimate)
    if all_results and total_return_pct != 0:
        days = len(all_results)
        annualized = (1 + total_return_pct) ** (365 / days) - 1
        print(f"\nAnnualized estimate (compound): {annualized*100:+.1f}% per year")
        print(f"  ⚠ Based on {days}-day sample. Real long-term will differ.")


if __name__ == "__main__":
    main()
