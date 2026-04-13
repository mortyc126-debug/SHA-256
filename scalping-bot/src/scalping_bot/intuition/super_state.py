"""Super-state engine — quantum-superposition-inspired pattern recognition.

Problem with k-NN pattern matching: O(library_size) per query. With a
library of 14k windows and 60k bars per day, that's ~10 minutes just
to score one day. Useless for live scalping where decisions must take
milliseconds.

Idea: don't enumerate all past windows. Compress history into K
archetypes (~12-20 typical chart "modes": trending up, choppy, etc).
Maintain a probability distribution over which archetype we're in
*right now*. Update probabilities incrementally on each new bar.

Per-bar cost: O(K), not O(N). For K=12 that's <0.1 ms.

The "superposition" metaphor: until enough evidence accumulates,
multiple archetypes have non-trivial probability. As more data
streams in, the distribution concentrates on one (decoheres).
We trade only when the distribution has collapsed enough that one
archetype dominates AND its historical future-return is meaningful.

Concretely, after warmup we:
  1. Run k-means on last `archetype_window` windows.
  2. For each archetype, compute mean future-return from training data.
  3. Each new bar: compute distance to each archetype, softmax → new
     probabilities, blend with previous (EMA).
  4. Predict = (state_probs @ archetype_returns) ± concentration.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans

from scalping_bot.live.bar_builder import OneSecondBar


def _window_to_vector(bars: Sequence[OneSecondBar]) -> np.ndarray:
    """Same encoding as PatternMatcher: log-returns + volume z-scores."""
    closes = np.array([b.close for b in bars], dtype=np.float64)
    vols = np.array([b.volume for b in bars], dtype=np.float64)
    if len(closes) < 2 or np.any(closes <= 0):
        return np.zeros(2 * len(bars) - 1)

    log_ret = np.diff(np.log(closes))
    vol_mean = vols.mean()
    vol_std = vols.std()
    vol_z = (vols - vol_mean) / vol_std if vol_std > 0 else np.zeros_like(vols)
    return np.concatenate([log_ret, vol_z])


@dataclass(frozen=True)
class SuperStatePrediction:
    """Probabilistic prediction from the superposition over archetypes."""

    expected_return_bps: float
    concentration: float  # [0, 1] — how collapsed is the superposition?
    dominant_archetype: int
    dominant_prob: float
    direction: int  # -1, 0, +1
    confidence: float  # combines magnitude + concentration


class SuperStateEngine:
    """Online superposition tracker over a fixed set of archetype windows.

    Lifecycle:
      1. Construct with desired n_archetypes, window_bars, etc.
      2. Call observe(bars) on each new bar. During warmup we collect
         (window, future_return) pairs.
      3. After `min_warmup_bars`, archetypes are fit via k-means.
      4. After fit, predict() returns SuperStatePrediction.
      5. observe(bars) keeps refreshing archetypes every
         `refit_interval_bars` to track regime shifts.
    """

    def __init__(
        self,
        n_archetypes: int = 12,
        window_bars: int = 60,
        horizon_bars: int = 60,
        min_warmup_bars: int = 3600,  # 1 hour
        refit_interval_bars: int = 1800,  # refit every 30 min
        ema_alpha: float = 0.30,
        softmax_temperature: float = 0.50,
        archetype_capacity: int = 7200,  # 2 hours of training pairs
        random_seed: int = 42,
    ) -> None:
        if n_archetypes < 2:
            raise ValueError(f"n_archetypes must be >= 2, got {n_archetypes}")
        if window_bars < 5:
            raise ValueError(f"window_bars must be >= 5, got {window_bars}")
        if not (0 < ema_alpha <= 1):
            raise ValueError(f"ema_alpha must be in (0, 1], got {ema_alpha}")
        if softmax_temperature <= 0:
            raise ValueError(f"softmax_temperature must be > 0, got {softmax_temperature}")

        self.n_archetypes = n_archetypes
        self.window_bars = window_bars
        self.horizon_bars = horizon_bars
        self.min_warmup_bars = min_warmup_bars
        self.refit_interval_bars = refit_interval_bars
        self.ema_alpha = ema_alpha
        self.softmax_temperature = softmax_temperature
        self.random_seed = random_seed

        self._training_pairs: deque[tuple[np.ndarray, float]] = deque(
            maxlen=archetype_capacity
        )
        self._pending: deque[tuple[np.ndarray, int]] = deque()
        self._n_seen: int = 0

        self._archetypes: np.ndarray | None = None  # (K, dim)
        self._archetype_returns: np.ndarray | None = None  # (K,)
        self._state_probs: np.ndarray | None = None  # (K,)
        self._last_fit_at: int = 0
        self._fitted: bool = False

    # --- Lifecycle ---------------------------------------------------------

    def observe(self, recent_bars: Sequence[OneSecondBar]) -> None:
        """Stream-update on a new bar. Captures training pair, refits if due."""
        self._n_seen += 1

        # Promote pending → training when their future is observable
        while self._pending and (self._n_seen - self._pending[0][1]) >= self.horizon_bars:
            vec, capture_idx = self._pending.popleft()
            future_offset = self._n_seen - capture_idx
            entry_close = recent_bars[-(future_offset + 1)].close
            now_close = recent_bars[-1].close
            if entry_close > 0:
                future_ret_bps = (now_close - entry_close) / entry_close * 10_000.0
                self._training_pairs.append((vec, future_ret_bps))

        # Capture new window
        if len(recent_bars) >= self.window_bars:
            vec = _window_to_vector(recent_bars[-self.window_bars :])
            if np.any(vec):
                self._pending.append((vec, self._n_seen))

        # Update state probabilities (only if fitted)
        if self._fitted and len(recent_bars) >= self.window_bars:
            current = _window_to_vector(recent_bars[-self.window_bars :])
            if np.any(current):
                self._update_state(current)

        # Maybe refit
        should_refit = (
            len(self._training_pairs) >= self.min_warmup_bars
            and (self._n_seen - self._last_fit_at) >= self.refit_interval_bars
        )
        if should_refit:
            self._refit_archetypes()

    def _refit_archetypes(self) -> None:
        if len(self._training_pairs) < self.n_archetypes * 2:
            return
        x_train = np.vstack([p[0] for p in self._training_pairs])
        y_train = np.array([p[1] for p in self._training_pairs], dtype=np.float64)

        n_clusters = min(self.n_archetypes, len(self._training_pairs) // 2)
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=self.random_seed,
            n_init=3,
        )
        labels = kmeans.fit_predict(x_train)

        archetype_returns = np.zeros(n_clusters)
        for k in range(n_clusters):
            mask = labels == k
            archetype_returns[k] = y_train[mask].mean() if mask.any() else 0.0

        self._archetypes = kmeans.cluster_centers_
        self._archetype_returns = archetype_returns
        # Initialize state_probs uniformly when we first fit; preserve on refit
        if self._state_probs is None or len(self._state_probs) != n_clusters:
            self._state_probs = np.full(n_clusters, 1.0 / n_clusters)
        self._fitted = True
        self._last_fit_at = self._n_seen

    def _update_state(self, current_vec: np.ndarray) -> None:
        assert self._archetypes is not None
        assert self._state_probs is not None
        # Distance to each archetype
        diffs = self._archetypes - current_vec
        dists = np.linalg.norm(diffs, axis=1)
        # Softmax with temperature
        scores = -dists / self.softmax_temperature
        scores -= scores.max()  # numerical stability
        exp = np.exp(scores)
        new_probs = exp / exp.sum()
        # EMA blend
        self._state_probs = (
            (1 - self.ema_alpha) * self._state_probs + self.ema_alpha * new_probs
        )
        # Renormalize against floating-point drift
        self._state_probs /= self._state_probs.sum()

    # --- Inference ---------------------------------------------------------

    def predict(self) -> SuperStatePrediction | None:
        """Return current prediction, or None if not yet fitted."""
        if not self._fitted or self._state_probs is None or self._archetype_returns is None:
            return None

        expected = float(self._state_probs @ self._archetype_returns)
        entropy = -float(np.sum(self._state_probs * np.log(self._state_probs + 1e-12)))
        max_entropy = float(np.log(len(self._state_probs)))
        concentration = (
            1.0 - entropy / max_entropy if max_entropy > 0 else 0.0
        )

        dominant_idx = int(np.argmax(self._state_probs))
        dominant_p = float(self._state_probs[dominant_idx])

        eps_bps = 0.5
        direction = 0 if abs(expected) < eps_bps else (1 if expected > 0 else -1)

        # Confidence = magnitude × concentration
        magnitude_score = min(1.0, abs(expected) / 5.0)  # 5 bps → 1.0
        confidence = magnitude_score * concentration

        return SuperStatePrediction(
            expected_return_bps=expected,
            concentration=concentration,
            dominant_archetype=dominant_idx,
            dominant_prob=dominant_p,
            direction=direction,
            confidence=confidence,
        )

    # --- Introspection -----------------------------------------------------

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def n_training_pairs(self) -> int:
        return len(self._training_pairs)

    @property
    def state_probs(self) -> np.ndarray | None:
        return None if self._state_probs is None else self._state_probs.copy()

    @property
    def archetype_returns(self) -> np.ndarray | None:
        return None if self._archetype_returns is None else self._archetype_returns.copy()
