"""Tests for live paper-trading components."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from scalping_bot.backtest.engine import Side
from scalping_bot.backtest.strategy import StrategyConfig, ThresholdStrategy
from scalping_bot.live.bar_builder import LiveBarBuilder, OneSecondBar
from scalping_bot.live.feature_pipeline import LiveFeatureBuilder
from scalping_bot.live.model_io import load_model, save_model
from scalping_bot.live.paper_broker import PaperBroker
from scalping_bot.models import Distinguisher

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# --- LiveBarBuilder ------------------------------------------------------


class TestLiveBarBuilder:
    def test_naive_ts_rejected(self) -> None:
        b = LiveBarBuilder()
        with pytest.raises(ValueError, match="tz-aware"):
            b.on_trade(datetime(2026, 1, 1, 12, 0, 0), "Buy", 100.0, 0.1)

    def test_emits_on_second_boundary(self) -> None:
        bars: list[OneSecondBar] = []
        b = LiveBarBuilder()
        b.on_bar(bars.append)
        # Two trades in second 0
        b.on_trade(T0, "Buy", 100.0, 0.5)
        b.on_trade(T0 + timedelta(milliseconds=500), "Sell", 101.0, 0.3)
        # Trade in second 1 → emits previous bar
        b.on_trade(T0 + timedelta(seconds=1, milliseconds=100), "Buy", 102.0, 0.2)
        assert len(bars) == 1
        bar = bars[0]
        assert bar.ts_bar == T0
        assert bar.open == 100.0
        assert bar.high == 101.0
        assert bar.low == 100.0
        assert bar.close == 101.0
        assert bar.volume == pytest.approx(0.8)
        assert bar.buy_volume == pytest.approx(0.5)
        assert bar.sell_volume == pytest.approx(0.3)
        assert bar.trade_count == 2

    def test_vwap(self) -> None:
        bars: list[OneSecondBar] = []
        b = LiveBarBuilder()
        b.on_bar(bars.append)
        b.on_trade(T0, "Buy", 100.0, 1.0)
        b.on_trade(T0 + timedelta(milliseconds=200), "Buy", 200.0, 1.0)
        b.on_trade(T0 + timedelta(seconds=1), "Buy", 50.0, 1.0)
        # First bar: vwap = (100+200)/2 = 150
        assert bars[0].vwap == pytest.approx(150.0)

    def test_force_flush_emits_in_progress(self) -> None:
        bars: list[OneSecondBar] = []
        b = LiveBarBuilder()
        b.on_bar(bars.append)
        b.on_trade(T0, "Buy", 100.0, 1.0)
        assert len(bars) == 0
        b.force_flush()
        assert len(bars) == 1


# --- LiveFeatureBuilder --------------------------------------------------


def _bar(t: datetime, close: float, vol: float = 1.0) -> OneSecondBar:
    return OneSecondBar(
        ts_bar=t,
        open=close,
        high=close + 0.1,
        low=close - 0.1,
        close=close,
        vwap=close,
        volume=vol,
        buy_volume=vol * 0.5,
        sell_volume=vol * 0.5,
        trade_count=10,
    )


class TestLiveFeatureBuilder:
    def test_warmup_required(self) -> None:
        f = LiveFeatureBuilder(window_bars=20, rv_windows=(5,), vwap_windows=(5,), cum_delta_windows=(5,))
        for i in range(3):
            f.add_bar(_bar(T0 + timedelta(seconds=i), 100.0 + i * 0.1))
        assert not f.warmed_up
        assert f.build_features().is_empty()

    def test_features_after_warmup(self) -> None:
        f = LiveFeatureBuilder(window_bars=50, rv_windows=(5,), vwap_windows=(5,), cum_delta_windows=(5,))
        for i in range(20):
            f.add_bar(_bar(T0 + timedelta(seconds=i), 100.0 + i * 0.1))
        assert f.warmed_up
        feat = f.build_features()
        assert not feat.is_empty()
        # All standard columns present
        for col in ("flow_imbalance", "trade_rate", "rv_w5", "vwap_w5", "cum_delta_w5", "hour_sin"):
            assert col in feat.columns

    def test_latest_row_one_row(self) -> None:
        f = LiveFeatureBuilder(window_bars=50, rv_windows=(5,), vwap_windows=(5,), cum_delta_windows=(5,))
        for i in range(20):
            f.add_bar(_bar(T0 + timedelta(seconds=i), 100.0 + i * 0.1))
        last = f.latest_feature_row()
        assert len(last) == 1


# --- PaperBroker ----------------------------------------------------------


class TestPaperBroker:
    def test_open_long_then_close(self) -> None:
        b = PaperBroker(starting_capital_usd=100.0, leverage=2.0)
        ok = b.open_long(T0, 100.0, size_fraction_of_equity=0.10)
        assert ok
        assert b.has_position
        assert b.position.side == Side.LONG
        b.close(T0 + timedelta(seconds=10), 105.0, "tp")
        assert not b.has_position
        assert len(b.trades) == 1

    def test_kill_switch_blocks_new_orders(self) -> None:
        b = PaperBroker(starting_capital_usd=100.0, leverage=2.0)
        b.kill_switch.trigger_kill("manual")
        assert not b.open_long(T0, 100.0, 0.1)
        assert not b.has_position

    def test_drawdown_triggers_kill(self) -> None:
        b = PaperBroker(starting_capital_usd=100.0, leverage=3.0)
        b.open_long(T0, 100.0, 1.0)
        # Move price way down → big unrealized loss → drawdown > 10%
        b.mark(50.0)
        assert not b.can_trade  # killed by drawdown circuit breaker

    def test_invalid_leverage_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError):
            PaperBroker(leverage=10.0)  # > MAX_LEVERAGE=3


# --- model_io -------------------------------------------------------------


def _trained_model() -> Distinguisher:
    import numpy as np

    rng = np.random.default_rng(0)
    n = 500
    f1 = rng.standard_normal(n)
    f2 = rng.standard_normal(n)
    score = f1 + 0.5 * f2 + 0.2 * rng.standard_normal(n)
    label = np.where(score > 0.5, 1, np.where(score < -0.5, -1, 0)).astype(np.int8)
    df = pl.DataFrame(
        {
            "ts_bar": [T0 + timedelta(seconds=i) for i in range(n)],
            "f1": f1,
            "f2": f2,
            "label": label,
        }
    )
    d = Distinguisher(feature_cols=["f1", "f2"], label_col="label", n_pairwise=2, max_iter=200)
    d.fit(df)
    return d


class TestModelIO:
    def test_roundtrip(self, tmp_path: Path) -> None:
        m1 = _trained_model()
        path = tmp_path / "model.joblib"
        save_model(m1, path)
        m2 = load_model(path)
        assert isinstance(m2, Distinguisher)
        # Predictions should match exactly
        df = pl.DataFrame(
            {
                "f1": [0.1, 1.0, -1.0],
                "f2": [0.0, 0.5, -0.3],
            }
        )
        p1 = m1.predict_proba(df)
        p2 = m2.predict_proba(df)
        assert (p1 == p2).all()

    def test_load_wrong_type_raises(self, tmp_path: Path) -> None:
        import joblib

        path = tmp_path / "x.joblib"
        joblib.dump({"not_a_model": True}, path)
        with pytest.raises(TypeError, match="Distinguisher"):
            load_model(path)


# --- Session smoke (no live WS) ------------------------------------------


class TestSessionSmoke:
    def test_handle_bar_runs_warmed_up_pipeline(self, tmp_path: Path) -> None:
        """Inject bars directly; verify model + strategy + broker integrate."""
        # Build a tiny fake model for the session
        import numpy as np

        from scalping_bot.live.runner import PaperTradingSession

        rng = np.random.default_rng(0)
        # Synthetic feature frame matching what LiveFeatureBuilder produces
        n = 700
        prices = 100.0 + np.cumsum(rng.standard_normal(n) * 0.01)
        df = pl.DataFrame(
            {
                "ts_bar": [T0 + timedelta(seconds=i) for i in range(n)],
                "open": prices,
                "high": prices + 0.05,
                "low": prices - 0.05,
                "close": prices,
                "vwap": prices,
                "volume": np.ones(n),
                "buy_volume": np.full(n, 0.5),
                "sell_volume": np.full(n, 0.5),
                "trade_count": np.full(n, 10),
            }
        )

        # Build features the same way LiveFeatureBuilder does, train on them
        from scalping_bot.features.flow import (
            cumulative_delta,
            flow_imbalance,
            trade_rate,
        )
        from scalping_bot.features.flow import (
            vwap as vwap_feat,
        )
        from scalping_bot.features.temporal import (
            hour_of_day_features,
            minute_of_hour_features,
        )
        from scalping_bot.features.volatility import realized_vol, trade_price_vol

        df = flow_imbalance(df)
        df = trade_rate(df)
        df = realized_vol(df, window_bars=60)
        df = realized_vol(df, window_bars=300)
        df = vwap_feat(df, window_bars=30)
        df = vwap_feat(df, window_bars=300)
        df = cumulative_delta(df, window_bars=30)
        df = cumulative_delta(df, window_bars=300)
        df = trade_price_vol(df, window_bars=300)
        df = hour_of_day_features(df)
        df = minute_of_hour_features(df)

        # Synthetic label
        label = (rng.standard_normal(n) > 0.3).astype(np.int8) * 2 - 1
        df = df.with_columns(pl.Series("label_30", label))
        df = df.drop_nulls()

        feature_cols = [
            "flow_imbalance",
            "trade_rate",
            "rv_w60",
            "rv_w300",
            "vwap_w30",
            "vwap_w300",
            "cum_delta_w30",
            "cum_delta_w300",
            "price_range_w300",
            "hour_sin",
            "hour_cos",
            "minute_sin",
            "minute_cos",
        ]
        model = Distinguisher(
            feature_cols=feature_cols,
            label_col="label_30",
            n_pairwise=3,
            max_iter=200,
        )
        model.fit(df)

        broker = PaperBroker(starting_capital_usd=100.0, leverage=2.0)
        strategy = ThresholdStrategy(StrategyConfig(enter_threshold=0.40))

        # We don't actually start the WS — just inject bars synthetically.
        session = PaperTradingSession(
            symbol="BTCUSDT",
            model=model,
            broker=broker,
            strategy=strategy,
            feature_window_bars=400,
        )

        # Feed many bars; once warmed up, _handle_bar should attempt
        # predictions without crashing.
        for i in range(500):
            bar = _bar(T0 + timedelta(seconds=i), prices[i] if i < n else prices[-1])
            session._handle_bar(bar)

        # Either there are trades or there aren't; the point is no crash.
        assert isinstance(broker.trades, tuple)
