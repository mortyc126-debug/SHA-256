"""Tests for orderbook microstructure features."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from scalping_bot.features.orderbook import (
    align_to_bars,
    join_to_feature_matrix,
    snapshot_features,
)

T0 = datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC)


def _snaps(rows: list[tuple[datetime, int, list[list[float]], list[list[float]]]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ts": [r[0] for r in rows],
            "update_id": [r[1] for r in rows],
            "bids": [r[2] for r in rows],
            "asks": [r[3] for r in rows],
        }
    )


class TestSnapshotFeatures:
    def test_empty_returns_empty(self) -> None:
        df = _snaps([])
        out = snapshot_features(df)
        assert out.is_empty()

    def test_missing_columns_raises(self) -> None:
        df = pl.DataFrame({"x": [1, 2]})
        with pytest.raises(ValueError, match="bids"):
            snapshot_features(df)

    def test_basic_mid_and_spread(self) -> None:
        df = _snaps(
            [
                (T0, 1, [[70_000.0, 1.0], [69_999.0, 2.0]], [[70_001.0, 0.5], [70_002.0, 1.5]]),
            ]
        )
        out = snapshot_features(df, levels_list=(2,))
        row = out.row(0, named=True)
        assert row["best_bid"] == 70_000.0
        assert row["best_ask"] == 70_001.0
        assert row["mid"] == 70_000.5
        # spread = 1.0 → 1.0 / 70_000.5 * 10_000 ≈ 0.143 bps
        assert row["spread_bps"] == pytest.approx(1.0 / 70_000.5 * 10_000.0, rel=1e-6)

    def test_obi_positive_when_more_bids(self) -> None:
        df = _snaps(
            [
                (T0, 1, [[100.0, 10.0], [99.0, 10.0]], [[101.0, 1.0], [102.0, 1.0]]),
            ]
        )
        out = snapshot_features(df, levels_list=(5,))
        obi = out["obi_5"][0]
        # (20 - 2) / 22 ≈ 0.818
        assert obi == pytest.approx((20.0 - 2.0) / (20.0 + 2.0), rel=1e-6)

    def test_obi_negative_when_more_asks(self) -> None:
        df = _snaps([(T0, 1, [[100.0, 1.0]], [[101.0, 10.0], [102.0, 10.0]])])
        out = snapshot_features(df, levels_list=(5,))
        obi = out["obi_5"][0]
        assert obi < -0.8

    def test_depth_skew_positive(self) -> None:
        df = _snaps([(T0, 1, [[100.0, 4.0]], [[101.0, 1.0]])])
        out = snapshot_features(df, levels_list=(5,))
        # log(4/1) ≈ 1.386
        assert out["depth_skew_5"][0] == pytest.approx(1.386, abs=0.01)

    def test_skips_zero_size_levels(self) -> None:
        df = _snaps(
            [(T0, 1, [[100.0, 0.0], [99.0, 1.0]], [[101.0, 0.0], [102.0, 1.0]])]
        )
        out = snapshot_features(df, levels_list=(5,))
        # best bid/ask should skip the 0-size top level
        assert out["best_bid"][0] == 99.0
        assert out["best_ask"][0] == 102.0

    def test_empty_side_yields_nulls(self) -> None:
        df = _snaps([(T0, 1, [], [[101.0, 1.0]])])
        out = snapshot_features(df, levels_list=(5,))
        assert out["best_bid"][0] is None
        assert out["mid"][0] is None
        # OBI is -1 when bids empty (pure ask pressure)
        assert out["obi_5"][0] == -1.0

    def test_multiple_levels(self) -> None:
        df = _snaps(
            [
                (
                    T0,
                    1,
                    [[100.0, 1.0], [99.0, 2.0], [98.0, 3.0]],
                    [[101.0, 1.0], [102.0, 2.0], [103.0, 3.0]],
                )
            ]
        )
        out = snapshot_features(df, levels_list=(1, 3))
        # Top-1: bid=1, ask=1 → obi=0
        assert out["obi_1"][0] == 0.0
        # Top-3: bid=6, ask=6 → obi=0
        assert out["obi_3"][0] == 0.0


class TestAlignToBars:
    def test_aligns_two_snapshots_into_one_bar(self) -> None:
        """Both snapshots fall in the same 1-second bar — averaged."""
        ts1 = T0
        ts2 = T0 + timedelta(milliseconds=500)
        df = pl.DataFrame(
            {
                "ts": [ts1, ts2],
                "update_id": [1, 2],
                "obi_5": [0.2, 0.4],
                "spread_bps": [0.5, 0.7],
                "mid": [70_000.0, 70_001.0],
            }
        )
        out = align_to_bars(df, bar_seconds=1.0)
        assert len(out) == 1
        assert out["obi_5"][0] == pytest.approx(0.3)
        assert out["mid"][0] == pytest.approx(70_000.5)

    def test_separate_bars_not_merged(self) -> None:
        df = pl.DataFrame(
            {
                "ts": [T0, T0 + timedelta(seconds=2)],
                "update_id": [1, 2],
                "obi_5": [0.2, 0.4],
            }
        )
        out = align_to_bars(df, bar_seconds=1.0)
        assert len(out) == 2

    def test_empty_input_safe(self) -> None:
        empty = pl.DataFrame({"ts": [], "obi_5": []}).cast(
            {"ts": pl.Datetime(time_zone="UTC"), "obi_5": pl.Float64}
        )
        out = align_to_bars(empty)
        assert "ts_bar" in out.columns


class TestJoinToFeatureMatrix:
    def test_left_join_forward_fills(self) -> None:
        trade_bars = pl.DataFrame(
            {
                "ts_bar": [
                    T0,
                    T0 + timedelta(seconds=1),
                    T0 + timedelta(seconds=2),
                ],
                "close": [100.0, 101.0, 102.0],
            }
        )
        ob_bars = pl.DataFrame(
            {
                "ts_bar": [T0, T0 + timedelta(seconds=2)],
                "obi_5": [0.2, 0.5],
            }
        )
        out = join_to_feature_matrix(trade_bars, ob_bars)
        # Row 1 (t+1s) had no OB row; should forward-fill 0.2
        assert out["obi_5"].to_list() == [0.2, 0.2, 0.5]

    def test_empty_orderbook_returns_trade_bars(self) -> None:
        trade_bars = pl.DataFrame({"ts_bar": [T0], "close": [100.0]})
        out = join_to_feature_matrix(trade_bars, pl.DataFrame())
        assert out.equals(trade_bars)
