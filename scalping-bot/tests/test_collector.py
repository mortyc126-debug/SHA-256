"""Tests for the Collector orchestration class.

We don't connect to Bybit. Instead we inject messages directly via the
private handler methods and verify orderbook state, recorder output,
and monitor state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import pytest

from scalping_bot.market_data.collector import (
    STREAM_ORDERBOOK,
    STREAM_TICKERS,
    STREAM_TRADES,
    Collector,
)


def _trade_msg(ts_ms: int, side: str, price: float, size: float, trade_id: str) -> dict[str, Any]:
    return {
        "topic": "publicTrade.BTCUSDT",
        "type": "snapshot",
        "ts": ts_ms,
        "data": [
            {
                "T": ts_ms,
                "s": "BTCUSDT",
                "S": side,
                "v": str(size),
                "p": str(price),
                "L": "PlusTick",
                "i": trade_id,
                "BT": False,
            }
        ],
    }


def _orderbook_msg(
    msg_type: str,
    ts_ms: int,
    update_id: int,
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
) -> dict[str, Any]:
    return {
        "topic": "orderbook.50.BTCUSDT",
        "type": msg_type,
        "ts": ts_ms,
        "data": {
            "s": "BTCUSDT",
            "b": [[str(p), str(s)] for p, s in bids],
            "a": [[str(p), str(s)] for p, s in asks],
            "u": update_id,
            "seq": update_id,
        },
    }


def _ticker_msg(ts_ms: int, last_price: float, funding_rate: float) -> dict[str, Any]:
    return {
        "topic": "tickers.BTCUSDT",
        "type": "snapshot",
        "ts": ts_ms,
        "data": {
            "symbol": "BTCUSDT",
            "lastPrice": str(last_price),
            "markPrice": str(last_price),
            "indexPrice": str(last_price),
            "fundingRate": str(funding_rate),
        },
    }


@pytest.fixture
def collector(tmp_path: Path) -> Collector:
    return Collector(symbol="BTCUSDT", data_dir=tmp_path, depth=5)


class TestTradeHandling:
    def test_trade_recorded(self, collector: Collector) -> None:
        collector._handle_trade(
            _trade_msg(ts_ms=1_704_067_200_000, side="Buy", price=70_000, size=0.1, trade_id="a")
        )
        collector.recorder.flush()
        assert collector.recorder.total_rows_written() >= 1
        assert STREAM_TRADES in collector.monitor.streams

    def test_malformed_trade_logged_not_crashed(self, collector: Collector) -> None:
        collector._handle_trade({"ts": "not-a-number", "data": []})
        # No exception; nothing recorded
        assert collector.recorder.total_rows_written() == 0

    def test_trade_list_iterated(self, collector: Collector) -> None:
        msg = _trade_msg(ts_ms=1_704_067_200_000, side="Buy", price=1, size=1, trade_id="a")
        msg["data"] = [
            msg["data"][0],
            {**msg["data"][0], "i": "b"},
            {**msg["data"][0], "i": "c"},
        ]
        collector._handle_trade(msg)
        collector.recorder.flush()
        assert collector.recorder.total_rows_written() == 3


class TestOrderbookHandling:
    def test_snapshot_initializes_book(self, collector: Collector) -> None:
        collector._handle_orderbook(
            _orderbook_msg(
                "snapshot",
                ts_ms=1_704_067_200_000,
                update_id=1,
                bids=[(70_000, 1.0), (69_999, 2.0)],
                asks=[(70_001, 0.5)],
            )
        )
        assert collector.orderbook.initialized
        assert collector.orderbook.best_bid() == (70_000.0, 1.0)

    def test_delta_updates_book(self, collector: Collector) -> None:
        collector._handle_orderbook(
            _orderbook_msg(
                "snapshot",
                ts_ms=1_704_067_200_000,
                update_id=1,
                bids=[(70_000, 1.0)],
                asks=[(70_001, 0.5)],
            )
        )
        collector._handle_orderbook(
            _orderbook_msg(
                "delta",
                ts_ms=1_704_067_200_100,
                update_id=2,
                bids=[(70_000, 2.0)],
                asks=[],
            )
        )
        assert collector.orderbook.best_bid() == (70_000.0, 2.0)

    def test_sequence_gap_resets_book(self, collector: Collector) -> None:
        collector._handle_orderbook(
            _orderbook_msg(
                "snapshot",
                ts_ms=1,
                update_id=10,
                bids=[(1.0, 1.0)],
                asks=[(2.0, 1.0)],
            )
        )
        assert collector.orderbook.initialized
        # Send a delta with an older update_id → gap detected → book reset
        collector._handle_orderbook(
            _orderbook_msg("delta", ts_ms=2, update_id=5, bids=[], asks=[])
        )
        assert not collector.orderbook.initialized
        assert collector.monitor.health_snapshot()[STREAM_ORDERBOOK]["gap_count"] == 1

    def test_malformed_orderbook_logged_not_crashed(self, collector: Collector) -> None:
        collector._handle_orderbook({"type": "snapshot", "ts": 1, "data": "oops"})
        # No crash; book not initialized
        assert not collector.orderbook.initialized

    def test_snapshot_recorded_to_parquet(self, tmp_path: Path, collector: Collector) -> None:
        collector._handle_orderbook(
            _orderbook_msg(
                "snapshot",
                ts_ms=1_704_067_200_000,
                update_id=1,
                bids=[(70_000, 1.0)],
                asks=[(70_001, 0.5)],
            )
        )
        collector.recorder.flush()
        # Snapshot should be in orderbook_snapshots stream
        counts = collector.recorder.write_counts()
        assert counts.get("orderbook_snapshots", 0) >= 1


class TestTickerHandling:
    def test_ticker_recorded(self, collector: Collector) -> None:
        collector._handle_ticker(
            _ticker_msg(ts_ms=1_704_067_200_000, last_price=70_000, funding_rate=0.0001)
        )
        collector.recorder.flush()
        counts = collector.recorder.write_counts()
        assert counts.get("tickers", 0) == 1
        assert STREAM_TICKERS in collector.monitor.streams

    def test_malformed_ticker_logged_not_crashed(self, collector: Collector) -> None:
        collector._handle_ticker({"ts": "x", "data": {}})
        assert collector.recorder.total_rows_written() == 0


class TestLifecycle:
    def test_stop_before_start_is_safe(self, collector: Collector) -> None:
        # Direct stop without run()
        collector.stop()

    def test_run_with_zero_duration_exits_quickly(
        self, collector: Collector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Monkey-patch WS start/stop to no-op
        monkeypatch.setattr(collector._ws, "start", lambda **kwargs: None)
        monkeypatch.setattr(collector._ws, "stop", lambda: None)
        collector.run(duration_seconds=0.01)


class TestDataOnDisk:
    def test_trades_readable_from_parquet(self, collector: Collector, tmp_path: Path) -> None:
        for i in range(3):
            collector._handle_trade(
                _trade_msg(
                    ts_ms=1_704_067_200_000 + i * 1000,
                    side="Buy",
                    price=70_000 + i,
                    size=0.1,
                    trade_id=f"t{i}",
                )
            )
        collector.recorder.flush()
        paths = list(collector.recorder.iter_files(tmp_path, "trades"))
        assert paths
        df = pl.read_parquet(paths[0])
        assert len(df) == 3
        assert set(df.columns) >= {"ts", "side", "price", "size", "trade_id"}
