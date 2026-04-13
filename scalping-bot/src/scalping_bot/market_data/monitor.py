"""Health monitor for market data streams.

Tracks per-stream message arrival times. A stream that hasn't had a message
for `HEARTBEAT_TIMEOUT_SECONDS` is considered stale; the collector should
log a warning and (optionally) trigger a pause on the kill switch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from scalping_bot.risk.limits import HEARTBEAT_TIMEOUT_SECONDS


@dataclass
class StreamHealth:
    """Per-stream health snapshot."""

    stream: str
    message_count: int = 0
    last_message_at: datetime | None = None
    gap_count: int = 0
    """Number of detected sequence gaps (re-subscriptions needed)."""


class CollectorMonitor:
    """Tracks health of multiple named streams. Thread-unsafe."""

    def __init__(self, heartbeat_timeout_seconds: int = HEARTBEAT_TIMEOUT_SECONDS) -> None:
        self._timeout = timedelta(seconds=heartbeat_timeout_seconds)
        self._streams: dict[str, StreamHealth] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def record_message(self, stream: str, now: datetime | None = None) -> None:
        """Record that a message was received on the named stream."""
        current = now if now is not None else self._now()
        health = self._streams.setdefault(stream, StreamHealth(stream=stream))
        health.message_count += 1
        health.last_message_at = current

    def record_gap(self, stream: str) -> None:
        """Record that a sequence gap was detected on the stream."""
        health = self._streams.setdefault(stream, StreamHealth(stream=stream))
        health.gap_count += 1

    def is_stream_healthy(self, stream: str, now: datetime | None = None) -> bool:
        """True iff stream exists and its last message is within timeout."""
        current = now if now is not None else self._now()
        health = self._streams.get(stream)
        if health is None or health.last_message_at is None:
            return False
        age = current - health.last_message_at
        return age <= self._timeout

    def all_healthy(self, streams: list[str], now: datetime | None = None) -> bool:
        """True iff every stream in the list is healthy."""
        return all(self.is_stream_healthy(s, now=now) for s in streams)

    def health_snapshot(self, now: datetime | None = None) -> dict[str, dict[str, object]]:
        """Dict view for logging / debugging."""
        current = now if now is not None else self._now()
        result: dict[str, dict[str, object]] = {}
        for name, h in self._streams.items():
            age_s: float | None = None
            if h.last_message_at is not None:
                age_s = (current - h.last_message_at).total_seconds()
            result[name] = {
                "message_count": h.message_count,
                "last_message_at": h.last_message_at.isoformat() if h.last_message_at else None,
                "age_seconds": age_s,
                "gap_count": h.gap_count,
                "healthy": self.is_stream_healthy(name, now=current),
            }
        return result

    @property
    def streams(self) -> tuple[str, ...]:
        return tuple(self._streams.keys())
