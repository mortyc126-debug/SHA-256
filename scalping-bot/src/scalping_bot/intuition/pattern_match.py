"""Pattern-matching predictor — k-NN search over recent chart windows.

Conceptual model: at any moment, the chart's future is a *distribution*
of possible paths. As we observe more of the recent past, that
distribution narrows. We approximate it by finding the K most similar
windows in our recent history and looking at what happened after each.

Procedure for each new bar:
  1. Take last `window_bars` bars, convert to a feature vector
     (normalized log-returns + volume z-scores).
  2. Search the rolling library of past windows for K nearest by
     euclidean distance.
  3. For each match, look up its actual next-`horizon_bars` return.
  4. Mean of those returns → predicted direction.
     Std → uncertainty. High mean, low std → high conviction.

The library is rolling: we drop windows older than `library_age_bars`.
This respects the user's principle that yesterday's regime is gone.

This is k-NN regression on z-scored time-series motifs. Mathematically
simple, computationally cheap (numpy), conceptually powerful but not
a magic bullet. See test file for empirical limitations.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from scalping_bot.live.bar_builder import OneSecondBar


@dataclass(frozen=True)
class PatternPrediction:
    """k-NN prediction of next-N-bar return distribution."""

    n_matches: int
    mean_return_bps: float
    std_return_bps: float
    direction: int  # -1, 0, +1
    confidence: float  # [0, 1]
    """confidence = |mean| / (|mean| + std + epsilon). High mean, low std → 1."""


def _window_to_vector(bars: Sequence[OneSecondBar]) -> np.ndarray:
    """Convert a window of bars into a feature vector for similarity search.

    Features (concatenated, all z-scored or normalized):
      * log-returns of close (window-1 values)
      * z-scores of volume (window values)
    Returns a flat 1-D array.
    """
    closes = np.array([b.close for b in bars], dtype=np.float64)
    vols = np.array([b.volume for b in bars], dtype=np.float64)
    if len(closes) < 2 or np.any(closes <= 0):
        return np.zeros(2 * len(bars) - 1)

    # log-returns
    log_ret = np.diff(np.log(closes))
    # Volume z-scores within window
    vol_mean = vols.mean()
    vol_std = vols.std()
    vol_z = (vols - vol_mean) / vol_std if vol_std > 0 else np.zeros_like(vols)

    return np.concatenate([log_ret, vol_z])


@dataclass
class _LibraryEntry:
    """One historical window + its observed future."""

    vector: np.ndarray
    future_return_bps: float
    age_at_capture: int  # for rolling expiry


class PatternMatcher:
    """k-NN time-series predictor over a rolling library of recent windows."""

    def __init__(
        self,
        window_bars: int = 60,
        horizon_bars: int = 60,
        library_capacity: int = 14_400,
        library_age_bars: int = 14_400,  # 4 hours of 1s bars
        k: int = 20,
    ) -> None:
        if window_bars < 5:
            raise ValueError(f"window_bars must be >= 5, got {window_bars}")
        if horizon_bars < 1:
            raise ValueError(f"horizon_bars must be >= 1, got {horizon_bars}")
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        self.window_bars = window_bars
        self.horizon_bars = horizon_bars
        self.library_age_bars = library_age_bars
        self.k = k
        self._library: deque[_LibraryEntry] = deque(maxlen=library_capacity)
        # Pending entries: vector captured but future not yet known
        self._pending: deque[tuple[np.ndarray, int]] = deque()
        self._n_seen: int = 0
        # Cache: stacked library matrix and futures, invalidated on any change
        self._lib_dirty: bool = True
        self._lib_matrix: np.ndarray | None = None
        self._lib_futures: np.ndarray | None = None

    def observe(self, recent_bars: Sequence[OneSecondBar]) -> None:
        """Call once per new bar with the most recent window of bars.

        Captures the current window for future addition to the library
        once `horizon_bars` has elapsed and the future return is observable.
        """
        self._n_seen += 1

        # Promote pending → library when their future is known
        while self._pending and (self._n_seen - self._pending[0][1]) >= self.horizon_bars:
            vec, capture_idx = self._pending.popleft()
            # The future bar is `horizon_bars` ahead of capture
            future_idx_relative = self._n_seen - capture_idx
            # The most recent bar is index -1; future was -future_idx_relative ago at capture
            entry_close = recent_bars[-(future_idx_relative + 1)].close
            now_close = recent_bars[-1].close
            # Wait — we need the close `horizon_bars` after the capture,
            # not the current close. But we capture each bar, so future
            # close is exactly `horizon_bars` bars after capture.
            if entry_close <= 0:
                continue
            future_return_bps = (now_close - entry_close) / entry_close * 10_000.0
            self._library.append(
                _LibraryEntry(
                    vector=vec,
                    future_return_bps=future_return_bps,
                    age_at_capture=capture_idx,
                )
            )
            self._lib_dirty = True

        # Drop old library entries (rolling window)
        while self._library and (self._n_seen - self._library[0].age_at_capture) > self.library_age_bars:
            self._library.popleft()
            self._lib_dirty = True

        # Capture this bar's window for later
        if len(recent_bars) >= self.window_bars:
            window = recent_bars[-self.window_bars :]
            vec = _window_to_vector(window)
            self._pending.append((vec, self._n_seen))

    def predict(self, recent_bars: Sequence[OneSecondBar]) -> PatternPrediction | None:
        """Return a prediction from k-NN over the library; None if not ready."""
        if len(self._library) < self.k or len(recent_bars) < self.window_bars:
            return None

        query = _window_to_vector(recent_bars[-self.window_bars :])
        if not np.any(query):
            return None

        # Rebuild cached matrix only when library has changed
        if self._lib_dirty or self._lib_matrix is None or self._lib_futures is None:
            self._lib_matrix = np.vstack([e.vector for e in self._library])
            self._lib_futures = np.array(
                [e.future_return_bps for e in self._library], dtype=np.float64
            )
            self._lib_dirty = False

        diffs = self._lib_matrix - query
        dists = np.linalg.norm(diffs, axis=1)
        if len(dists) <= self.k:
            top_idx = np.arange(len(dists))
        else:
            top_idx = np.argpartition(dists, self.k)[: self.k]

        futures = self._lib_futures[top_idx]
        mean = float(futures.mean())
        std = float(futures.std())
        eps = 0.5  # epsilon in bps
        direction = 0 if abs(mean) < eps else (1 if mean > 0 else -1)
        confidence = abs(mean) / (abs(mean) + std + eps)
        return PatternPrediction(
            n_matches=len(top_idx),
            mean_return_bps=mean,
            std_return_bps=std,
            direction=direction,
            confidence=float(confidence),
        )

    @property
    def library_size(self) -> int:
        return len(self._library)

    @property
    def pending_size(self) -> int:
        return len(self._pending)
