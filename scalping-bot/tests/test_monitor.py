"""Tests for CollectorMonitor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scalping_bot.market_data.monitor import CollectorMonitor

T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)


class TestBasics:
    def test_empty_monitor(self) -> None:
        m = CollectorMonitor()
        assert m.streams == ()
        assert not m.is_stream_healthy("trades")
        assert not m.all_healthy(["trades", "orderbook"])

    def test_record_message_marks_healthy(self) -> None:
        m = CollectorMonitor(heartbeat_timeout_seconds=30)
        m.record_message("trades", now=T0)
        assert m.is_stream_healthy("trades", now=T0)
        assert m.is_stream_healthy("trades", now=T0 + timedelta(seconds=29))

    def test_stale_stream_unhealthy(self) -> None:
        m = CollectorMonitor(heartbeat_timeout_seconds=30)
        m.record_message("trades", now=T0)
        assert not m.is_stream_healthy("trades", now=T0 + timedelta(seconds=31))

    def test_all_healthy_requires_all(self) -> None:
        m = CollectorMonitor(heartbeat_timeout_seconds=30)
        m.record_message("trades", now=T0)
        m.record_message("orderbook", now=T0)
        assert m.all_healthy(["trades", "orderbook"], now=T0)
        # Let orderbook go stale
        future = T0 + timedelta(seconds=31)
        m.record_message("trades", now=future)
        assert not m.all_healthy(["trades", "orderbook"], now=future)


class TestCounts:
    def test_message_count_increments(self) -> None:
        m = CollectorMonitor()
        for i in range(5):
            m.record_message("trades", now=T0 + timedelta(seconds=i))
        snap = m.health_snapshot(now=T0 + timedelta(seconds=5))
        assert snap["trades"]["message_count"] == 5

    def test_gap_count_records(self) -> None:
        m = CollectorMonitor()
        m.record_gap("orderbook")
        m.record_gap("orderbook")
        snap = m.health_snapshot(now=T0)
        assert snap["orderbook"]["gap_count"] == 2


class TestHealthSnapshot:
    def test_snapshot_fields(self) -> None:
        m = CollectorMonitor(heartbeat_timeout_seconds=30)
        m.record_message("trades", now=T0)
        snap = m.health_snapshot(now=T0 + timedelta(seconds=5))
        assert "trades" in snap
        entry = snap["trades"]
        assert entry["message_count"] == 1
        assert entry["last_message_at"] == T0.isoformat()
        assert entry["age_seconds"] == 5.0
        assert entry["gap_count"] == 0
        assert entry["healthy"] is True

    def test_snapshot_reports_unhealthy(self) -> None:
        m = CollectorMonitor(heartbeat_timeout_seconds=10)
        m.record_message("trades", now=T0)
        snap = m.health_snapshot(now=T0 + timedelta(seconds=20))
        assert snap["trades"]["healthy"] is False
        assert snap["trades"]["age_seconds"] == 20.0
