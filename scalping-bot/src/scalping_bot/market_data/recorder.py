"""Parquet recorder with date-partitioned layout and batched writes.

Storage layout:
    data_dir/
        trades/date=YYYY-MM-DD/BTCUSDT_HH.parquet
        orderbook/date=YYYY-MM-DD/BTCUSDT_HH.parquet    (deltas only)
        orderbook_snapshots/date=YYYY-MM-DD/BTCUSDT_HH.parquet
        tickers/date=YYYY-MM-DD/BTCUSDT_HH.parquet

Files rotate hourly so recovery after a crash is bounded to at most
one partial file. Buffers flush whenever:
  - `batch_size` rows accumulated, OR
  - `flush_interval_seconds` elapsed since last flush, OR
  - `flush()` is called explicitly (shutdown path).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import polars as pl

DEFAULT_BATCH_SIZE: Final[int] = 1000
DEFAULT_FLUSH_INTERVAL_SECONDS: Final[float] = 60.0


@dataclass
class _StreamBuffer:
    """In-memory buffer for one stream kind."""

    name: str
    rows: list[dict[str, object]] = field(default_factory=list)
    last_flush_at: datetime | None = None


class ParquetRecorder:
    """Buffer and periodically flush market-data rows to hour-partitioned Parquet."""

    def __init__(
        self,
        data_dir: Path,
        symbol: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        flush_interval_seconds: float = DEFAULT_FLUSH_INTERVAL_SECONDS,
    ) -> None:
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        if flush_interval_seconds <= 0:
            raise ValueError(
                f"flush_interval_seconds must be positive, got {flush_interval_seconds}"
            )

        self._data_dir = Path(data_dir)
        self._symbol = symbol
        self._batch_size = batch_size
        self._flush_interval_seconds = flush_interval_seconds
        self._buffers: dict[str, _StreamBuffer] = {}
        self._write_counts: dict[str, int] = {}

    # --- Recording entrypoints ----------------------------------------------

    def record_trade(self, ts: datetime, row: dict[str, object]) -> None:
        """Record a single trade row. Expects a flat dict with basic types."""
        self._add_row("trades", ts, row)

    def record_orderbook_delta(self, ts: datetime, row: dict[str, object]) -> None:
        """Record an orderbook delta (bids, asks, update_id, ts)."""
        self._add_row("orderbook", ts, row)

    def record_orderbook_snapshot(self, ts: datetime, row: dict[str, object]) -> None:
        """Record an orderbook snapshot (full top-N book)."""
        self._add_row("orderbook_snapshots", ts, row)

    def record_ticker(self, ts: datetime, row: dict[str, object]) -> None:
        """Record a ticker update (lastPrice, fundingRate, markPrice, etc.)."""
        self._add_row("tickers", ts, row)

    # --- Internals ----------------------------------------------------------

    def _add_row(self, stream: str, ts: datetime, row: dict[str, object]) -> None:
        if ts.tzinfo is None:
            raise ValueError("ts must be tz-aware")
        buf = self._buffers.setdefault(stream, _StreamBuffer(name=stream))
        # Stamp each row with ingest time for later alignment checks
        row_out = {"ts": ts, **row}
        buf.rows.append(row_out)

        if self._should_flush(buf):
            self._flush_buffer(stream, buf, now=ts)

    def _should_flush(self, buf: _StreamBuffer) -> bool:
        if len(buf.rows) >= self._batch_size:
            return True
        if buf.last_flush_at is None:
            # First row in this buffer; no time-based flush yet
            return False
        last_ts = buf.rows[-1]["ts"]
        assert isinstance(last_ts, datetime)
        age = (last_ts - buf.last_flush_at).total_seconds()
        return age >= self._flush_interval_seconds

    def _flush_buffer(self, stream: str, buf: _StreamBuffer, now: datetime) -> None:
        if not buf.rows:
            buf.last_flush_at = now
            return

        df = pl.DataFrame(buf.rows)
        path = self._file_path_for(stream, now)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            # Append by concat + rewrite. Simpler than streaming append; OK at
            # hourly rotation cadence.
            existing = pl.read_parquet(path)
            df = pl.concat([existing, df], how="vertical_relaxed")

        df.write_parquet(path, compression="snappy")

        self._write_counts[stream] = self._write_counts.get(stream, 0) + len(buf.rows)
        buf.rows.clear()
        buf.last_flush_at = now

    def _file_path_for(self, stream: str, ts: datetime) -> Path:
        date_str = ts.strftime("%Y-%m-%d")
        hour = ts.strftime("%H")
        return (
            self._data_dir
            / stream
            / f"date={date_str}"
            / f"{self._symbol}_{hour}.parquet"
        )

    # --- Lifecycle ----------------------------------------------------------

    def flush(self, now: datetime | None = None) -> None:
        """Force flush of all non-empty buffers. Call on shutdown."""
        current = now if now is not None else datetime.now(UTC)
        for stream, buf in self._buffers.items():
            if buf.rows:
                self._flush_buffer(stream, buf, now=current)

    def total_rows_written(self) -> int:
        return sum(self._write_counts.values())

    def write_counts(self) -> dict[str, int]:
        return dict(self._write_counts)

    def buffered_counts(self) -> dict[str, int]:
        return {s: len(b.rows) for s, b in self._buffers.items()}

    # --- Read helpers for tests / downstream --------------------------------

    @staticmethod
    def iter_files(data_dir: Path, stream: str) -> Iterable[Path]:
        """Walk all .parquet files under `data_dir/stream/`. Useful in tests."""
        base = Path(data_dir) / stream
        if not base.exists():
            return []
        return base.rglob("*.parquet")
