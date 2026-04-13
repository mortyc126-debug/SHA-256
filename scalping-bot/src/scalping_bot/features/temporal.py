"""Time-of-day encoding.

Research notes §3 documents that OBI predictive power depends on the
hour (strong at ~03 UTC, weak at ~15 UTC). We need hour and minute
features in a continuous form the classifier can use: sin/cos of the
angular position, not one-hot dummies.
"""

from __future__ import annotations

import math

import polars as pl


def hour_of_day_features(bars: pl.DataFrame, ts_col: str = "ts_bar") -> pl.DataFrame:
    """Add sin/cos of hour-of-day. Cycle length = 24 hours.

    Adds columns: hour_sin, hour_cos.
    """
    if ts_col not in bars.columns:
        raise ValueError(f"bars must have column {ts_col!r}")

    hour = pl.col(ts_col).dt.hour().cast(pl.Float64)
    angle = hour / 24.0 * (2 * math.pi)
    return bars.with_columns(
        angle.sin().alias("hour_sin"),
        angle.cos().alias("hour_cos"),
    )


def minute_of_hour_features(bars: pl.DataFrame, ts_col: str = "ts_bar") -> pl.DataFrame:
    """Add sin/cos of minute-of-hour. Cycle length = 60 minutes.

    Adds columns: minute_sin, minute_cos.
    """
    if ts_col not in bars.columns:
        raise ValueError(f"bars must have column {ts_col!r}")

    minute = pl.col(ts_col).dt.minute().cast(pl.Float64)
    angle = minute / 60.0 * (2 * math.pi)
    return bars.with_columns(
        angle.sin().alias("minute_sin"),
        angle.cos().alias("minute_cos"),
    )


__all__ = ["hour_of_day_features", "minute_of_hour_features"]
