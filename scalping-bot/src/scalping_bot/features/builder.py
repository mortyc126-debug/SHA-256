"""High-level feature matrix builder.

Reads Parquet from our data/raw layout, aggregates trades to time bars,
and stacks all feature modules into a single frame ready for training.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl

from scalping_bot.features.flow import (
    aggregate_trades_to_bars,
    cumulative_delta,
    flow_imbalance,
    trade_rate,
    vwap,
)
from scalping_bot.features.labels import label_direction
from scalping_bot.features.temporal import hour_of_day_features, minute_of_hour_features
from scalping_bot.features.volatility import realized_vol, trade_price_vol


def load_trades_range(
    data_dir: Path,
    symbol: str,
    start: date,
    end: date,
) -> pl.DataFrame:
    """Load all hourly trade Parquets for dates in [start, end] inclusive."""
    return _load_parquet_range(
        base=Path(data_dir) / "trades",
        symbol=symbol,
        start=start,
        end=end,
        sort_col="ts",
    )


def load_orderbook_snapshots_range(
    data_dir: Path,
    symbol: str,
    start: date,
    end: date,
) -> pl.DataFrame:
    """Load all orderbook snapshot Parquets for dates in [start, end] inclusive."""
    return _load_parquet_range(
        base=Path(data_dir) / "orderbook_snapshots",
        symbol=symbol,
        start=start,
        end=end,
        sort_col="ts",
    )


def _load_parquet_range(
    base: Path,
    symbol: str,
    start: date,
    end: date,
    sort_col: str,
) -> pl.DataFrame:
    if start > end:
        raise ValueError(f"start={start} must be <= end={end}")

    frames: list[pl.DataFrame] = []
    current = start
    while current <= end:
        date_dir = base / f"date={current.isoformat()}"
        if date_dir.is_dir():
            pattern = str(date_dir / f"{symbol}_*.parquet")
            df = pl.read_parquet(pattern)
            frames.append(df)
        current += timedelta(days=1)

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical_relaxed").sort(sort_col)


def build_feature_matrix(
    trades: pl.DataFrame,
    bar_seconds: float = 1.0,
    label_horizon_bars: int = 30,
    label_threshold_bps: float = 2.0,
    rv_windows: tuple[int, ...] = (60, 300),
    vwap_windows: tuple[int, ...] = (30, 300),
    cum_delta_windows: tuple[int, ...] = (30, 300),
) -> pl.DataFrame:
    """End-to-end: raw trades → feature matrix with target label.

    Defaults produce 1-second bars, 30-second forward horizon, 2 bps
    threshold for up/down classification. Windows are in bars, not
    seconds (so 60 with 1s bars = 60 seconds).

    The returned frame drops rows where the forward return is undefined
    (last `label_horizon_bars` rows) and any rows where any feature is
    null (typically the first ~max(window) rows).
    """
    if trades.is_empty():
        return trades

    bars = aggregate_trades_to_bars(trades, bar_seconds=bar_seconds)
    bars = flow_imbalance(bars)
    bars = trade_rate(bars)

    for w in rv_windows:
        bars = realized_vol(bars, window_bars=w)
    for w in vwap_windows:
        bars = vwap(bars, window_bars=w)
    for w in cum_delta_windows:
        bars = cumulative_delta(bars, window_bars=w)

    bars = trade_price_vol(bars, window_bars=max(rv_windows))
    bars = hour_of_day_features(bars)
    bars = minute_of_hour_features(bars)

    bars = label_direction(
        bars,
        horizon_bars=label_horizon_bars,
        threshold_bps=label_threshold_bps,
    )

    # Drop tail rows with undefined forward return, then drop any null
    # rows from early windows.
    return bars.drop_nulls().sort("ts_bar")


__all__ = ["build_feature_matrix", "load_trades_range"]
