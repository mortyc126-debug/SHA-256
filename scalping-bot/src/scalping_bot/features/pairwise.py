"""Pairwise AND features — Distinguisher v4.1 pattern from SHA-256 methodology.

Given a feature matrix, we want binary "both conditions met" features:
    bit_i = 1 if x_i > p90(x_i)  else 0
    bit_j = 1 if x_j < p10(x_j)  else 0
    feature_ij = bit_i AND bit_j  (possibly NOT the second too)

Then rank all such (i, j) pairs by correlation with the target label and
keep the top-k. This catches non-linear interactions that a plain linear
model can't.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import polars as pl


@dataclass(frozen=True)
class PairwiseSpec:
    """One AND-condition: `feat_a` op_a thresh_a AND `feat_b` op_b thresh_b."""

    feat_a: str
    op_a: str  # ">" or "<"
    thresh_a: float
    feat_b: str
    op_b: str
    thresh_b: float

    @property
    def name(self) -> str:
        return f"and__{self.feat_a}_{self.op_a}_{self.feat_b}_{self.op_b}"


def _binarize(col: pl.Expr, threshold: float, op: str) -> pl.Expr:
    if op == ">":
        return (col > threshold).cast(pl.Int8)
    if op == "<":
        return (col < threshold).cast(pl.Int8)
    raise ValueError(f"op must be '>' or '<', got {op!r}")


def _percentile(df: pl.DataFrame, col: str, q: float) -> float:
    val = df[col].quantile(q, interpolation="linear")
    if val is None:
        return 0.0
    return float(val)


def top_k_pairs_by_correlation(
    df: pl.DataFrame,
    feature_cols: Iterable[str],
    target_col: str,
    k: int = 10,
    q_high: float = 0.90,
    q_low: float = 0.10,
) -> list[PairwiseSpec]:
    """Select top-k AND pairs most correlated with the target.

    For each unordered pair (a, b) of feature_cols, tries four combinations
    of high/low thresholds and picks the one with the largest |corr|.
    Returns the global top-k across all pairs.
    """
    features = list(feature_cols)
    if len(features) < 2:
        return []

    # Precompute thresholds
    high = {c: _percentile(df, c, q_high) for c in features}
    low = {c: _percentile(df, c, q_low) for c in features}

    target = df[target_col].to_numpy()
    scored: list[tuple[float, PairwiseSpec]] = []

    for i, a in enumerate(features):
        a_high = df[a].to_numpy() > high[a]
        a_low = df[a].to_numpy() < low[a]
        for b in features[i + 1 :]:
            b_high = df[b].to_numpy() > high[b]
            b_low = df[b].to_numpy() < low[b]

            for op_a, mask_a, th_a in (
                (">", a_high, high[a]),
                ("<", a_low, low[a]),
            ):
                for op_b, mask_b, th_b in (
                    (">", b_high, high[b]),
                    ("<", b_low, low[b]),
                ):
                    joint = (mask_a & mask_b).astype(np.float64)
                    if joint.sum() < 10:
                        continue
                    # Correlation vs target
                    if joint.std() == 0 or np.std(target) == 0:
                        continue
                    corr = float(np.corrcoef(joint, target)[0, 1])
                    if not np.isfinite(corr):
                        continue
                    scored.append(
                        (
                            abs(corr),
                            PairwiseSpec(
                                feat_a=a,
                                op_a=op_a,
                                thresh_a=th_a,
                                feat_b=b,
                                op_b=op_b,
                                thresh_b=th_b,
                            ),
                        )
                    )

    scored.sort(key=lambda x: x[0], reverse=True)
    return [spec for _, spec in scored[:k]]


def pairwise_and_features(df: pl.DataFrame, specs: Iterable[PairwiseSpec]) -> pl.DataFrame:
    """Add one binary column per spec to `df`. Column name is `spec.name`."""
    exprs: list[pl.Expr] = []
    for spec in specs:
        a = _binarize(pl.col(spec.feat_a), spec.thresh_a, spec.op_a)
        b = _binarize(pl.col(spec.feat_b), spec.thresh_b, spec.op_b)
        exprs.append((a & b).cast(pl.Int8).alias(spec.name))
    if not exprs:
        return df
    return df.with_columns(exprs)


__all__ = [
    "PairwiseSpec",
    "pairwise_and_features",
    "top_k_pairs_by_correlation",
]
