"""Experiment: σ-confidence-based adaptive leverage.

Idea (from SuperBit methodology §55-58, §61, §78):
    σ ∈ [0, 1] is per-decision confidence.
    Position size and leverage scale linearly with σ.
    High σ (clear signal) → larger position + higher leverage.
    Low σ (noisy)         → smaller position + lower leverage.

Compares 5 leverage configurations on the same train/test split.
Adds a simple liquidation model: if mark-to-market loss exceeds the
maintenance margin (5% of notional), the position is force-closed at
that price and counted as a stop-out.

Run: uv run python scripts/leverage_experiment.py
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

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
MAINTENANCE_MARGIN_RATE = 0.05  # 5% — Bybit-typical for low-leverage tiers

FEATURE_COLS = [
    "flow_imbalance", "trade_rate", "rv_w60", "rv_w300",
    "vwap_w30", "vwap_w300", "cum_delta_w30", "cum_delta_w300",
    "price_range_w300", "hour_sin", "hour_cos", "minute_sin", "minute_cos",
]


@dataclass
class LeverageConfig:
    name: str
    min_lev: float
    max_lev: float
    """Leverage interpolated linearly between min and max by confidence σ."""


CONFIGS = [
    LeverageConfig("fixed-3x  baseline", 3.0, 3.0),
    LeverageConfig("σ-scaled 1-3x  ",   1.0, 3.0),
    LeverageConfig("σ-scaled 1-10x ",   1.0, 10.0),
    LeverageConfig("σ-scaled 1-30x ",   1.0, 30.0),
    LeverageConfig("σ-scaled 1-50x ",   1.0, 50.0),
]


def confidence_sigma(p_up: float, p_down: float) -> float:
    """σ in [0, 1] from model probabilities. Concrete: |P_up - P_down|.

    Theoretical max distance is 1 (one prob = 1, other = 0). For
    multinomial with three classes this is rarely hit; typical signal
    σ ≈ 0.05-0.30 for our model.
    """
    return min(1.0, abs(p_up - p_down))


def adaptive_size_and_leverage(
    p_up: float,
    p_down: float,
    cfg: LeverageConfig,
    base_kelly: float = 0.20,
) -> tuple[float, float]:
    """Return (size_fraction_of_equity, effective_leverage).

    Strategy: confidence σ determines BOTH size and leverage.
    """
    sigma = confidence_sigma(p_up, p_down)
    leverage = cfg.min_lev + (cfg.max_lev - cfg.min_lev) * sigma
    size = max(0.05, min(1.0, sigma * base_kelly))
    return size, leverage


def _maybe_liquidate(
    engine: BacktestEngine,
    ts,
    price: float,
) -> bool:
    """If unrealized loss exceeds maintenance margin, force close.

    Maintenance margin = MAINTENANCE_MARGIN_RATE * notional. When equity
    + unrealized < 0, position is wiped. Returns True if we liquidated.
    """
    if engine.position is None:
        return False
    pos = engine.position
    unreal = pos.unrealized_pnl(price)
    # Equity contribution from this position would be reduced this much
    if engine.equity + unreal <= pos.notional_usd * MAINTENANCE_MARGIN_RATE:
        # Force close: model the worst — fill at current price (no slippage on emergency)
        engine.close_position(ts, price, "LIQUIDATED")
        return True
    return False


def run_one_config(
    feature_matrix: pl.DataFrame,
    proba_up: np.ndarray,
    proba_down: np.ndarray,
    cfg: LeverageConfig,
    use_maker: bool = True,
) -> dict[str, float | int]:
    """Run a single leverage config end-to-end on the test day."""
    base_strategy_cfg = StrategyConfig(
        enter_threshold=0.40,
        exit_threshold=0.50,
        take_profit_bps=20.0,
        stop_loss_bps=30.0,
        max_hold_bars=300,
        kelly_fraction=0.20,
    )

    engine = BacktestEngine(
        starting_capital_usd=STARTING_CAPITAL,
        leverage=cfg.max_lev,  # max allowed; per-trade leverage applied via size
        fee_model=FeeModel(),
        use_taker=not use_maker,
    )
    strategy = ThresholdStrategy(config=base_strategy_cfg)

    prices = feature_matrix["close"].to_numpy()
    timestamps = feature_matrix["ts_bar"].to_list()

    n_liquidations = 0
    sigma_history: list[float] = []

    for ts, price, pu, pd in zip(timestamps, prices, proba_up, proba_down, strict=True):
        # Mark-to-market and check liquidation
        engine.mark_to_market(float(price))
        if _maybe_liquidate(engine, ts, float(price)):
            n_liquidations += 1
            strategy.reset()  # clear holding counter
            if engine.equity <= 0:
                break  # game over

        # Custom open: bypass strategy's hardcoded leverage, set per-trade
        if engine.position is None and engine.equity > 0:
            sigma = confidence_sigma(float(pu), float(pd))
            sigma_history.append(sigma)
            if pu >= base_strategy_cfg.enter_threshold and pu > pd:
                size, lev = adaptive_size_and_leverage(float(pu), float(pd), cfg)
                # We re-target the engine's leverage for this trade via size scaling:
                effective_size = (size * lev) / cfg.max_lev
                engine.open_position(Side.LONG, ts, float(price), effective_size)
                strategy._bars_in_position = 0
            elif pd >= base_strategy_cfg.enter_threshold and pd > pu:
                size, lev = adaptive_size_and_leverage(float(pd), float(pu), cfg)
                effective_size = (size * lev) / cfg.max_lev
                engine.open_position(Side.SHORT, ts, float(price), effective_size)
                strategy._bars_in_position = 0
        elif engine.position is not None:
            # Use base strategy logic for exits
            strategy.step(engine, ts, float(price), float(pu), float(pd))

    # Force close at end
    if engine.position is not None:
        engine.close_position(timestamps[-1], float(prices[-1]), "session_end")

    summary = summarize_trades(engine.trades, starting_capital_usd=STARTING_CAPITAL)

    return {
        "name": cfg.name,
        "min_lev": cfg.min_lev,
        "max_lev": cfg.max_lev,
        "trades": summary.n_trades,
        "win_rate": summary.win_rate,
        "total_pnl_usd": summary.total_pnl_usd,
        "total_return_pct": summary.total_return_pct,
        "max_dd_pct": summary.max_drawdown_pct,
        "fees_usd": summary.total_fees_usd,
        "sharpe_ann": summary.sharpe_annualized or 0.0,
        "n_liquidations": n_liquidations,
        "final_equity": summary.final_equity_usd,
        "avg_sigma": float(np.mean(sigma_history)) if sigma_history else 0.0,
        "max_sigma": float(np.max(sigma_history)) if sigma_history else 0.0,
    }


def main() -> None:
    from pathlib import Path

    print("\n=== TRAINING (Dec 21-29) ===")
    train_trades = load_trades_range(Path("data/raw"), SYMBOL, TRAIN_START, TRAIN_END)
    train_fm = build_feature_matrix(
        train_trades, bar_seconds=1.0, label_horizon_bars=300, label_threshold_bps=10.0
    )
    print(f"Train: {len(train_trades):,} ticks → {len(train_fm):,} bars")

    model = Distinguisher(
        feature_cols=FEATURE_COLS, label_col="label_300", n_pairwise=10, max_iter=500
    )
    model.fit(train_fm)

    print("\n=== TEST (Dec 30) — predicting probabilities ===")
    test_trades = load_trades_range(Path("data/raw"), SYMBOL, TEST_DATE, TEST_DATE)
    test_fm = build_feature_matrix(
        test_trades, bar_seconds=1.0, label_horizon_bars=300, label_threshold_bps=10.0
    )
    print(f"Test: {len(test_fm):,} bars")

    proba = model.predict_proba(test_fm)
    classes = model.classes_.tolist()
    proba_up = proba[:, classes.index(1)]
    proba_down = proba[:, classes.index(-1)]

    print(f"\nσ stats — mean={float(np.mean(np.abs(proba_up - proba_down))):.4f}, "
          f"max={float(np.max(np.abs(proba_up - proba_down))):.4f}, "
          f"p99={float(np.quantile(np.abs(proba_up - proba_down), 0.99)):.4f}")

    print("\n=== LEVERAGE CONFIGURATIONS ===\n")
    print(f"{'Config':22s}  {'Trades':>6}  {'Win%':>6}  {'Return':>8}  "
          f"{'Max DD':>7}  {'Final $':>9}  {'Sharpe':>7}  {'LIQ':>4}")
    print("-" * 100)

    results = []
    for cfg in CONFIGS:
        r = run_one_config(test_fm, proba_up, proba_down, cfg)
        results.append(r)
        print(
            f"{r['name']:22s}  {r['trades']:>6}  {r['win_rate']*100:>5.1f}%  "
            f"{r['total_return_pct']*100:>+7.3f}%  {r['max_dd_pct']*100:>6.2f}%  "
            f"{r['final_equity']:>9.3f}  {r['sharpe_ann']:>7.2f}  {r['n_liquidations']:>4}"
        )

    print("\n=== INTERPRETATION ===\n")
    baseline = results[0]["total_return_pct"]
    for r in results[1:]:
        delta_pp = (r["total_return_pct"] - baseline) * 100
        marker = "✓" if r["total_return_pct"] > baseline and r["n_liquidations"] == 0 else "✗"
        print(
            f"{marker} {r['name']}: "
            f"return {r['total_return_pct']*100:+.3f}% vs baseline {baseline*100:+.3f}% "
            f"(Δ {delta_pp:+.3f} pp), liquidations: {r['n_liquidations']}, "
            f"final ${r['final_equity']:.3f}"
        )


if __name__ == "__main__":
    main()
