"""Tests for orderbook state reconstruction from snapshot + delta."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scalping_bot.market_data.orderbook import (
    OrderbookState,
    SequenceGapError,
    parse_bybit_orderbook_msg,
)

TS0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)
TS1 = datetime(2026, 4, 13, 12, 0, 1, tzinfo=UTC)
TS2 = datetime(2026, 4, 13, 12, 0, 2, tzinfo=UTC)


class TestSnapshot:
    def test_empty_state_before_snapshot(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        assert not ob.initialized
        assert ob.best_bid() is None
        assert ob.best_ask() is None
        assert ob.mid_price() is None

    def test_snapshot_initializes(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000.0, 1.0), (69_999.0, 2.0)],
            asks=[(70_001.0, 0.5), (70_002.0, 1.5)],
            update_id=100,
            ts=TS0,
        )
        assert ob.initialized
        assert ob.best_bid() == (70_000.0, 1.0)
        assert ob.best_ask() == (70_001.0, 0.5)
        assert ob.mid_price() == pytest.approx(70_000.5)
        assert ob.last_update_id == 100

    def test_snapshot_drops_zero_size_levels(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000.0, 1.0), (69_999.0, 0.0)],  # 0-size should not appear
            asks=[(70_001.0, 0.5)],
            update_id=100,
            ts=TS0,
        )
        assert ob.top_n_bids(5) == [(70_000.0, 1.0)]

    def test_snapshot_replaces_prior_state(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000.0, 1.0)],
            asks=[(70_001.0, 0.5)],
            update_id=100,
            ts=TS0,
        )
        ob.apply_snapshot(
            bids=[(70_100.0, 2.0)],
            asks=[(70_101.0, 1.0)],
            update_id=200,
            ts=TS1,
        )
        assert ob.top_n_bids(5) == [(70_100.0, 2.0)]
        assert ob.last_update_id == 200


class TestDeltaApplication:
    def _initial_book(self) -> OrderbookState:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000.0, 1.0), (69_999.0, 2.0), (69_998.0, 3.0)],
            asks=[(70_001.0, 0.5), (70_002.0, 1.5), (70_003.0, 2.5)],
            update_id=100,
            ts=TS0,
        )
        return ob

    def test_delta_before_snapshot_raises(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        with pytest.raises(SequenceGapError, match="before snapshot"):
            ob.apply_delta(bids=[], asks=[], update_id=1, ts=TS0)

    def test_delta_updates_existing_level(self) -> None:
        ob = self._initial_book()
        ob.apply_delta(
            bids=[(70_000.0, 5.0)],  # price exists, update size
            asks=[],
            update_id=101,
            ts=TS1,
        )
        assert ob.best_bid() == (70_000.0, 5.0)

    def test_delta_adds_new_level(self) -> None:
        ob = self._initial_book()
        ob.apply_delta(
            bids=[(69_995.0, 10.0)],  # new price level
            asks=[],
            update_id=101,
            ts=TS1,
        )
        prices = [p for p, _ in ob.top_n_bids(10)]
        assert 69_995.0 in prices

    def test_delta_removes_level_on_zero_size(self) -> None:
        ob = self._initial_book()
        ob.apply_delta(
            bids=[(70_000.0, 0.0)],  # 0 = remove
            asks=[],
            update_id=101,
            ts=TS1,
        )
        assert ob.best_bid() == (69_999.0, 2.0)

    def test_delta_ask_side(self) -> None:
        ob = self._initial_book()
        ob.apply_delta(
            bids=[],
            asks=[(70_001.0, 0.0), (70_000.5, 7.0)],
            update_id=101,
            ts=TS1,
        )
        assert ob.best_ask() == (70_000.5, 7.0)

    def test_monotonic_update_id_required(self) -> None:
        ob = self._initial_book()
        with pytest.raises(SequenceGapError, match="non-monotonic"):
            ob.apply_delta(bids=[], asks=[], update_id=100, ts=TS1)  # same as last
        with pytest.raises(SequenceGapError, match="non-monotonic"):
            ob.apply_delta(bids=[], asks=[], update_id=99, ts=TS1)  # older

    def test_chained_deltas(self) -> None:
        ob = self._initial_book()
        ob.apply_delta(bids=[(70_000.0, 1.5)], asks=[], update_id=101, ts=TS1)
        ob.apply_delta(bids=[(70_000.0, 2.0)], asks=[], update_id=102, ts=TS2)
        ob.apply_delta(
            bids=[(70_000.0, 0.0)],  # remove
            asks=[],
            update_id=103,
            ts=TS2,
        )
        assert ob.best_bid() == (69_999.0, 2.0)


class TestQueries:
    def _populated(self) -> OrderbookState:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000 - i, 1.0 + i) for i in range(10)],
            asks=[(70_001 + i, 0.5 + i) for i in range(10)],
            update_id=1,
            ts=TS0,
        )
        return ob

    def test_spread_bps(self) -> None:
        ob = self._populated()
        # spread = 1.0; mid = 70_000.5; bps = 1.0 / 70_000.5 * 10000 ≈ 0.143
        spread = ob.spread_bps()
        assert spread is not None
        assert spread == pytest.approx(1.0 / 70_000.5 * 10_000.0, rel=1e-6)

    def test_top_n_bids_sorted_desc(self) -> None:
        ob = self._populated()
        top = ob.top_n_bids(5)
        assert len(top) == 5
        prices = [p for p, _ in top]
        assert prices == sorted(prices, reverse=True)
        assert prices[0] == 70_000.0

    def test_top_n_asks_sorted_asc(self) -> None:
        ob = self._populated()
        top = ob.top_n_asks(3)
        assert len(top) == 3
        prices = [p for p, _ in top]
        assert prices == sorted(prices)
        assert prices[0] == 70_001.0

    def test_imbalance_positive_when_more_bids(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000.0, 10.0), (69_999.0, 10.0)],
            asks=[(70_001.0, 1.0), (70_002.0, 1.0)],
            update_id=1,
            ts=TS0,
        )
        imb = ob.imbalance(levels=5)
        assert imb is not None
        assert imb > 0.8  # overwhelmingly bid

    def test_imbalance_negative_when_more_asks(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(
            bids=[(70_000.0, 1.0)],
            asks=[(70_001.0, 10.0), (70_002.0, 10.0)],
            update_id=1,
            ts=TS0,
        )
        imb = ob.imbalance(levels=5)
        assert imb is not None
        assert imb < -0.8

    def test_imbalance_none_when_one_side_empty(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        ob.apply_snapshot(bids=[(70_000.0, 1.0)], asks=[], update_id=1, ts=TS0)
        assert ob.imbalance() is None

    def test_snapshot_view_structure(self) -> None:
        ob = self._populated()
        view = ob.snapshot_view()
        assert view["symbol"] == "BTCUSDT"
        assert view["update_id"] == 1
        assert isinstance(view["bids"], list)
        assert isinstance(view["asks"], list)


class TestBybitMessageParsing:
    def test_parses_snapshot(self) -> None:
        msg = {
            "topic": "orderbook.50.BTCUSDT",
            "type": "snapshot",
            "ts": 1_704_067_200_000,
            "data": {
                "s": "BTCUSDT",
                "b": [["70000.00", "1.0"], ["69999.50", "2.0"]],
                "a": [["70000.50", "0.5"]],
                "u": 1234,
                "seq": 9999,
            },
        }
        msg_type, bids, asks, uid, ts = parse_bybit_orderbook_msg(msg)
        assert msg_type == "snapshot"
        assert bids == [(70000.0, 1.0), (69999.5, 2.0)]
        assert asks == [(70000.5, 0.5)]
        assert uid == 1234
        assert ts.tzinfo == UTC

    def test_parses_delta(self) -> None:
        msg = {
            "topic": "orderbook.50.BTCUSDT",
            "type": "delta",
            "ts": 1_704_067_200_100,
            "data": {
                "s": "BTCUSDT",
                "b": [],
                "a": [["70000.50", "0.0"]],
                "u": 1235,
                "seq": 10000,
            },
        }
        msg_type, bids, asks, uid, _ts = parse_bybit_orderbook_msg(msg)
        assert msg_type == "delta"
        assert bids == []
        assert asks == [(70000.5, 0.0)]
        assert uid == 1235

    def test_rejects_unknown_type(self) -> None:
        msg = {"type": "weird", "ts": 1, "data": {"u": 1}}
        with pytest.raises(ValueError, match="unexpected"):
            parse_bybit_orderbook_msg(msg)

    def test_rejects_non_dict_data(self) -> None:
        msg = {"type": "snapshot", "ts": 1, "data": "oops"}
        with pytest.raises(ValueError, match="dict data"):
            parse_bybit_orderbook_msg(msg)

    def test_rejects_non_list_bids_or_asks(self) -> None:
        msg = {"type": "snapshot", "ts": 1, "data": {"b": "nope", "a": [], "u": 1}}
        with pytest.raises(ValueError, match="must be lists"):
            parse_bybit_orderbook_msg(msg)


class TestFullReconstructionScenario:
    """Replay a realistic snapshot+deltas sequence end-to-end."""

    def test_reconstructed_state_matches_expected(self) -> None:
        ob = OrderbookState(symbol="BTCUSDT")
        # Snapshot: 3 bids, 3 asks
        ob.apply_snapshot(
            bids=[(70_000.0, 1.0), (69_999.0, 2.0), (69_998.0, 3.0)],
            asks=[(70_001.0, 0.5), (70_002.0, 1.5), (70_003.0, 2.5)],
            update_id=100,
            ts=TS0,
        )

        # Delta 1: remove top bid, add new ask level
        ob.apply_delta(
            bids=[(70_000.0, 0.0)],
            asks=[(70_000.5, 0.7)],
            update_id=101,
            ts=TS1,
        )
        # Delta 2: update existing ask
        ob.apply_delta(
            bids=[],
            asks=[(70_001.0, 5.0)],
            update_id=102,
            ts=TS2,
        )
        # Delta 3: add new best bid
        ob.apply_delta(
            bids=[(70_000.2, 4.0)],
            asks=[],
            update_id=103,
            ts=TS2,
        )

        assert ob.best_bid() == (70_000.2, 4.0)
        assert ob.best_ask() == (70_000.5, 0.7)
        assert ob.last_update_id == 103
        # Spread = 0.3; mid ≈ 70_000.35
        spread = ob.spread_bps()
        assert spread is not None
        assert spread == pytest.approx(0.3 / 70_000.35 * 10_000.0, rel=1e-6)
