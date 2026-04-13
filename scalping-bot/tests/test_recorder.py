"""Tests for ParquetRecorder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from scalping_bot.market_data.recorder import ParquetRecorder

T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)


class TestConstruction:
    def test_rejects_invalid_batch_size(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="batch_size"):
            ParquetRecorder(data_dir=tmp_path, symbol="BTCUSDT", batch_size=0)

    def test_rejects_invalid_flush_interval(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="flush_interval_seconds"):
            ParquetRecorder(
                data_dir=tmp_path,
                symbol="BTCUSDT",
                flush_interval_seconds=0,
            )

    def test_rejects_naive_ts(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(data_dir=tmp_path, symbol="BTCUSDT")
        with pytest.raises(ValueError, match="tz-aware"):
            rec.record_trade(ts=datetime(2026, 4, 13, 12, 0, 0), row={"price": 70_000})


class TestBatching:
    def test_small_batch_not_flushed_immediately(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(
            data_dir=tmp_path,
            symbol="BTCUSDT",
            batch_size=1000,
            flush_interval_seconds=60,
        )
        rec.record_trade(
            ts=T0,
            row={"trade_time_ms": 1, "side": "Buy", "price": 70_000.0, "size": 0.1, "trade_id": "a"},
        )
        assert rec.buffered_counts()["trades"] == 1
        assert rec.total_rows_written() == 0

    def test_reaches_batch_size_triggers_flush(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(
            data_dir=tmp_path,
            symbol="BTCUSDT",
            batch_size=3,
            flush_interval_seconds=60,
        )
        for i in range(3):
            rec.record_trade(
                ts=T0 + timedelta(microseconds=i),
                row={
                    "trade_time_ms": i,
                    "side": "Buy",
                    "price": 70_000.0 + i,
                    "size": 0.1,
                    "trade_id": f"a{i}",
                },
            )
        assert rec.total_rows_written() == 3
        assert rec.buffered_counts()["trades"] == 0


class TestFlush:
    def test_flush_writes_buffered_rows(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(
            data_dir=tmp_path,
            symbol="BTCUSDT",
            batch_size=1000,
            flush_interval_seconds=600,
        )
        for i in range(5):
            rec.record_trade(
                ts=T0 + timedelta(microseconds=i),
                row={
                    "trade_time_ms": i,
                    "side": "Buy",
                    "price": 70_000.0,
                    "size": 0.1,
                    "trade_id": f"a{i}",
                },
            )
        rec.flush(now=T0 + timedelta(seconds=10))
        assert rec.total_rows_written() == 5
        assert rec.buffered_counts()["trades"] == 0

    def test_flush_on_empty_buffer_is_safe(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(data_dir=tmp_path, symbol="BTCUSDT")
        rec.flush()  # should not raise
        assert rec.total_rows_written() == 0


class TestFileLayout:
    def test_trade_file_written_at_expected_path(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(
            data_dir=tmp_path,
            symbol="BTCUSDT",
            batch_size=1,
        )
        rec.record_trade(
            ts=T0,
            row={
                "trade_time_ms": 1,
                "side": "Buy",
                "price": 70_000.0,
                "size": 0.1,
                "trade_id": "abc",
            },
        )
        expected = tmp_path / "trades" / "date=2026-04-13" / "BTCUSDT_12.parquet"
        assert expected.exists()

    def test_files_rotate_hourly(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(
            data_dir=tmp_path,
            symbol="BTCUSDT",
            batch_size=1,
        )
        # 12:00 and 13:00 land in different files
        rec.record_trade(
            ts=T0,
            row={
                "trade_time_ms": 1,
                "side": "Buy",
                "price": 70_000.0,
                "size": 0.1,
                "trade_id": "a",
            },
        )
        rec.record_trade(
            ts=T0 + timedelta(hours=1),
            row={
                "trade_time_ms": 2,
                "side": "Sell",
                "price": 70_100.0,
                "size": 0.2,
                "trade_id": "b",
            },
        )
        paths = list(ParquetRecorder.iter_files(tmp_path, "trades"))
        hours = sorted(p.stem.split("_")[-1] for p in paths)
        assert hours == ["12", "13"]

    def test_appends_within_same_file(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(data_dir=tmp_path, symbol="BTCUSDT", batch_size=1)
        rec.record_trade(
            ts=T0,
            row={
                "trade_time_ms": 1,
                "side": "Buy",
                "price": 70_000.0,
                "size": 0.1,
                "trade_id": "a",
            },
        )
        rec.record_trade(
            ts=T0 + timedelta(seconds=1),
            row={
                "trade_time_ms": 2,
                "side": "Sell",
                "price": 70_100.0,
                "size": 0.2,
                "trade_id": "b",
            },
        )
        path = tmp_path / "trades" / "date=2026-04-13" / "BTCUSDT_12.parquet"
        df = pl.read_parquet(path)
        assert len(df) == 2


class TestMultipleStreams:
    def test_separate_directories(self, tmp_path: Path) -> None:
        rec = ParquetRecorder(data_dir=tmp_path, symbol="BTCUSDT", batch_size=1)
        rec.record_trade(
            ts=T0,
            row={
                "trade_time_ms": 1,
                "side": "Buy",
                "price": 70_000.0,
                "size": 0.1,
                "trade_id": "a",
            },
        )
        rec.record_ticker(ts=T0, row={"lastPrice": "70000.0", "fundingRate": "0.0001"})
        rec.record_orderbook_delta(
            ts=T0,
            row={"update_id": 1, "bids": [[70_000.0, 1.0]], "asks": []},
        )
        counts = rec.write_counts()
        assert counts.get("trades") == 1
        assert counts.get("tickers") == 1
        assert counts.get("orderbook") == 1
