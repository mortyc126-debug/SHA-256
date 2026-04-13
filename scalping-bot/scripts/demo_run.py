"""One-off demo: train on 9 days, simulate trading on the 10th day with $100.

Usage: uv run python scripts/demo_run.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from scalping_bot.backtest.engine import BacktestEngine, FeeModel
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.backtest.strategy import StrategyConfig, ThresholdStrategy
from scalping_bot.features import build_feature_matrix, load_trades_range
from scalping_bot.models import Distinguisher

# Configuration
SYMBOL = "BTCUSDT"
TRAIN_START, TRAIN_END = date(2025, 12, 21), date(2025, 12, 29)
TEST_DATE = date(2025, 12, 30)
STARTING_CAPITAL = 100.0
LEVERAGE = 3.0
MAKER = True  # use maker fees (rebate)

# Strategy params (the ones that survived backtest)
STRATEGY = StrategyConfig(
    enter_threshold=0.40,
    exit_threshold=0.50,
    take_profit_bps=20.0,
    stop_loss_bps=30.0,
    max_hold_bars=300,  # 5 minutes
    kelly_fraction=0.20,
    min_size_fraction=0.05,
)

FEATURE_COLS = [
    "flow_imbalance",
    "trade_rate",
    "rv_w60",
    "rv_w300",
    "vwap_w30",
    "vwap_w300",
    "cum_delta_w30",
    "cum_delta_w300",
    "price_range_w300",
    "hour_sin",
    "hour_cos",
    "minute_sin",
    "minute_cos",
]


def main() -> None:
    data_dir = Path("data/raw")

    # --- 1. Train ---------------------------------------------------------
    print(f"\n=== TRAINING on {TRAIN_START} .. {TRAIN_END} ===")
    train_trades = load_trades_range(data_dir, SYMBOL, TRAIN_START, TRAIN_END)
    print(f"Train ticks: {len(train_trades):,}")

    train_fm = build_feature_matrix(
        train_trades,
        bar_seconds=1.0,
        label_horizon_bars=300,
        label_threshold_bps=10.0,
    )
    print(f"Train bars: {len(train_fm):,}")

    label_col = "label_300"
    model = Distinguisher(
        feature_cols=FEATURE_COLS,
        label_col=label_col,
        n_pairwise=10,
        max_iter=500,
    )
    model.fit(train_fm)
    print(f"Model fit. Pairwise specs: {len(model.pairwise_specs)}")

    # --- 2. Test ----------------------------------------------------------
    print(f"\n=== TESTING on {TEST_DATE} ===")
    test_trades = load_trades_range(data_dir, SYMBOL, TEST_DATE, TEST_DATE)
    test_fm = build_feature_matrix(
        test_trades,
        bar_seconds=1.0,
        label_horizon_bars=300,
        label_threshold_bps=10.0,
    )
    print(f"Test bars: {len(test_fm):,}")

    proba = model.predict_proba(test_fm)
    classes = model.classes_.tolist()
    proba_up = proba[:, classes.index(1)]
    proba_down = proba[:, classes.index(-1)]

    # --- 3. Simulate ------------------------------------------------------
    print(f"\n=== SIMULATING with ${STARTING_CAPITAL:.2f}, {LEVERAGE}x leverage, "
          f"{'maker' if MAKER else 'taker'} fees ===\n")

    engine = BacktestEngine(
        starting_capital_usd=STARTING_CAPITAL,
        leverage=LEVERAGE,
        fee_model=FeeModel(),
        use_taker=not MAKER,
    )
    strategy = ThresholdStrategy(config=STRATEGY)

    prices = test_fm["close"].to_numpy()
    timestamps = test_fm["ts_bar"].to_list()

    print(f"{'#':>4}  {'Time':19}  {'Side':5}  {'Entry':>10}  {'Exit':>10}  "
          f"{'Hold':>5}  {'P&L $':>7}  {'Equity':>9}  Reason")
    print("-" * 110)

    trade_count_before = 0
    for ts, price, pu, pd in zip(timestamps, prices, proba_up, proba_down, strict=True):
        engine.mark_to_market(float(price))
        strategy.step(engine, ts, float(price), float(pu), float(pd))
        if len(engine.trades) > trade_count_before:
            t = engine.trades[-1]
            hold_s = (t.exit_ts - t.entry_ts).total_seconds()
            print(
                f"{len(engine.trades):>4}  "
                f"{t.entry_ts.strftime('%Y-%m-%d %H:%M:%S')}  "
                f"{t.side.value:5}  "
                f"{t.entry_price:>10.2f}  "
                f"{t.exit_price:>10.2f}  "
                f"{hold_s:>4.0f}s  "
                f"{t.pnl_usd:>+7.3f}  "
                f"{engine.equity:>9.3f}  "
                f"{t.reason_close}"
            )
            trade_count_before = len(engine.trades)

    if engine.position is not None:
        engine.close_position(timestamps[-1], float(prices[-1]), "session_end")
        t = engine.trades[-1]
        hold_s = (t.exit_ts - t.entry_ts).total_seconds()
        print(
            f"{len(engine.trades):>4}  "
            f"{t.entry_ts.strftime('%Y-%m-%d %H:%M:%S')}  "
            f"{t.side.value:5}  "
            f"{t.entry_price:>10.2f}  "
            f"{t.exit_price:>10.2f}  "
            f"{hold_s:>4.0f}s  "
            f"{t.pnl_usd:>+7.3f}  "
            f"{engine.equity:>9.3f}  "
            f"{t.reason_close}"
        )

    # --- 4. Summary -------------------------------------------------------
    summary = summarize_trades(engine.trades, starting_capital_usd=STARTING_CAPITAL)
    print()
    print("=" * 60)
    print(f"RESULTS for {TEST_DATE}")
    print("=" * 60)
    print(f"Starting capital:    ${STARTING_CAPITAL:.2f}")
    print(f"Final equity:        ${summary.final_equity_usd:.4f}")
    print(f"Total P&L:           ${summary.total_pnl_usd:+.4f}  ({summary.total_return_pct*100:+.3f}%)")
    print(f"Total fees:          ${summary.total_fees_usd:+.4f}  "
          f"{'(rebate)' if summary.total_fees_usd < 0 else '(cost)'}")
    print(f"Trades:              {summary.n_trades}  ({summary.n_wins}W / {summary.n_losses}L)")
    print(f"Win rate:            {summary.win_rate*100:.1f}%")
    if summary.profit_factor != float("inf"):
        print(f"Profit factor:       {summary.profit_factor:.3f}")
    else:
        print("Profit factor:       inf (no losses)")
    print(f"Avg P&L per trade:   ${summary.avg_pnl_usd:+.4f}")
    print(f"Avg holding time:    {summary.avg_holding_seconds:.1f} sec")
    print(f"Max drawdown:        {summary.max_drawdown_pct*100:.2f}%")
    if summary.sharpe_annualized:
        print(f"Sharpe (annualized): {summary.sharpe_annualized:.2f}  "
              f"(small-sample, take with grain of salt)")

    # Reason breakdown
    reasons: dict[str, int] = {}
    for t in engine.trades:
        reasons[t.reason_close] = reasons.get(t.reason_close, 0) + 1
    if reasons:
        print(f"\nClose reasons:")
        for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  {r:20} {c:3}")


if __name__ == "__main__":
    main()
