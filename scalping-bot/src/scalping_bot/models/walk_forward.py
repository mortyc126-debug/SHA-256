"""Time-series cross-validation (walk-forward).

Unlike k-fold, walk-forward respects time ordering: training data is
always older than validation data. Prevents look-ahead leakage which
is the #1 killer of trading-strategy backtests (research notes §3).

Parameters:
    n_splits : number of folds
    embargo  : number of rows between train end and val start,
               to prevent leakage from label-horizon overlap

Layout of a 3-split, embargo=0 run on 100 rows:

    fold 0:  train [0..25)   val [25..50)
    fold 1:  train [0..50)   val [50..75)
    fold 2:  train [0..75)   val [75..100)
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class WalkForwardSplit:
    """A single time-ordered train/val split expressed as row index ranges."""

    fold: int
    train_start: int
    train_end: int
    val_start: int
    val_end: int

    def __post_init__(self) -> None:
        if not (self.train_start < self.train_end <= self.val_start < self.val_end):
            raise ValueError(
                f"invalid split: train=[{self.train_start},{self.train_end}) "
                f"val=[{self.val_start},{self.val_end})"
            )


def walk_forward_splits(
    n_rows: int,
    n_splits: int = 4,
    embargo: int = 0,
    min_train_rows: int = 1,
) -> Iterator[WalkForwardSplit]:
    """Yield expanding-window walk-forward splits over `n_rows`.

    Validation windows are of equal size and non-overlapping, placed at
    the end of the series. Training window grows with each fold.
    """
    if n_rows <= 1:
        return
    if n_splits < 1:
        raise ValueError(f"n_splits must be >= 1, got {n_splits}")
    if embargo < 0:
        raise ValueError(f"embargo must be >= 0, got {embargo}")

    # Reserve the last `val_block * n_splits` rows for validation
    val_block = n_rows // (n_splits + 1)
    if val_block < 1:
        raise ValueError(
            f"n_rows={n_rows} too small for n_splits={n_splits}"
        )

    for fold in range(n_splits):
        val_start = n_rows - (n_splits - fold) * val_block
        val_end = val_start + val_block

        train_end = max(min_train_rows, val_start - embargo)
        train_start = 0

        if train_end - train_start < min_train_rows:
            # Skip this split if not enough training data
            continue

        yield WalkForwardSplit(
            fold=fold,
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
        )
