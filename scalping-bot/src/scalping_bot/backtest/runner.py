"""Walk-forward backtest runner.

For each fold:
  1. Train Distinguisher on the train slice.
  2. Predict probabilities on the val slice.
  3. Run ThresholdStrategy through BacktestEngine bar-by-bar on val.
  4. Collect resulting trades.

Final aggregate is over all folds' trades concatenated.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from scalping_bot.backtest.engine import BacktestEngine, CompletedTrade, FeeModel
from scalping_bot.backtest.metrics import BacktestSummary, summarize_trades
from scalping_bot.backtest.strategy import StrategyConfig, ThresholdStrategy
from scalping_bot.models import Distinguisher, walk_forward_splits


@dataclass
class FoldResult:
    fold: int
    n_trades: int
    summary: BacktestSummary


def run_walk_forward_backtest(
    feature_matrix: pl.DataFrame,
    feature_cols: list[str],
    label_col: str,
    *,
    n_splits: int = 4,
    n_pairwise: int = 10,
    starting_capital_usd: float = 100.0,
    leverage: float = 3.0,
    strategy_config: StrategyConfig | None = None,
    fee_model: FeeModel | None = None,
    bar_seconds: float = 1.0,
    price_col: str = "close",
    use_taker: bool = True,
    distinguisher_max_iter: int = 500,
) -> tuple[list[FoldResult], BacktestSummary]:
    """Train and backtest walk-forward; return per-fold results + aggregate."""
    if "ts_bar" not in feature_matrix.columns:
        raise ValueError("feature_matrix must have ts_bar column")
    if price_col not in feature_matrix.columns:
        raise ValueError(f"feature_matrix must have {price_col!r} column")

    cfg = strategy_config or StrategyConfig()
    fees = fee_model or FeeModel()
    fold_results: list[FoldResult] = []
    all_trades: list[CompletedTrade] = []

    for split in walk_forward_splits(n_rows=len(feature_matrix), n_splits=n_splits):
        train_df = feature_matrix[split.train_start : split.train_end]
        val_df = feature_matrix[split.val_start : split.val_end]

        d = Distinguisher(
            feature_cols=feature_cols,
            label_col=label_col,
            n_pairwise=n_pairwise,
            max_iter=distinguisher_max_iter,
        )
        d.fit(train_df)

        proba = d.predict_proba(val_df)
        classes = d.classes_.tolist()
        if 1 not in classes or -1 not in classes:
            continue
        idx_up = classes.index(1)
        idx_down = classes.index(-1)
        proba_up = proba[:, idx_up]
        proba_down = proba[:, idx_down]

        prices = val_df[price_col].to_numpy()
        timestamps = val_df["ts_bar"].to_list()

        engine = BacktestEngine(
            starting_capital_usd=starting_capital_usd,
            leverage=leverage,
            fee_model=fees,
            use_taker=use_taker,
        )
        strategy = ThresholdStrategy(config=cfg)

        for ts, price, pu, pd in zip(timestamps, prices, proba_up, proba_down, strict=True):
            engine.mark_to_market(float(price))
            strategy.step(engine, ts, float(price), float(pu), float(pd))

        # Force close at end
        if engine.position is not None and len(prices) > 0:
            engine.close_position(timestamps[-1], float(prices[-1]), "fold_end")

        fold_summary = summarize_trades(
            engine.trades,
            starting_capital_usd=starting_capital_usd,
            bar_seconds=bar_seconds,
        )
        fold_results.append(
            FoldResult(
                fold=split.fold,
                n_trades=fold_summary.n_trades,
                summary=fold_summary,
            )
        )
        all_trades.extend(engine.trades)

    aggregate = summarize_trades(
        all_trades,
        starting_capital_usd=starting_capital_usd,
        bar_seconds=bar_seconds,
    )
    return fold_results, aggregate
