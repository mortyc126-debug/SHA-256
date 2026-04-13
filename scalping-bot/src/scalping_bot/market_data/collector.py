"""High-level collector: WebSocket ingest → orderbook state → Parquet storage.

Orchestrates bybit_ws, orderbook, recorder, monitor. The point of entry is
`Collector.run()`, which blocks until stopped (SIGINT or explicit call).

Note on orderbook stream behavior: pybit does its own snapshot/delta
reconstruction internally and presents already-merged book states via the
callback. In practice every callback invocation carries `type="snapshot"`
with the current top-N book. Our OrderbookState code still supports the
delta path for future direct-WebSocket use; for now, the delta branch is
mostly defensive (it would trigger on any raw-mode subscriber).
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from scalping_bot.market_data.bybit_ws import BybitPublicWS
from scalping_bot.market_data.monitor import CollectorMonitor
from scalping_bot.market_data.orderbook import (
    OrderbookState,
    SequenceGapError,
    parse_bybit_orderbook_msg,
)
from scalping_bot.market_data.recorder import ParquetRecorder

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

STREAM_TRADES = "trades"
STREAM_ORDERBOOK = "orderbook"
STREAM_TICKERS = "tickers"

SNAPSHOT_CHECKPOINT_INTERVAL_SECONDS = 60.0


class Collector:
    """Run a market-data collection session for a single symbol."""

    def __init__(
        self,
        symbol: str,
        data_dir: Path,
        depth: int = 50,
        testnet: bool = False,
        snapshot_interval_seconds: float = SNAPSHOT_CHECKPOINT_INTERVAL_SECONDS,
    ) -> None:
        self._symbol = symbol
        self._depth = depth

        self._ws = BybitPublicWS(symbol=symbol, depth=depth, testnet=testnet)
        self._recorder = ParquetRecorder(data_dir=data_dir, symbol=symbol)
        self._monitor = CollectorMonitor()
        self._book = OrderbookState(symbol=symbol, depth=depth)

        self._snapshot_interval = snapshot_interval_seconds
        self._last_snapshot_checkpoint: datetime | None = None
        self._stop_event = threading.Event()

    # --- Lifecycle ----------------------------------------------------------

    def run(self, duration_seconds: float | None = None) -> None:
        """Start streams and block until stopped. Flushes on exit."""
        log.info(
            "collector.starting",
            symbol=self._symbol,
            depth=self._depth,
        )
        self._ws.start(
            on_trade=self._handle_trade,
            on_orderbook=self._handle_orderbook,
            on_ticker=self._handle_ticker,
        )

        deadline = None
        if duration_seconds is not None:
            deadline = time.monotonic() + duration_seconds

        try:
            while not self._stop_event.is_set():
                if deadline is not None and time.monotonic() >= deadline:
                    break
                self._stop_event.wait(timeout=1.0)
                self._log_health_if_due()
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop WebSocket, flush recorder buffers."""
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        log.info("collector.stopping", symbol=self._symbol)
        self._ws.stop()
        self._recorder.flush()
        log.info(
            "collector.stopped",
            total_rows=self._recorder.total_rows_written(),
            counts=self._recorder.write_counts(),
        )

    # --- Message handlers ---------------------------------------------------

    def _handle_trade(self, msg: dict[str, Any]) -> None:
        try:
            ts = datetime.fromtimestamp(int(msg["ts"]) / 1000.0, tz=UTC)
            data = msg.get("data") or []
            if not isinstance(data, list):
                return
            for trade in data:
                row = {
                    "trade_time_ms": int(trade["T"]),
                    "side": str(trade["S"]),
                    "price": float(trade["p"]),
                    "size": float(trade["v"]),
                    "trade_id": str(trade["i"]),
                }
                self._recorder.record_trade(ts=ts, row=row)
            self._monitor.record_message(STREAM_TRADES)
        except (KeyError, ValueError, TypeError) as exc:
            log.warning("trade.parse_failed", error=str(exc), msg_sample=_safe_sample(msg))

    def _handle_orderbook(self, msg: dict[str, Any]) -> None:
        try:
            msg_type, bids, asks, update_id, ts = parse_bybit_orderbook_msg(msg)
        except (KeyError, ValueError, TypeError) as exc:
            log.warning("orderbook.parse_failed", error=str(exc), msg_sample=_safe_sample(msg))
            return

        try:
            if msg_type == "snapshot":
                self._book.apply_snapshot(bids=bids, asks=asks, update_id=update_id, ts=ts)
                snapshot = self._book.snapshot_view()
                self._recorder.record_orderbook_snapshot(ts=ts, row=snapshot)
                self._last_snapshot_checkpoint = ts
            else:
                self._book.apply_delta(bids=bids, asks=asks, update_id=update_id, ts=ts)
                self._recorder.record_orderbook_delta(
                    ts=ts,
                    row={
                        "update_id": update_id,
                        "bids": [list(pair) for pair in bids],
                        "asks": [list(pair) for pair in asks],
                    },
                )
                self._maybe_record_snapshot_checkpoint(ts)
        except SequenceGapError as exc:
            log.warning(
                "orderbook.gap_detected",
                error=str(exc),
                update_id=update_id,
                last_update_id=self._book.last_update_id,
            )
            self._monitor.record_gap(STREAM_ORDERBOOK)
            # Reset state and wait for next snapshot. pybit will keep the
            # stream open; Bybit sends a fresh snapshot periodically. If we
            # want faster recovery we could re-subscribe here.
            self._book = OrderbookState(symbol=self._symbol, depth=self._depth)
            return

        self._monitor.record_message(STREAM_ORDERBOOK)

    def _handle_ticker(self, msg: dict[str, Any]) -> None:
        try:
            ts = datetime.fromtimestamp(int(msg["ts"]) / 1000.0, tz=UTC)
            data = msg.get("data") or {}
            if not isinstance(data, dict):
                return
            # Tickers arrive as partial updates; record the whole payload as-is.
            row: dict[str, object] = dict(data)
            self._recorder.record_ticker(ts=ts, row=row)
            self._monitor.record_message(STREAM_TICKERS)
        except (KeyError, ValueError, TypeError) as exc:
            log.warning("ticker.parse_failed", error=str(exc), msg_sample=_safe_sample(msg))

    # --- Periodic tasks -----------------------------------------------------

    def _maybe_record_snapshot_checkpoint(self, ts: datetime) -> None:
        if self._last_snapshot_checkpoint is None:
            return
        elapsed = (ts - self._last_snapshot_checkpoint).total_seconds()
        if elapsed < self._snapshot_interval:
            return
        self._recorder.record_orderbook_snapshot(ts=ts, row=self._book.snapshot_view())
        self._last_snapshot_checkpoint = ts

    def _log_health_if_due(self) -> None:
        # Log once per minute at most; cheap enough to always log from here.
        now = datetime.now(UTC)
        # Simple rate-limit via rounded-minute trick
        if getattr(self, "_last_health_log_minute", None) == now.replace(
            second=0, microsecond=0
        ):
            return
        self._last_health_log_minute = now.replace(second=0, microsecond=0)
        log.info("collector.health", snapshot=self._monitor.health_snapshot(now=now))

    # --- Introspection -------------------------------------------------------

    @property
    def monitor(self) -> CollectorMonitor:
        return self._monitor

    @property
    def orderbook(self) -> OrderbookState:
        return self._book

    @property
    def recorder(self) -> ParquetRecorder:
        return self._recorder


def _safe_sample(msg: dict[str, Any], max_len: int = 200) -> str:
    s = str(msg)
    return s[:max_len] + ("..." if len(s) > max_len else "")
