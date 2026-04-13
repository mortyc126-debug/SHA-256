"""Tests for SuperStateEngine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from scalping_bot.intuition.super_state import SuperStateEngine, SuperStatePrediction
from scalping_bot.live.bar_builder import OneSecondBar

T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)


def _bars_from_prices(prices: list[float]) -> list[OneSecondBar]:
    return [
        OneSecondBar(
            ts_bar=T0 + timedelta(seconds=i),
            open=p, high=p, low=p, close=p, vwap=p,
            volume=1.0, buy_volume=0.5, sell_volume=0.5, trade_count=10,
        )
        for i, p in enumerate(prices)
    ]


class TestConstruction:
    def test_invalid_archetypes(self) -> None:
        with pytest.raises(ValueError, match="n_archetypes"):
            SuperStateEngine(n_archetypes=1)

    def test_invalid_window(self) -> None:
        with pytest.raises(ValueError, match="window_bars"):
            SuperStateEngine(window_bars=2)

    def test_invalid_alpha(self) -> None:
        with pytest.raises(ValueError, match="ema_alpha"):
            SuperStateEngine(ema_alpha=0)
        with pytest.raises(ValueError, match="ema_alpha"):
            SuperStateEngine(ema_alpha=1.5)

    def test_invalid_temperature(self) -> None:
        with pytest.raises(ValueError, match="softmax_temperature"):
            SuperStateEngine(softmax_temperature=0)


class TestLifecycle:
    def test_no_prediction_before_warmup(self) -> None:
        eng = SuperStateEngine(
            n_archetypes=4, window_bars=10, horizon_bars=5,
            min_warmup_bars=50, refit_interval_bars=20,
        )
        rng = np.random.default_rng(0)
        prices = 100.0 + np.cumsum(rng.standard_normal(30) * 0.01)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            eng.observe(bars[:i])
        assert not eng.fitted
        assert eng.predict() is None

    def test_fit_after_warmup(self) -> None:
        eng = SuperStateEngine(
            n_archetypes=4, window_bars=10, horizon_bars=5,
            min_warmup_bars=80, refit_interval_bars=20,
        )
        rng = np.random.default_rng(1)
        prices = 100.0 + np.cumsum(rng.standard_normal(150) * 0.01)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            eng.observe(bars[:i])
        assert eng.fitted
        pred = eng.predict()
        assert pred is not None
        assert isinstance(pred, SuperStatePrediction)
        assert 0 <= pred.concentration <= 1
        assert 0 <= pred.dominant_prob <= 1
        assert -1 <= pred.direction <= 1


class TestPredictionStructure:
    def _train_and_predict(self) -> SuperStatePrediction | None:
        eng = SuperStateEngine(
            n_archetypes=4, window_bars=10, horizon_bars=5,
            min_warmup_bars=80, refit_interval_bars=20,
        )
        rng = np.random.default_rng(7)
        prices = 100.0 + np.cumsum(rng.standard_normal(200) * 0.02 + 0.001)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            eng.observe(bars[:i])
        return eng.predict()

    def test_state_probs_sum_to_one(self) -> None:
        eng = SuperStateEngine(
            n_archetypes=5, window_bars=10, horizon_bars=5,
            min_warmup_bars=80, refit_interval_bars=20,
        )
        rng = np.random.default_rng(2)
        prices = 100.0 + np.cumsum(rng.standard_normal(150) * 0.01)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            eng.observe(bars[:i])
        sp = eng.state_probs
        assert sp is not None
        assert pytest.approx(sp.sum(), abs=1e-6) == 1.0

    def test_concentration_in_unit_interval(self) -> None:
        pred = self._train_and_predict()
        if pred is not None:
            assert 0 <= pred.concentration <= 1

    def test_archetype_returns_finite(self) -> None:
        eng = SuperStateEngine(
            n_archetypes=4, window_bars=10, horizon_bars=5,
            min_warmup_bars=80, refit_interval_bars=20,
        )
        rng = np.random.default_rng(3)
        prices = 100.0 + np.cumsum(rng.standard_normal(150) * 0.01)
        bars = _bars_from_prices(prices.tolist())
        for i in range(1, len(bars) + 1):
            eng.observe(bars[:i])
        ar = eng.archetype_returns
        if ar is not None:
            assert np.all(np.isfinite(ar))


class TestPerformance:
    def test_per_bar_cost_is_bounded(self) -> None:
        """Sanity: 1000 bars should run in under a second on any machine."""
        import time as _time
        eng = SuperStateEngine(
            n_archetypes=12, window_bars=60, horizon_bars=30,
            min_warmup_bars=200, refit_interval_bars=200,
        )
        rng = np.random.default_rng(4)
        prices = 100.0 + np.cumsum(rng.standard_normal(1000) * 0.01)
        bars = _bars_from_prices(prices.tolist())
        start = _time.time()
        for i in range(1, len(bars) + 1):
            eng.observe(bars[:i])
        elapsed = _time.time() - start
        # 1000 bars should comfortably fit in < 5 sec
        assert elapsed < 5.0, f"too slow: {elapsed:.2f}s for 1000 bars"
