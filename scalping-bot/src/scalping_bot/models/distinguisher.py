"""The Distinguisher: L1 logistic regression + top-k pairwise AND features.

Pattern ported from SHA-256 methodology v4.1 (§128-129):
  score(x) = Σ phi_i · x_i  +  Σ w_j · bit_j(x)
where `bit_j(x)` is a binary AND condition on a pair of features. The
pairs are selected by absolute correlation with the target on the
training set.

We wrap sklearn's LogisticRegression with standardization. We use
one-vs-rest classification with three binary heads (up, down, flat),
matching how we'll consume the scores at trade time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scalping_bot.features.pairwise import (
    PairwiseSpec,
    pairwise_and_features,
    top_k_pairs_by_correlation,
)


@dataclass
class DistinguisherFit:
    """Trained state: scaler, logistic weights, and the pairwise specs."""

    scaler: StandardScaler
    model: LogisticRegression
    pairwise_specs: list[PairwiseSpec] = field(default_factory=list)
    feature_cols: list[str] = field(default_factory=list)
    classes: np.ndarray = field(default_factory=lambda: np.array([]))


class Distinguisher:
    """Linear + pairwise classifier over a bar-level feature frame.

    Usage:
        d = Distinguisher(feature_cols=[...], label_col='label_30')
        d.fit(train_df)
        proba = d.predict_proba(val_df)
    """

    def __init__(
        self,
        feature_cols: list[str],
        label_col: str = "label_30",
        n_pairwise: int = 10,
        pairwise_q_high: float = 0.90,
        pairwise_q_low: float = 0.10,
        l1_c: float = 1.0,
        max_iter: int = 1000,
        random_state: int = 42,
    ) -> None:
        if not feature_cols:
            raise ValueError("feature_cols must be non-empty")
        self.feature_cols = list(feature_cols)
        self.label_col = label_col
        self.n_pairwise = n_pairwise
        self.pairwise_q_high = pairwise_q_high
        self.pairwise_q_low = pairwise_q_low
        self.l1_c = l1_c
        self.max_iter = max_iter
        self.random_state = random_state
        self._fit: DistinguisherFit | None = None

    # --- Fit / predict ------------------------------------------------------

    def fit(self, train: pl.DataFrame) -> DistinguisherFit:
        """Train on a DataFrame with label column and self.feature_cols."""
        if self.label_col not in train.columns:
            raise ValueError(f"label column {self.label_col!r} missing from train")
        missing = [c for c in self.feature_cols if c not in train.columns]
        if missing:
            raise ValueError(f"features missing from train: {missing}")

        # Select top-k pairwise specs on training data
        specs = top_k_pairs_by_correlation(
            train,
            feature_cols=self.feature_cols,
            target_col=self.label_col,
            k=self.n_pairwise,
            q_high=self.pairwise_q_high,
            q_low=self.pairwise_q_low,
        )

        enriched = pairwise_and_features(train, specs)
        all_cols = [*self.feature_cols, *(s.name for s in specs)]

        x = enriched.select(all_cols).to_numpy()
        y = enriched[self.label_col].to_numpy()

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)

        # sklearn 1.8+: use l1_ratio (1.0 = pure L1) instead of penalty="l1"
        model = LogisticRegression(
            l1_ratio=1.0,
            solver="saga",
            C=self.l1_c,
            max_iter=self.max_iter,
            random_state=self.random_state,
        )
        model.fit(x_scaled, y)

        fit_state = DistinguisherFit(
            scaler=scaler,
            model=model,
            pairwise_specs=specs,
            feature_cols=all_cols,
            classes=model.classes_,
        )
        self._fit = fit_state
        return fit_state

    def predict_proba(self, df: pl.DataFrame) -> np.ndarray:
        """Return class probabilities in the order of `classes_`.

        Columns follow sklearn's ordering (usually [-1, 0, 1]).
        """
        if self._fit is None:
            raise RuntimeError("call fit() before predict_proba()")

        enriched = pairwise_and_features(df, self._fit.pairwise_specs)
        x = enriched.select(self._fit.feature_cols).to_numpy()
        x_scaled = self._fit.scaler.transform(x)
        proba: np.ndarray = self._fit.model.predict_proba(x_scaled)
        return proba

    def predict(self, df: pl.DataFrame) -> np.ndarray:
        """Argmax class prediction."""
        proba = self.predict_proba(df)
        if self._fit is None:
            raise RuntimeError("not fit")
        result: np.ndarray = self._fit.classes[proba.argmax(axis=1)]
        return result

    # --- Convenience accessors ---------------------------------------------

    @property
    def classes_(self) -> np.ndarray:
        if self._fit is None:
            raise RuntimeError("not fit")
        return self._fit.classes

    @property
    def pairwise_specs(self) -> list[PairwiseSpec]:
        if self._fit is None:
            return []
        return list(self._fit.pairwise_specs)

    def coefs_(self) -> dict[str, np.ndarray]:
        """Per-class coefficients as a dict for logging and inspection."""
        if self._fit is None:
            raise RuntimeError("not fit")
        coefs = self._fit.model.coef_
        return {
            str(cls): coefs[i] for i, cls in enumerate(self._fit.classes)
        }
