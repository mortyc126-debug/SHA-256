"""End-to-end live paper-trading session orchestrator.

Wires together:
    Bybit WS (trades stream)  ──┐
                                ├─→ LiveBarBuilder ─→ LiveFeatureBuilder
                                │                       │
                                │                       ↓
                                │           Distinguisher.predict_proba
                                │                       │
                                │                       ↓
                                │           ThresholdStrategy.step ↔ PaperBroker
                                │                       │
                                └────── periodic stats logger ←────┘

Public entry point: PaperTradingSession.run().
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from scalping_bot.backtest.strategy import ThresholdStrategy
from scalping_bot.live.bar_builder import LiveBarBuilder, OneSecondBar
from scalping_bot.live.feature_pipeline import LiveFeatureBuilder
from scalping_bot.live.paper_broker import PaperBroker
from scalping_bot.market_data.bybit_ws import BybitPublicWS
from scalping_bot.models import Distinguisher

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@dataclass
class PaperTradingSession:
    """One live paper-trading session bound to a specific symbol + model."""

    symbol: str
    model: Distinguisher
    broker: PaperBroker
    strategy: ThresholdStrategy
    feature_window_bars: int = 600
    testnet: bool = False
    feature_cols_override: list[str] | None = None

    _ws: BybitPublicWS = field(init=False)
    _bars: LiveBarBuilder = field(init=False)
    _features: LiveFeatureBuilder = field(init=False)
    _stop_event: threading.Event = field(init=False, default_factory=threading.Event)
    _last_bar_ts: datetime | None = field(init=False, default=None)
    _ticks_seen: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._ws = BybitPublicWS(symbol=self.symbol, depth=50, testnet=self.testnet)
        self._bars = LiveBarBuilder()
        self._features = LiveFeatureBuilder(window_bars=self.feature_window_bars)
        self._bars.on_bar(self._handle_bar)

    # --- Lifecycle ----------------------------------------------------------

    def run(self, duration_seconds: float | None = None) -> None:
        log.info(
            "paper.starting",
            symbol=self.symbol,
            testnet=self.testnet,
            window_bars=self.feature_window_bars,
            equity=self.broker.equity,
        )
        self._ws.start(on_trade=self._handle_trade_msg)

        deadline = (
            time.monotonic() + duration_seconds if duration_seconds is not None else None
        )
        try:
            while not self._stop_event.is_set():
                if deadline is not None and time.monotonic() >= deadline:
                    break
                self._stop_event.wait(timeout=1.0)
                self._log_status_if_due()
        finally:
            self.stop()

    def stop(self) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self._ws.stop()
        # If there's an open position, flatten at last known price
        if self.broker.has_position and self._last_bar_ts is not None:
            # Use the latest bar's close as the exit price proxy
            feat = self._features.build_features()
            if not feat.is_empty():
                last_close = float(feat["close"][-1])
                self.broker.close(self._last_bar_ts, last_close, "session_stop")
        log.info(
            "paper.stopped",
            n_trades=len(self.broker.trades),
            equity=round(self.broker.equity, 4),
            ticks_seen=self._ticks_seen,
            bars_emitted=self._bars.bars_emitted,
        )

    # --- Message handlers ---------------------------------------------------

    def _handle_trade_msg(self, msg: dict[str, Any]) -> None:
        try:
            ts_ms = int(msg["ts"])
            ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
            data = msg.get("data") or []
            if not isinstance(data, list):
                return
            for trade in data:
                self._bars.on_trade(
                    ts=ts,
                    side=str(trade["S"]),
                    price=float(trade["p"]),
                    size=float(trade["v"]),
                )
                self._ticks_seen += 1
        except (KeyError, ValueError, TypeError) as exc:
            log.warning("paper.trade.parse_failed", error=str(exc))

    def _handle_bar(self, bar: OneSecondBar) -> None:
        self._features.add_bar(bar)
        self._last_bar_ts = bar.ts_bar
        self.broker.mark(bar.close)

        if not self._features.warmed_up:
            return
        if not self.broker.can_trade and not self.broker.has_position:
            return  # hard stop, don't enter; closes still allowed

        feat_row = self._features.latest_feature_row()
        if feat_row.is_empty():
            return

        feature_cols = self.feature_cols_override or self.model._fit.feature_cols  # type: ignore[union-attr]
        # The model expects pairwise-augmented columns, but predict_proba
        # internally re-applies pairwise specs, so we just need the base
        # feature columns to be present. Filter to those that the model's
        # pairwise specs reference plus its base feature_cols.
        base_cols = [c for c in feature_cols if c in feat_row.columns]
        if not base_cols:
            return

        try:
            proba = self.model.predict_proba(feat_row)
        except Exception as exc:
            log.warning("paper.predict_failed", error=str(exc))
            return

        classes = self.model.classes_.tolist()
        proba_up = float(proba[0, classes.index(1)]) if 1 in classes else 0.0
        proba_down = float(proba[0, classes.index(-1)]) if -1 in classes else 0.0

        action = self.strategy.step(
            engine=self.broker.engine,
            ts=bar.ts_bar,
            price=float(bar.close),
            proba_up=proba_up,
            proba_down=proba_down,
        )
        log.info(
            "paper.bar",
            ts=bar.ts_bar.isoformat(),
            close=bar.close,
            proba_up=round(proba_up, 4),
            proba_down=round(proba_down, 4),
            action=action.value,
            equity=round(self.broker.equity, 4),
            position_side=(
                self.broker.engine.position.side.value
                if self.broker.engine.position is not None
                else None
            ),
        )

    # --- Periodic stats -----------------------------------------------------

    _last_status_minute: datetime | None = None

    def _log_status_if_due(self) -> None:
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        if self._last_status_minute == now:
            return
        self._last_status_minute = now
        log.info(
            "paper.status",
            ticks=self._ticks_seen,
            bars=self._bars.bars_emitted,
            equity=round(self.broker.equity, 4),
            n_trades=len(self.broker.trades),
            warmed_up=self._features.warmed_up,
            can_trade=self.broker.can_trade,
            has_position=self.broker.has_position,
        )
