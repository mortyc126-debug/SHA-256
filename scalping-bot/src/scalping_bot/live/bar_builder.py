"""Live 1-second bar accumulator.

Receives trade ticks one at a time (ts, side, price, size) and emits a
finalized OneSecondBar whenever the second boundary is crossed. Stateless
between bars except for the in-progress bar.

Bar timestamp is the start of the second (UTC).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OneSecondBar:
    """Aggregated trade activity over one wall-clock second."""

    ts_bar: datetime
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: float
    buy_volume: float
    sell_volume: float
    trade_count: int


@dataclass
class _Acc:
    """Mutable in-progress bar accumulator."""

    open: float
    high: float
    low: float
    close: float
    sum_pv: float = 0.0
    volume: float = 0.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    trade_count: int = 0


def _floor_second(ts: datetime) -> datetime:
    return ts.replace(microsecond=0)


@dataclass
class LiveBarBuilder:
    """Bar accumulator. Call `on_trade(...)` per tick.

    When a trade arrives in a new second, the previous bar is finalized
    and yielded via the callback registered with `on_bar(...)`.
    """

    _on_bar: Callable[[OneSecondBar], None] | None = None
    _current_bar_start: datetime | None = None
    _acc: _Acc | None = None
    _bars_emitted: int = 0

    def on_bar(self, callback: Callable[[OneSecondBar], None]) -> None:
        """Register a single callback for finalized bars. Replaces previous."""
        self._on_bar = callback

    def on_trade(self, ts: datetime, side: str, price: float, size: float) -> None:
        """Fold a trade tick into the in-progress bar."""
        if ts.tzinfo is None:
            raise ValueError("trade ts must be tz-aware")

        bar_start = _floor_second(ts)
        if self._current_bar_start is None:
            self._current_bar_start = bar_start
            self._acc = _Acc(open=price, high=price, low=price, close=price)
        elif bar_start != self._current_bar_start:
            self._finalize_and_emit()
            self._current_bar_start = bar_start
            self._acc = _Acc(open=price, high=price, low=price, close=price)

        assert self._acc is not None
        self._acc.high = max(self._acc.high, price)
        self._acc.low = min(self._acc.low, price)
        self._acc.close = price
        self._acc.sum_pv += price * size
        self._acc.volume += size
        if side == "Buy":
            self._acc.buy_volume += size
        elif side == "Sell":
            self._acc.sell_volume += size
        self._acc.trade_count += 1

    def force_flush(self, until: datetime | None = None) -> None:
        """Emit the in-progress bar (if any) and any empty bars up to `until`.

        Useful for end-of-stream cleanup or filling gaps if no trades
        arrived in a second.
        """
        if self._acc is None:
            return
        self._finalize_and_emit()

    def _finalize_and_emit(self) -> None:
        if self._acc is None or self._current_bar_start is None:
            return
        bar = OneSecondBar(
            ts_bar=self._current_bar_start,
            open=self._acc.open,
            high=self._acc.high,
            low=self._acc.low,
            close=self._acc.close,
            vwap=(self._acc.sum_pv / self._acc.volume) if self._acc.volume > 0 else self._acc.close,
            volume=self._acc.volume,
            buy_volume=self._acc.buy_volume,
            sell_volume=self._acc.sell_volume,
            trade_count=self._acc.trade_count,
        )
        self._bars_emitted += 1
        self._acc = None
        if self._on_bar is not None:
            self._on_bar(bar)

    @property
    def bars_emitted(self) -> int:
        return self._bars_emitted
