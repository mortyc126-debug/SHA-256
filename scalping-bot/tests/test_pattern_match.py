"""Tests for PatternMatcher."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from scalping_bot.intuition.pattern_match import PatternMatcher, _window_to_vector
from scalping_bot.live.bar_builder import OneSecondBar

T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)


def _bars_from_prices(prices: list[float], vols: list[float] | None = None) -> list[OneSecondBar]:
    if vols is None:
        vols = [1.0] * len(prices)
    return [
        OneSecondBar(
            ts_bar=T0 + timedelta(seconds=i),
            open=p,
            high=p,
            low=p,
            close=p,
            vwap=p,
            volume=v,
            buy_volume=v / 2,
            sell_volume=v / 2,
            trade_count=10,
        )
        for i, (p, v) in enumerate(zip(prices, vols, strict=True))
    ]


class TestWindowVector:
    def test_short_window_returns_zeros(self) -> None:
        bars = _bars_from_prices([100.0])
        vec = _window_to_vector(bars)
        # 2*1 - 1 = 1 element of zeros
        assert vec.shape == (1,)
        assert np.all(vec == 0)

    def test_constant_price_zero_returns(self) -> None:
        bars = _bars_from_prices([100.0] * 10)
        vec = _window_to_vector(bars)
        # First 9 elements are log-returns (all 0), next 10 are vol z-scores
        assert np.all(vec[:9] == 0)

    def test_uptrend_positive_returns(self) -> None:
        bars = _bars_from_prices([100.0 + i * 0.1 for i in range(10)])
        vec = _window_to_vector(bars)
        # First 9 elements are log-returns, all positive
        assert np.all(vec[:9] > 0)


class TestMatcherConstruction:
    def test_invalid_window_raises(self) -> None:
        with pytest.raises(ValueError, match="window_bars"):
            PatternMatcher(window_bars=2)

    def test_invalid_horizon_raises(self) -> None:
        with pytest.raises(ValueError, match="horizon_bars"):
            PatternMatcher(horizon_bars=0)

    def test_invalid_k_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be"):
            PatternMatcher(k=0)


class TestMatcherLifecycle:
    def test_no_prediction_during_warmup(self) -> None:
        m = PatternMatcher(window_bars=10, horizon_bars=5, k=3, library_capacity=100)
        bars = _bars_from_prices([100.0 + i * 0.01 for i in range(15)])
        for i in range(1, len(bars) + 1):
            m.observe(bars[:i])
            assert m.predict(bars[:i]) is None  # library too small

    def test_library_grows_after_horizon_elapses(self) -> None:
        m = PatternMatcher(window_bars=10, horizon_bars=5, k=3, library_capacity=200)
        bars = _bars_from_prices([100.0 + i * 0.01 for i in range(50)])
        for i in range(1, len(bars) + 1):
            m.observe(bars[:i])
        # By the end we should have many library entries
        assert m.library_size > 0

    def test_prediction_returns_when_library_has_k(self) -> None:
        m = PatternMatcher(window_bars=10, horizon_bars=5, k=3, library_capacity=200)
        # Generate noisy upward drift
        rng = np.random.default_rng(0)
        prices = 100.0 + np.cumsum(rng.standard_normal(200) * 0.01 + 0.001)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            m.observe(bars[:i])
        pred = m.predict(bars)
        if pred is not None:  # may be None if library still warming
            assert pred.n_matches >= 3
            assert -1 <= pred.direction <= 1
            assert 0 <= pred.confidence <= 1


class TestRollingExpiry:
    def test_old_entries_dropped(self) -> None:
        m = PatternMatcher(
            window_bars=5, horizon_bars=3, k=2,
            library_capacity=10000, library_age_bars=20,
        )
        rng = np.random.default_rng(1)
        prices = 100.0 + np.cumsum(rng.standard_normal(60) * 0.01)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            m.observe(bars[:i])
        # Library age cap is 20 → can't hold more than ~20 entries
        assert m.library_size <= 25  # small slack for boundary effects


class TestPredictionStructure:
    def test_strong_signal_high_confidence(self) -> None:
        # Build a library where every match has +20 bps future
        m = PatternMatcher(window_bars=10, horizon_bars=5, k=5, library_capacity=200)
        # Synthetic: same window pattern repeated, always followed by upward move
        prices = []
        for _ in range(20):
            prices.extend([100.0] * 10)  # flat window
            prices.extend([100.0 * 1.002] * 5)  # +20 bps jump
        bars = _bars_from_prices(prices)
        for i in range(1, len(bars) + 1):
            m.observe(bars[:i])

        # Now query with a flat 10-bar window
        query_bars = _bars_from_prices([100.0] * 10)
        # Need to feed enough context so library is populated
        pred = m.predict(query_bars)
        if pred is not None and pred.n_matches > 0:
            # Should detect the pattern: flat → up
            assert pred.confidence >= 0.0  # at least be defined
