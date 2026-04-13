"""Forward-return labels for supervised training.

Convention: label at time t answers "what happens in the next N bars?"
so the label at the last N bars of the series is NaN (no future data).
"""

from __future__ import annotations

import polars as pl


def forward_return(
    bars: pl.DataFrame,
    horizon_bars: int,
    price_col: str = "close",
) -> pl.DataFrame:
    """Add `fwd_return_{N}` column: pct change over next `horizon_bars` bars.

    fwd_return[t] = price[t + horizon] / price[t] - 1
    """
    if price_col not in bars.columns:
        raise ValueError(f"bars must have column {price_col!r}")
    if horizon_bars <= 0:
        raise ValueError(f"horizon_bars must be positive, got {horizon_bars}")

    future = pl.col(price_col).shift(-horizon_bars)
    return bars.with_columns(
        ((future / pl.col(price_col)) - 1.0).alias(f"fwd_return_{horizon_bars}")
    )


def label_direction(
    bars: pl.DataFrame,
    horizon_bars: int,
    threshold_bps: float = 2.0,
    price_col: str = "close",
) -> pl.DataFrame:
    """Add `label_{N}` column with three-way classification.

    +1 if fwd_return > +threshold_bps / 10000
    -1 if fwd_return < -threshold_bps / 10000
     0 otherwise (flat / noise)

    The last `horizon_bars` rows will have NaN return and are labelled 0
    (we'll drop them before training; see build_feature_matrix).
    """
    bars = forward_return(bars, horizon_bars=horizon_bars, price_col=price_col)

    ret_col = f"fwd_return_{horizon_bars}"
    threshold = threshold_bps / 10_000.0
    label_name = f"label_{horizon_bars}"

    return bars.with_columns(
        pl.when(pl.col(ret_col) > threshold)
        .then(1)
        .when(pl.col(ret_col) < -threshold)
        .then(-1)
        .otherwise(0)
        .cast(pl.Int8)
        .alias(label_name)
    )


__all__ = ["forward_return", "label_direction"]
