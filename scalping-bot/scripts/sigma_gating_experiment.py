"""Experiment 2: σ-gating — only trade when confidence exceeds threshold.

Hypothesis: low avg σ in our model means most signals are noise.
Filter to high-σ events only. Higher win rate, fewer trades, possibly
better risk-adjusted return.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from scalping_bot.backtest.engine import BacktestEngine, FeeModel, Side
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.backtest.strategy import StrategyConfig, ThresholdStrategy
from scalping_bot.features import build_feature_matrix, load_trades_range
from scalping_bot.models import Distinguisher

SYMBOL = "BTCUSDT"
TRAIN_START, TRAIN_END = date(2025, 12, 21), date(2025, 12, 29)
TEST_DATE = date(2025, 12, 30)
STARTING_CAPITAL = 100.0

FEATURE_COLS = [
    "flow_imbalance", "trade_rate", "rv_w60", "rv_w300",
    "vwap_w30", "vwap_w300", "cum_delta_w30", "cum_delta_w300",
    "price_range_w300", "hour_sin", "hour_cos", "minute_sin", "minute_cos",
]


def run_with_sigma_gate(
    fm: pl.DataFrame,
    proba_up: np.ndarray,
    proba_down: np.ndarray,
    sigma_min: float,
    leverage: float,
) -> dict:
    engine = BacktestEngine(
        starting_capital_usd=STARTING_CAPITAL,
        leverage=leverage,
        fee_model=FeeModel(),
        use_taker=False,  # maker
    )
    cfg = StrategyConfig(
        enter_threshold=0.40,
        exit_threshold=0.50,
        take_profit_bps=20.0,
        stop_loss_bps=30.0,
        max_hold_bars=300,
        kelly_fraction=0.20,
    )
    strategy = ThresholdStrategy(config=cfg)

    prices = fm["close"].to_numpy()
    timestamps = fm["ts_bar"].to_list()

    for ts, price, pu, pd in zip(timestamps, prices, proba_up, proba_down, strict=True):
        engine.mark_to_market(float(price))
        sigma = abs(float(pu) - float(pd))

        # σ-gate: skip low-confidence bars from opening
        if engine.position is None and sigma < sigma_min:
            continue

        strategy.step(engine, ts, float(price), float(pu), float(pd))

    if engine.position is not None:
        engine.close_position(timestamps[-1], float(prices[-1]), "session_end")

    summary = summarize_trades(engine.trades, starting_capital_usd=STARTING_CAPITAL)
    return {
        "sigma_min": sigma_min,
        "leverage": leverage,
        "trades": summary.n_trades,
        "win_rate": summary.win_rate,
        "return_pct": summary.total_return_pct,
        "max_dd": summary.max_drawdown_pct,
        "fees": summary.total_fees_usd,
        "final": summary.final_equity_usd,
    }


def main() -> None:
    print("\n=== TRAINING ===")
    train_trades = load_trades_range(Path("data/raw"), SYMBOL, TRAIN_START, TRAIN_END)
    train_fm = build_feature_matrix(
        train_trades, bar_seconds=1.0, label_horizon_bars=300, label_threshold_bps=10.0
    )
    print(f"Train bars: {len(train_fm):,}")

    model = Distinguisher(
        feature_cols=FEATURE_COLS, label_col="label_300", n_pairwise=10, max_iter=500
    )
    model.fit(train_fm)

    print("\n=== TEST ===")
    test_trades = load_trades_range(Path("data/raw"), SYMBOL, TEST_DATE, TEST_DATE)
    test_fm = build_feature_matrix(
        test_trades, bar_seconds=1.0, label_horizon_bars=300, label_threshold_bps=10.0
    )

    proba = model.predict_proba(test_fm)
    classes = model.classes_.tolist()
    proba_up = proba[:, classes.index(1)]
    proba_down = proba[:, classes.index(-1)]

    sigma_all = np.abs(proba_up - proba_down)
    print(f"σ percentiles: p50={np.quantile(sigma_all, 0.5):.4f}, "
          f"p75={np.quantile(sigma_all, 0.75):.4f}, "
          f"p90={np.quantile(sigma_all, 0.90):.4f}, "
          f"p95={np.quantile(sigma_all, 0.95):.4f}, "
          f"p99={np.quantile(sigma_all, 0.99):.4f}")

    # Grid: σ-thresholds × leverage
    sigma_thresholds = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
    leverages = [3.0, 5.0, 10.0, 20.0]

    print("\n=== σ-GATE × LEVERAGE GRID (Dec 30, $100, maker) ===\n")
    print(f"{'σ-min':>7}  {'Lev':>4}  {'Trades':>6}  {'Win%':>6}  "
          f"{'Return':>8}  {'MaxDD':>7}  {'Final $':>9}")
    print("-" * 80)

    best = None
    for sigma_min in sigma_thresholds:
        for lev in leverages:
            r = run_with_sigma_gate(test_fm, proba_up, proba_down, sigma_min, lev)
            marker = ""
            if best is None or r["return_pct"] > best["return_pct"]:
                best = r
                marker = " ←"
            print(
                f"{r['sigma_min']:>7.2f}  {r['leverage']:>4.0f}  "
                f"{r['trades']:>6}  {r['win_rate']*100:>5.1f}%  "
                f"{r['return_pct']*100:>+7.3f}%  {r['max_dd']*100:>6.2f}%  "
                f"{r['final']:>9.3f}{marker}"
            )

    print(f"\nBest: σ-min={best['sigma_min']}, lev={best['leverage']}x → "
          f"return {best['return_pct']*100:+.3f}%, final ${best['final']:.3f}, "
          f"DD {best['max_dd']*100:.2f}%")


if __name__ == "__main__":
    main()
