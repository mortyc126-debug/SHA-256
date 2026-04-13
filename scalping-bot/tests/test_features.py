"""Tests for the feature engineering modules.

We use small synthetic polars frames so assertions are exact. A separate
file (test_features_integration.py) exercises end-to-end on data sampled
via fixtures if available.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from scalping_bot.features import (
    aggregate_trades_to_bars,
    build_feature_matrix,
    cumulative_delta,
    flow_imbalance,
    forward_return,
    hour_of_day_features,
    label_direction,
    load_trades_range,
    minute_of_hour_features,
    pairwise_and_features,
    realized_vol,
    top_k_pairs_by_correlation,
    trade_price_vol,
    trade_rate,
    vwap,
)
from scalping_bot.features.pairwise import PairwiseSpec

T0 = datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC)


def _make_trades(n: int, price: float = 70_000.0) -> pl.DataFrame:
    """Produce a deterministic trades frame with alternating sides."""
    return pl.DataFrame(
        {
            "ts": [T0 + timedelta(milliseconds=i * 100) for i in range(n)],
            "side": ["Buy" if i % 2 == 0 else "Sell" for i in range(n)],
            "price": [price + i * 0.01 for i in range(n)],
            "size": [0.1 for _ in range(n)],
        }
    )


def _make_bars(n: int = 20) -> pl.DataFrame:
    """Synthetic bar frame with known structure."""
    prices = [70_000.0 + i * 0.5 for i in range(n)]
    return pl.DataFrame(
        {
            "ts_bar": [T0 + timedelta(seconds=i) for i in range(n)],
            "open": prices,
            "high": [p + 0.3 for p in prices],
            "low": [p - 0.3 for p in prices],
            "close": prices,
            "vwap": prices,
            "volume": [1.0 for _ in range(n)],
            "buy_volume": [0.7 if i % 2 == 0 else 0.3 for i in range(n)],
            "sell_volume": [0.3 if i % 2 == 0 else 0.7 for i in range(n)],
            "trade_count": [10 for _ in range(n)],
        }
    )


class TestAggregateTrades:
    def test_empty_input_returns_empty(self) -> None:
        empty = pl.DataFrame({"ts": [], "side": [], "price": [], "size": []}).cast(
            {
                "ts": pl.Datetime(time_zone="UTC"),
                "side": pl.Utf8,
                "price": pl.Float64,
                "size": pl.Float64,
            }
        )
        out = aggregate_trades_to_bars(empty)
        assert out.is_empty()

    def test_bars_contain_ohlc(self) -> None:
        trades = _make_trades(20)
        bars = aggregate_trades_to_bars(trades, bar_seconds=1.0)
        assert {"open", "high", "low", "close", "vwap", "volume"}.issubset(bars.columns)
        # All trades fit into 2 seconds → 2 bars
        assert bars.height == 2

    def test_buy_sell_split(self) -> None:
        trades = _make_trades(20)
        bars = aggregate_trades_to_bars(trades, bar_seconds=5.0)
        row = bars.row(0, named=True)
        # 10 buys (idx 0..18 step 2) * 0.1 = 1.0, same for sells
        assert pytest.approx(row["buy_volume"], abs=1e-9) == 1.0
        assert pytest.approx(row["sell_volume"], abs=1e-9) == 1.0


class TestFlow:
    def test_flow_imbalance_bounded(self) -> None:
        bars = _make_bars()
        out = flow_imbalance(bars)
        assert "flow_imbalance" in out.columns
        vals = out["flow_imbalance"].to_list()
        for v in vals:
            assert -1.0 <= v <= 1.0

    def test_flow_imbalance_requires_cols(self) -> None:
        bad = pl.DataFrame({"x": [1, 2, 3]})
        with pytest.raises(ValueError, match="buy_volume and sell_volume"):
            flow_imbalance(bad)

    def test_flow_imbalance_zero_on_no_volume(self) -> None:
        bars = pl.DataFrame(
            {
                "ts_bar": [T0],
                "buy_volume": [0.0],
                "sell_volume": [0.0],
            }
        )
        out = flow_imbalance(bars)
        assert out["flow_imbalance"].to_list() == [0.0]

    def test_cum_delta_monotonic_when_buy_dominant(self) -> None:
        bars = pl.DataFrame(
            {
                "ts_bar": [T0 + timedelta(seconds=i) for i in range(5)],
                "buy_volume": [1.0, 2.0, 3.0, 4.0, 5.0],
                "sell_volume": [0.0, 0.0, 0.0, 0.0, 0.0],
            }
        )
        out = cumulative_delta(bars)
        vals = out["cum_delta"].to_list()
        assert vals == [1.0, 3.0, 6.0, 10.0, 15.0]

    def test_cum_delta_windowed(self) -> None:
        bars = pl.DataFrame(
            {
                "ts_bar": [T0 + timedelta(seconds=i) for i in range(4)],
                "buy_volume": [1.0, 1.0, 1.0, 1.0],
                "sell_volume": [0.0, 0.0, 0.0, 0.0],
            }
        )
        out = cumulative_delta(bars, window_bars=2)
        assert out["cum_delta_w2"].to_list() == [1.0, 2.0, 2.0, 2.0]

    def test_trade_rate(self) -> None:
        bars = _make_bars(5)
        out = trade_rate(bars)
        # Bar width inferred as 1s → rate == trade_count
        assert out["trade_rate"].to_list() == [10.0, 10.0, 10.0, 10.0, 10.0]

    def test_vwap_rolling(self) -> None:
        bars = pl.DataFrame(
            {
                "ts_bar": [T0 + timedelta(seconds=i) for i in range(4)],
                "vwap": [100.0, 200.0, 300.0, 400.0],
                "volume": [1.0, 1.0, 1.0, 1.0],
            }
        )
        out = vwap(bars, window_bars=2)
        # Rolling sum(vwap*vol)=[(100),(300),(500),(700)]
        # Rolling sum(vol)=[(1),(2),(2),(2)]
        # Result = [100, 150, 250, 350]
        assert out["vwap_w2"].to_list() == pytest.approx([100.0, 150.0, 250.0, 350.0])


class TestVolatility:
    def test_realized_vol_basic(self) -> None:
        bars = _make_bars(10)
        out = realized_vol(bars, window_bars=3)
        assert f"rv_w{3}" in out.columns

    def test_realized_vol_requires_col(self) -> None:
        bars = _make_bars(5).drop("close")
        with pytest.raises(ValueError):
            realized_vol(bars, window_bars=3)

    def test_trade_price_vol(self) -> None:
        bars = _make_bars(10)
        out = trade_price_vol(bars, window_bars=5)
        assert "price_range_w5" in out.columns
        # All positive (high>low always)
        for v in out["price_range_w5"].drop_nulls().to_list():
            assert v >= 0


class TestTemporal:
    def test_hour_encoding(self) -> None:
        bars = _make_bars(1)
        out = hour_of_day_features(bars)
        assert "hour_sin" in out.columns
        assert "hour_cos" in out.columns
        # hour=12 → angle = pi → sin≈0, cos=-1
        assert out["hour_sin"][0] == pytest.approx(0, abs=1e-10)
        assert out["hour_cos"][0] == pytest.approx(-1, abs=1e-10)

    def test_minute_encoding(self) -> None:
        bars = _make_bars(1)
        out = minute_of_hour_features(bars)
        # minute=0 → angle=0 → sin=0, cos=1
        assert out["minute_sin"][0] == pytest.approx(0, abs=1e-10)
        assert out["minute_cos"][0] == pytest.approx(1, abs=1e-10)

    def test_missing_col_raises(self) -> None:
        bars = pl.DataFrame({"x": [1]})
        with pytest.raises(ValueError):
            hour_of_day_features(bars)
        with pytest.raises(ValueError):
            minute_of_hour_features(bars)


class TestLabels:
    def test_forward_return(self) -> None:
        bars = pl.DataFrame(
            {
                "ts_bar": [T0 + timedelta(seconds=i) for i in range(4)],
                "close": [100.0, 110.0, 121.0, 121.0],
            }
        )
        out = forward_return(bars, horizon_bars=1)
        # [(110/100-1), (121/110-1), (121/121-1), null]
        vals = out["fwd_return_1"].to_list()
        assert vals[0] == pytest.approx(0.10)
        assert vals[1] == pytest.approx(0.10)
        assert vals[2] == pytest.approx(0.0)
        assert vals[3] is None

    def test_forward_return_requires_positive_horizon(self) -> None:
        bars = _make_bars(3)
        with pytest.raises(ValueError, match="horizon_bars"):
            forward_return(bars, horizon_bars=0)

    def test_label_direction_three_classes(self) -> None:
        bars = pl.DataFrame(
            {
                "ts_bar": [T0 + timedelta(seconds=i) for i in range(4)],
                "close": [100.0, 100.05, 99.95, 100.0],
            }
        )
        out = label_direction(bars, horizon_bars=1, threshold_bps=3.0)
        labels = out["label_1"].to_list()
        # 1st: 100.05/100-1 = 5 bps > 3 → +1
        # 2nd: 99.95/100.05-1 = ~-10 bps < -3 → -1
        # 3rd: 100/99.95-1 = 5 bps > 3 → +1
        # 4th: null forward → 0
        assert labels[:3] == [1, -1, 1]


class TestPairwise:
    def test_top_k_returns_specs(self) -> None:
        df = pl.DataFrame(
            {
                "a": list(range(100)),
                "b": list(range(100, 0, -1)),
                "target": [1 if i > 80 else 0 for i in range(100)],
            }
        )
        specs = top_k_pairs_by_correlation(df, feature_cols=["a", "b"], target_col="target", k=3)
        assert len(specs) <= 3
        for s in specs:
            assert s.feat_a in {"a", "b"}
            assert s.feat_b in {"a", "b"}

    def test_apply_pairwise_features(self) -> None:
        df = pl.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [10.0, 20.0, 30.0, 40.0]})
        spec = PairwiseSpec(
            feat_a="a", op_a=">", thresh_a=2.5,
            feat_b="b", op_b=">", thresh_b=25.0,
        )
        out = pairwise_and_features(df, [spec])
        assert spec.name in out.columns
        assert out[spec.name].to_list() == [0, 0, 1, 1]

    def test_empty_specs_returns_input(self) -> None:
        df = pl.DataFrame({"a": [1, 2]})
        out = pairwise_and_features(df, [])
        assert out.equals(df)

    def test_binarize_rejects_bad_op(self) -> None:
        df = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        bad_spec = PairwiseSpec(
            feat_a="a", op_a="==", thresh_a=1, feat_b="b", op_b=">", thresh_b=0
        )
        with pytest.raises(ValueError, match="op must be"):
            pairwise_and_features(df, [bad_spec])


class TestBuilder:
    def test_load_trades_range_empty_for_missing_dates(self, tmp_path):
        from datetime import date

        out = load_trades_range(tmp_path, "BTCUSDT", date(2020, 1, 1), date(2020, 1, 2))
        assert out.is_empty()

    def test_load_trades_range_rejects_reversed(self, tmp_path):
        from datetime import date

        with pytest.raises(ValueError, match="must be"):
            load_trades_range(tmp_path, "BTCUSDT", date(2020, 1, 2), date(2020, 1, 1))

    def test_build_feature_matrix_small(self) -> None:
        # 600 trades across 60 seconds, varied prices
        trades = _make_trades(600)
        # Adjust to ensure enough data for 60-bar window
        fm = build_feature_matrix(
            trades,
            bar_seconds=0.1,  # 10 bars per sec → 600 bars
            label_horizon_bars=3,
            rv_windows=(5,),
            vwap_windows=(5,),
            cum_delta_windows=(5,),
        )
        assert not fm.is_empty()
        expected_cols = {
            "ts_bar",
            "close",
            "flow_imbalance",
            "trade_rate",
            "rv_w5",
            "vwap_w5",
            "cum_delta_w5",
            "hour_sin",
            "hour_cos",
            "label_3",
        }
        assert expected_cols.issubset(fm.columns)
        # Labels in {-1, 0, 1}
        assert set(fm["label_3"].unique().to_list()).issubset({-1, 0, 1})
