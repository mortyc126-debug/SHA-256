"""Volatility features — realized vol, price range, etc."""

from __future__ import annotations

import polars as pl


def realized_vol(bars: pl.DataFrame, window_bars: int, price_col: str = "close") -> pl.DataFrame:
    """Rolling realized volatility of log-returns over `window_bars`.

    Adds column `rv_w{N}`. Log-returns are computed from the given price
    column. NaN or non-positive prices are replaced with forward-fill of
    the previous valid price before computing returns.
    """
    if price_col not in bars.columns:
        raise ValueError(f"bars must have column {price_col!r}")

    logret = pl.col(price_col).log().diff()
    return bars.with_columns(
        logret.rolling_std(window_size=window_bars, min_samples=2).alias(
            f"rv_w{window_bars}"
        )
    )


def trade_price_vol(bars: pl.DataFrame, window_bars: int) -> pl.DataFrame:
    """Rolling std of (high - low) / close — a cheap intrabar range proxy.

    Adds column `price_range_w{N}`.
    """
    if not {"high", "low", "close"}.issubset(bars.columns):
        raise ValueError("bars must have high, low, close columns")

    span = (pl.col("high") - pl.col("low")) / pl.col("close")
    return bars.with_columns(
        span.rolling_mean(window_size=window_bars, min_samples=1).alias(
            f"price_range_w{window_bars}"
        )
    )


__all__ = ["realized_vol", "trade_price_vol"]
