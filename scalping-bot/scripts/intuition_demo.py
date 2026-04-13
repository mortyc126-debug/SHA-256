"""Demo: bot with NO training data, only "here-and-now" intuition.

Walks through Dec 30 BTCUSDT bar by bar. The IntuitionEngine evaluates
the current state, accumulates conviction, and trades when convinced —
exactly like a discretionary trader watching the screen.

Compare with demo_run.py (which uses a model trained on 9 prior days).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scalping_bot.backtest.engine import BacktestEngine, FeeModel, Side
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.features.flow import aggregate_trades_to_bars
from scalping_bot.features import load_trades_range
from scalping_bot.intuition import IntuitionConfig, IntuitionEngine
from scalping_bot.live.bar_builder import OneSecondBar


SYMBOL = "BTCUSDT"
TEST_DATE = date(2025, 12, 30)
STARTING_CAPITAL = 100.0
LEVERAGE = 3.0  # production-safe

# Strategy parameters
TAKE_PROFIT_BPS = 20.0
STOP_LOSS_BPS = 30.0
MAX_HOLD_BARS = 300  # 5 minutes


def bars_from_polars(df) -> list[OneSecondBar]:
    """Convert our trades-aggregated polars frame into OneSecondBar list."""
    return [
        OneSecondBar(
            ts_bar=row["ts_bar"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            vwap=row["vwap"],
            volume=row["volume"],
            buy_volume=row["buy_volume"],
            sell_volume=row["sell_volume"],
            trade_count=row["trade_count"],
        )
        for row in df.iter_rows(named=True)
    ]


def main() -> None:
    print(f"\n=== INTUITION-ONLY DEMO ===")
    print(f"Symbol: {SYMBOL}, Date: {TEST_DATE}")
    print(f"Capital: ${STARTING_CAPITAL}, Leverage: {LEVERAGE}x, Maker fees")
    print(f"NO TRAINING — bot reads current microstructure only\n")

    # Load and bar-aggregate the test day
    trades = load_trades_range(Path("data/raw"), SYMBOL, TEST_DATE, TEST_DATE)
    print(f"Loaded {len(trades):,} ticks")
    bars_df = aggregate_trades_to_bars(trades, bar_seconds=1.0)
    bars = bars_from_polars(bars_df)
    print(f"Aggregated {len(bars):,} 1-second bars\n")

    engine = BacktestEngine(
        starting_capital_usd=STARTING_CAPITAL,
        leverage=LEVERAGE,
        fee_model=FeeModel(),
        use_taker=False,  # maker
    )
    intuition = IntuitionEngine(
        IntuitionConfig(
            confirm_bars=5,
            sigma_enter=0.40,
            sigma_exit=0.20,
            cooldown_bars=60,
        )
    )

    # Track the active position's holding bars and entry sigma for exit
    bars_in_position = 0

    print(f"{'#':>4}  {'Time':19}  {'Side':5}  {'Entry':>10}  {'Exit':>10}  "
          f"{'Hold':>5}  {'σ@open':>7}  {'P&L $':>7}  {'Equity':>9}  Reason")
    print("-" * 130)

    n_trades_before = 0
    open_sigma = 0.0
    for i in range(1, len(bars) + 1):
        window = bars[:i]
        bar = bars[i - 1]
        engine.mark_to_market(bar.close)
        state = intuition.evaluate(window)

        if engine.position is not None:
            bars_in_position += 1
            pos = engine.position

            # P&L percentage
            if pos.side == Side.LONG:
                pnl_pct = (bar.close - pos.entry_price) / pos.entry_price
            else:
                pnl_pct = (pos.entry_price - bar.close) / pos.entry_price

            # Exit conditions
            close_reason = None
            if pnl_pct >= TAKE_PROFIT_BPS / 10_000.0:
                close_reason = "take_profit"
            elif pnl_pct <= -STOP_LOSS_BPS / 10_000.0:
                close_reason = "stop_loss"
            elif bars_in_position >= MAX_HOLD_BARS:
                close_reason = "time_exit"
            elif (pos.side == Side.LONG and state.sigma < -intuition.config.sigma_exit) or (
                pos.side == Side.SHORT and state.sigma > intuition.config.sigma_exit
            ):
                close_reason = "intuition_reversal"
            elif abs(state.sigma) < intuition.config.sigma_exit and bars_in_position > 30:
                close_reason = "intuition_fade"

            if close_reason:
                engine.close_position(bar.ts_bar, bar.close, close_reason)
                intuition.cooldown_after_trade()
                bars_in_position = 0
                t = engine.trades[-1]
                hold_s = (t.exit_ts - t.entry_ts).total_seconds()
                print(
                    f"{len(engine.trades):>4}  "
                    f"{t.entry_ts.strftime('%Y-%m-%d %H:%M:%S')}  "
                    f"{t.side.value:5}  "
                    f"{t.entry_price:>10.2f}  "
                    f"{t.exit_price:>10.2f}  "
                    f"{hold_s:>4.0f}s  "
                    f"{open_sigma:>+7.3f}  "
                    f"{t.pnl_usd:>+7.3f}  "
                    f"{engine.equity:>9.3f}  "
                    f"{t.reason_close}"
                )

        elif state.is_convicted:
            # Open in conviction direction
            if state.direction > 0:
                engine.open_position(Side.LONG, bar.ts_bar, bar.close, 0.10)
            else:
                engine.open_position(Side.SHORT, bar.ts_bar, bar.close, 0.10)
            bars_in_position = 0
            open_sigma = state.sigma

    if engine.position is not None:
        engine.close_position(bars[-1].ts_bar, bars[-1].close, "session_end")
        t = engine.trades[-1]
        hold_s = (t.exit_ts - t.entry_ts).total_seconds()
        print(
            f"{len(engine.trades):>4}  "
            f"{t.entry_ts.strftime('%Y-%m-%d %H:%M:%S')}  "
            f"{t.side.value:5}  "
            f"{t.entry_price:>10.2f}  "
            f"{t.exit_price:>10.2f}  "
            f"{hold_s:>4.0f}s  "
            f"{open_sigma:>+7.3f}  "
            f"{t.pnl_usd:>+7.3f}  "
            f"{engine.equity:>9.3f}  "
            f"{t.reason_close}"
        )

    summary = summarize_trades(engine.trades, starting_capital_usd=STARTING_CAPITAL)
    print()
    print("=" * 60)
    print(f"INTUITION-ONLY RESULTS for {TEST_DATE}")
    print("=" * 60)
    print(f"Final equity:     ${summary.final_equity_usd:.4f}")
    print(f"Total P&L:        ${summary.total_pnl_usd:+.4f}  ({summary.total_return_pct*100:+.3f}%)")
    print(f"Total fees:       ${summary.total_fees_usd:+.4f}")
    print(f"Trades:           {summary.n_trades}  ({summary.n_wins}W / {summary.n_losses}L)")
    print(f"Win rate:         {summary.win_rate*100:.1f}%")
    if summary.profit_factor != float("inf"):
        print(f"Profit factor:    {summary.profit_factor:.3f}")
    print(f"Avg holding time: {summary.avg_holding_seconds:.0f} sec")
    print(f"Max drawdown:     {summary.max_drawdown_pct*100:.2f}%")

    reasons: dict[str, int] = {}
    for t in engine.trades:
        reasons[t.reason_close] = reasons.get(t.reason_close, 0) + 1
    if reasons:
        print(f"\nClose reasons:")
        for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  {r:24}{c:>3}")


if __name__ == "__main__":
    main()
