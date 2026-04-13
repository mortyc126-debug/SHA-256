"""Trade-flow features.

All functions accept a polars DataFrame with at least columns:
    ts: datetime[UTC], side: str ("Buy"/"Sell"), price: f64, size: f64

and return either an aggregated bar frame or the same frame with new columns.
"""

from __future__ import annotations

import polars as pl


def aggregate_trades_to_bars(
    trades: pl.DataFrame,
    bar_seconds: float = 1.0,
) -> pl.DataFrame:
    """Aggregate tick trades into fixed-width time bars.

    Output columns:
        ts_bar            — left-closed bar timestamp
        open, high, low, close, vwap — price stats
        volume            — total size
        buy_volume, sell_volume — split by aggressor side
        trade_count       — number of ticks in the bar
    """
    if trades.is_empty():
        return trades.with_columns(pl.lit(None).alias("_placeholder")).drop("_placeholder")

    interval = f"{int(bar_seconds * 1000)}ms"

    return (
        trades.sort("ts")
        .group_by_dynamic("ts", every=interval, closed="left", label="left")
        .agg(
            pl.col("price").first().alias("open"),
            pl.col("price").max().alias("high"),
            pl.col("price").min().alias("low"),
            pl.col("price").last().alias("close"),
            (
                (pl.col("price") * pl.col("size")).sum() / pl.col("size").sum()
            ).alias("vwap"),
            pl.col("size").sum().alias("volume"),
            pl.col("size").filter(pl.col("side") == "Buy").sum().alias("buy_volume"),
            pl.col("size").filter(pl.col("side") == "Sell").sum().alias("sell_volume"),
            pl.len().alias("trade_count"),
        )
        .rename({"ts": "ts_bar"})
    )


def flow_imbalance(bars: pl.DataFrame) -> pl.DataFrame:
    """Per-bar buy/sell imbalance in [-1, +1].

    Positive = taker-buy dominated; negative = taker-sell.
    Adds column `flow_imbalance`.
    """
    if "buy_volume" not in bars.columns or "sell_volume" not in bars.columns:
        raise ValueError("bars must have buy_volume and sell_volume columns")

    return bars.with_columns(
        pl.when(pl.col("buy_volume") + pl.col("sell_volume") > 0)
        .then(
            (pl.col("buy_volume") - pl.col("sell_volume"))
            / (pl.col("buy_volume") + pl.col("sell_volume"))
        )
        .otherwise(0.0)
        .alias("flow_imbalance")
    )


def cumulative_delta(bars: pl.DataFrame, window_bars: int | None = None) -> pl.DataFrame:
    """Rolling cumulative delta of (buy_volume - sell_volume).

    If window_bars is None, it accumulates over the whole series.
    Adds column `cum_delta` (or `cum_delta_w{N}` if windowed).
    """
    delta = pl.col("buy_volume") - pl.col("sell_volume")
    if window_bars is None:
        return bars.with_columns(delta.cum_sum().alias("cum_delta"))
    return bars.with_columns(
        delta.rolling_sum(window_size=window_bars, min_samples=1).alias(
            f"cum_delta_w{window_bars}"
        )
    )


def trade_rate(bars: pl.DataFrame) -> pl.DataFrame:
    """Per-second trade frequency. Assumes uniform bar widths.

    Adds column `trade_rate` (trades per second in that bar).
    """
    if "trade_count" not in bars.columns:
        raise ValueError("bars must have trade_count column")
    # We infer bar width from the timestamp difference; fall back to 1s.
    if bars.height >= 2:
        dt = (bars["ts_bar"][1] - bars["ts_bar"][0]).total_seconds()
        if dt <= 0:
            dt = 1.0
    else:
        dt = 1.0
    return bars.with_columns((pl.col("trade_count") / dt).alias("trade_rate"))


def vwap(bars: pl.DataFrame, window_bars: int) -> pl.DataFrame:
    """Rolling VWAP over `window_bars` bars.

    Adds column `vwap_w{N}`.
    """
    if "vwap" not in bars.columns or "volume" not in bars.columns:
        raise ValueError("bars must have vwap and volume columns")

    num = (pl.col("vwap") * pl.col("volume")).rolling_sum(
        window_size=window_bars, min_samples=1
    )
    den = pl.col("volume").rolling_sum(window_size=window_bars, min_samples=1)
    return bars.with_columns(
        pl.when(den > 0).then(num / den).otherwise(pl.col("vwap")).alias(f"vwap_w{window_bars}")
    )


__all__ = [
    "aggregate_trades_to_bars",
    "cumulative_delta",
    "flow_imbalance",
    "trade_rate",
    "vwap",
]
