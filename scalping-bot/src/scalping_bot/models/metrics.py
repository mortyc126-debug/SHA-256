"""Trading-relevant metrics.

AUC is fine as a "does the classifier learn anything?" sanity check.
But for trading we also want:
  - Precision at confidence threshold: "when we DO trade, how often right?"
  - Coverage: "what fraction of bars do we trade at that threshold?"
  - Directional accuracy: accuracy on the subset where label != 0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import roc_auc_score


def binary_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """AUC of a binary target using prediction scores. NaN if only one class."""
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def confusion_counts(
    y_true: np.ndarray, y_pred: np.ndarray
) -> dict[tuple[int, int], int]:
    """Counts keyed by (true, pred) for the 3-class label {-1, 0, +1}."""
    counts: dict[tuple[int, int], int] = {}
    for t, p in zip(y_true.tolist(), y_pred.tolist(), strict=True):
        key = (int(t), int(p))
        counts[key] = counts.get(key, 0) + 1
    return counts


@dataclass(frozen=True)
class DirectionalMetrics:
    """Metrics focused on directional (non-flat) predictions."""

    auc_up_vs_rest: float
    auc_down_vs_rest: float
    coverage: float  # fraction of rows where model predicts a direction
    directional_accuracy: float  # accuracy on those rows
    precision_up: float
    precision_down: float
    n_rows: int
    n_signals: int


def directional_metrics(
    y_true: np.ndarray,
    proba_up: np.ndarray,
    proba_down: np.ndarray,
    enter_threshold: float = 0.55,
) -> DirectionalMetrics:
    """Evaluate a trinary classifier for trading.

    Args:
        y_true:     Labels in {-1, 0, +1}.
        proba_up:   P(label == +1) from the model.
        proba_down: P(label == -1) from the model.
        enter_threshold: minimum probability to signal a trade.

    Returns:
        DirectionalMetrics with AUC (each direction vs rest),
        coverage, precision and directional accuracy.
    """
    y = np.asarray(y_true).astype(int)
    pu = np.asarray(proba_up, dtype=float)
    pd = np.asarray(proba_down, dtype=float)

    auc_up = binary_auc((y == 1).astype(int), pu)
    auc_down = binary_auc((y == -1).astype(int), pd)

    # Signal: whichever side has higher probability above threshold
    signal = np.zeros_like(y)
    up_mask = (pu >= enter_threshold) & (pu >= pd)
    down_mask = (pd >= enter_threshold) & (pd > pu)
    signal[up_mask] = 1
    signal[down_mask] = -1

    n_signals = int((signal != 0).sum())
    coverage = n_signals / len(y) if len(y) > 0 else 0.0

    if n_signals == 0:
        directional_acc = float("nan")
        prec_up = float("nan")
        prec_down = float("nan")
    else:
        correct = (signal == y) & (signal != 0)
        directional_acc = float(correct.sum()) / n_signals

        up_signals = signal == 1
        down_signals = signal == -1
        prec_up = (
            float(((y == 1) & up_signals).sum() / up_signals.sum())
            if up_signals.any()
            else float("nan")
        )
        prec_down = (
            float(((y == -1) & down_signals).sum() / down_signals.sum())
            if down_signals.any()
            else float("nan")
        )

    return DirectionalMetrics(
        auc_up_vs_rest=auc_up,
        auc_down_vs_rest=auc_down,
        coverage=coverage,
        directional_accuracy=directional_acc,
        precision_up=prec_up,
        precision_down=prec_down,
        n_rows=len(y),
        n_signals=n_signals,
    )
