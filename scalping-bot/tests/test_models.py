"""Tests for Distinguisher, walk-forward splits, and metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from scalping_bot.models import (
    Distinguisher,
    binary_auc,
    confusion_counts,
    directional_metrics,
    walk_forward_splits,
)
from scalping_bot.models.walk_forward import WalkForwardSplit

T0 = datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC)


def _synth_features(n: int = 500, seed: int = 0) -> pl.DataFrame:
    """Features with a planted linear signal for `label`."""
    rng = np.random.default_rng(seed)
    f1 = rng.standard_normal(n)
    f2 = rng.standard_normal(n)
    f3 = rng.standard_normal(n)
    # Target roughly follows sign(f1 + 0.5*f2 + noise)
    score = f1 + 0.5 * f2 + 0.2 * rng.standard_normal(n)
    label = np.where(score > 0.5, 1, np.where(score < -0.5, -1, 0)).astype(np.int8)
    return pl.DataFrame(
        {
            "ts_bar": [T0 + timedelta(seconds=i) for i in range(n)],
            "f1": f1,
            "f2": f2,
            "f3": f3,
            "label": label,
        }
    )


class TestWalkForwardSplit:
    def test_valid_split(self) -> None:
        s = WalkForwardSplit(fold=0, train_start=0, train_end=50, val_start=50, val_end=100)
        assert s.fold == 0

    def test_invalid_split_raises(self) -> None:
        with pytest.raises(ValueError):
            WalkForwardSplit(fold=0, train_start=0, train_end=100, val_start=50, val_end=80)
        with pytest.raises(ValueError):
            WalkForwardSplit(fold=0, train_start=50, train_end=50, val_start=50, val_end=100)

    def test_generates_expected_folds(self) -> None:
        splits = list(walk_forward_splits(n_rows=100, n_splits=4))
        assert len(splits) == 4
        assert splits[0].val_start < splits[1].val_start
        # Training windows grow
        for i in range(1, len(splits)):
            assert splits[i].train_end >= splits[i - 1].train_end

    def test_no_splits_when_too_small(self) -> None:
        assert list(walk_forward_splits(n_rows=1, n_splits=3)) == []

    def test_rejects_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            list(walk_forward_splits(n_rows=100, n_splits=0))
        with pytest.raises(ValueError):
            list(walk_forward_splits(n_rows=100, n_splits=3, embargo=-1))
        with pytest.raises(ValueError):
            list(walk_forward_splits(n_rows=10, n_splits=100))

    def test_embargo_inserts_gap(self) -> None:
        splits = list(walk_forward_splits(n_rows=100, n_splits=3, embargo=5))
        for s in splits:
            assert s.val_start - s.train_end >= 5


class TestMetrics:
    def test_binary_auc_basic(self) -> None:
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.2, 0.8, 0.9])
        assert binary_auc(y, score) == 1.0

    def test_binary_auc_one_class_returns_nan(self) -> None:
        y = np.array([1, 1, 1])
        score = np.array([0.1, 0.5, 0.9])
        assert np.isnan(binary_auc(y, score))

    def test_confusion_counts(self) -> None:
        y_true = np.array([1, -1, 0, 1, 1])
        y_pred = np.array([1, 1, 0, -1, 1])
        c = confusion_counts(y_true, y_pred)
        assert c[(1, 1)] == 2
        assert c[(-1, 1)] == 1
        assert c[(0, 0)] == 1
        assert c[(1, -1)] == 1

    def test_directional_metrics_no_signal(self) -> None:
        y = np.array([1, -1, 0, 1])
        pu = np.array([0.3, 0.2, 0.3, 0.3])
        pd = np.array([0.3, 0.4, 0.3, 0.3])
        m = directional_metrics(y, pu, pd, enter_threshold=0.9)
        assert m.n_signals == 0
        assert m.coverage == 0.0

    def test_directional_metrics_perfect(self) -> None:
        y = np.array([1, -1, 1, -1])
        pu = np.array([0.9, 0.1, 0.9, 0.1])
        pd = np.array([0.05, 0.9, 0.05, 0.9])
        m = directional_metrics(y, pu, pd, enter_threshold=0.5)
        assert m.n_signals == 4
        assert m.directional_accuracy == 1.0
        assert m.precision_up == 1.0
        assert m.precision_down == 1.0

    def test_directional_metrics_mixed(self) -> None:
        y = np.array([1, 1, -1, -1, 0])
        pu = np.array([0.9, 0.6, 0.05, 0.1, 0.3])
        pd = np.array([0.05, 0.2, 0.9, 0.6, 0.3])
        m = directional_metrics(y, pu, pd, enter_threshold=0.55)
        assert m.n_signals == 4
        # up signals rows 0, 1 both right → precision_up = 1
        assert m.precision_up == 1.0
        assert m.precision_down == 1.0


class TestDistinguisher:
    def test_fit_requires_features(self) -> None:
        with pytest.raises(ValueError, match="feature_cols"):
            Distinguisher(feature_cols=[], label_col="label")

    def test_fit_missing_label_raises(self) -> None:
        df = _synth_features().drop("label")
        d = Distinguisher(feature_cols=["f1", "f2"], label_col="label")
        with pytest.raises(ValueError, match="label"):
            d.fit(df)

    def test_fit_missing_feature_raises(self) -> None:
        df = _synth_features()
        d = Distinguisher(feature_cols=["f1", "nonexistent"], label_col="label")
        with pytest.raises(ValueError, match="features missing"):
            d.fit(df)

    def test_predict_before_fit_raises(self) -> None:
        df = _synth_features()
        d = Distinguisher(feature_cols=["f1", "f2"], label_col="label")
        with pytest.raises(RuntimeError, match="fit"):
            d.predict_proba(df)

    def test_fit_and_predict_shapes(self) -> None:
        df = _synth_features(500)
        d = Distinguisher(
            feature_cols=["f1", "f2", "f3"],
            label_col="label",
            n_pairwise=4,
            max_iter=300,
        )
        d.fit(df)
        proba = d.predict_proba(df)
        assert proba.shape == (500, len(d.classes_))
        # Probabilities sum to 1 per row
        row_sums = proba.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=1e-6)

    def test_learns_planted_signal(self) -> None:
        """AUC should be clearly > 0.5 on synthetic data with planted signal."""
        df = _synth_features(2000)
        train = df[:1500]
        val = df[1500:]
        d = Distinguisher(
            feature_cols=["f1", "f2", "f3"],
            label_col="label",
            n_pairwise=5,
            max_iter=500,
        )
        d.fit(train)
        proba = d.predict_proba(val)
        classes = d.classes_.tolist()
        proba_up = proba[:, classes.index(1)]
        proba_down = proba[:, classes.index(-1)]

        y_val = val["label"].to_numpy()
        m = directional_metrics(y_val, proba_up, proba_down, enter_threshold=0.4)
        # Should be clearly above random
        assert m.auc_up_vs_rest > 0.7
        assert m.auc_down_vs_rest > 0.7

    def test_pairwise_specs_attached(self) -> None:
        df = _synth_features(500)
        d = Distinguisher(
            feature_cols=["f1", "f2", "f3"],
            label_col="label",
            n_pairwise=3,
        )
        d.fit(df)
        assert len(d.pairwise_specs) <= 3

    def test_coefs_returned_per_class(self) -> None:
        df = _synth_features(300)
        d = Distinguisher(feature_cols=["f1", "f2"], label_col="label", n_pairwise=0)
        d.fit(df)
        coefs = d.coefs_()
        assert len(coefs) == len(d.classes_)
        for vec in coefs.values():
            assert vec.shape[0] == len(d._fit.feature_cols)  # type: ignore[union-attr]
