"""Orderbook state reconstruction from Bybit snapshot + delta stream.

Bybit's public orderbook stream works as follows:
- First message after subscribe has `type="snapshot"`, contains full top-N book.
- Subsequent messages have `type="delta"`, contain only changed price levels.
- Each message carries `u` (update id) which is monotonically increasing.
- If `u` has a gap, local state is inconsistent; must re-subscribe.

A delta update with `size=0` at a price level means remove that level.
Otherwise it means set that price level to the given size (replace, not add).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

Price = float
Size = float


class SequenceGapError(RuntimeError):
    """Raised when orderbook delta update_id is non-monotonic or has a gap.

    Recovery is to discard state and re-subscribe (Bybit will send a fresh
    snapshot on subscription).
    """


@dataclass
class OrderbookState:
    """Mutable top-of-book state. Bids/asks are dicts price -> size.

    `apply_snapshot` initializes; `apply_delta` incrementally updates.
    """

    symbol: str
    depth: int = 50

    _bids: dict[Price, Size] = field(default_factory=dict)
    _asks: dict[Price, Size] = field(default_factory=dict)
    _last_update_id: int = -1
    _last_update_ts: datetime | None = None
    _initialized: bool = False

    # --- Construction -------------------------------------------------------

    def apply_snapshot(
        self,
        bids: list[tuple[Price, Size]],
        asks: list[tuple[Price, Size]],
        update_id: int,
        ts: datetime,
    ) -> None:
        """Replace entire book state from a snapshot message."""
        self._bids = {p: s for p, s in bids if s > 0}
        self._asks = {p: s for p, s in asks if s > 0}
        self._last_update_id = update_id
        self._last_update_ts = ts
        self._initialized = True

    # --- Incremental --------------------------------------------------------

    def apply_delta(
        self,
        bids: list[tuple[Price, Size]],
        asks: list[tuple[Price, Size]],
        update_id: int,
        ts: datetime,
    ) -> None:
        """Apply a delta update. Raises SequenceGapError on gap or regression.

        Rules:
          - `update_id` must be strictly greater than the last one.
          - Bybit only guarantees monotonic `u`, not `u == prev_u + 1` in all
            cases. We treat any forward-moving `u` as valid.
          - A size of 0 at a price level means remove that level.
          - Otherwise the size replaces whatever was there.
        """
        if not self._initialized:
            raise SequenceGapError("delta received before snapshot")

        if update_id <= self._last_update_id:
            raise SequenceGapError(
                f"non-monotonic update_id: got {update_id}, last was {self._last_update_id}"
            )

        for price, size in bids:
            if size == 0:
                self._bids.pop(price, None)
            else:
                self._bids[price] = size

        for price, size in asks:
            if size == 0:
                self._asks.pop(price, None)
            else:
                self._asks[price] = size

        self._last_update_id = update_id
        self._last_update_ts = ts

    # --- Queries ------------------------------------------------------------

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def last_update_id(self) -> int:
        return self._last_update_id

    @property
    def last_update_ts(self) -> datetime | None:
        return self._last_update_ts

    def best_bid(self) -> tuple[Price, Size] | None:
        """Highest bid price and its size, or None if no bids."""
        if not self._bids:
            return None
        price = max(self._bids)
        return price, self._bids[price]

    def best_ask(self) -> tuple[Price, Size] | None:
        """Lowest ask price and its size, or None if no asks."""
        if not self._asks:
            return None
        price = min(self._asks)
        return price, self._asks[price]

    def mid_price(self) -> Price | None:
        """Mid price = (best_bid + best_ask) / 2, or None if book empty."""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return None
        return (bid[0] + ask[0]) / 2

    def spread_bps(self) -> float | None:
        """Bid-ask spread in basis points of mid, or None if book empty."""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return None
        mid = (bid[0] + ask[0]) / 2
        if mid == 0:
            return None
        return (ask[0] - bid[0]) / mid * 10_000.0

    def top_n_bids(self, n: int) -> list[tuple[Price, Size]]:
        """Top-n bids sorted by price descending."""
        sorted_prices = sorted(self._bids.keys(), reverse=True)[:n]
        return [(p, self._bids[p]) for p in sorted_prices]

    def top_n_asks(self, n: int) -> list[tuple[Price, Size]]:
        """Top-n asks sorted by price ascending."""
        sorted_prices = sorted(self._asks.keys())[:n]
        return [(p, self._asks[p]) for p in sorted_prices]

    def imbalance(self, levels: int = 5) -> float | None:
        """Order book imbalance using top `levels` on each side.

        Formula: (bid_vol - ask_vol) / (bid_vol + ask_vol).
        Range: [-1, +1]. Positive = more bid pressure.
        Returns None if either side is empty.
        """
        bids = self.top_n_bids(levels)
        asks = self.top_n_asks(levels)
        if not bids or not asks:
            return None
        bid_vol = sum(size for _, size in bids)
        ask_vol = sum(size for _, size in asks)
        total = bid_vol + ask_vol
        if total == 0:
            return None
        return (bid_vol - ask_vol) / total

    def snapshot_view(self) -> dict[str, object]:
        """Serializable snapshot for recording. Only top-`depth` levels on each side."""
        return {
            "symbol": self.symbol,
            "update_id": self._last_update_id,
            "ts": self._last_update_ts.isoformat() if self._last_update_ts else None,
            "bids": self.top_n_bids(self.depth),
            "asks": self.top_n_asks(self.depth),
        }


# --- Message parsing --------------------------------------------------------

# Bybit message types for orderbook stream
MSG_TYPE_SNAPSHOT: Final[str] = "snapshot"
MSG_TYPE_DELTA: Final[str] = "delta"


def parse_bybit_orderbook_msg(
    msg: dict[str, object],
) -> tuple[str, list[tuple[float, float]], list[tuple[float, float]], int, datetime]:
    """Parse a Bybit orderbook WebSocket message.

    Returns: (msg_type, bids, asks, update_id, timestamp)

    Raises KeyError or ValueError on malformed input (caller should log and skip).
    """
    msg_type = str(msg["type"])
    if msg_type not in (MSG_TYPE_SNAPSHOT, MSG_TYPE_DELTA):
        raise ValueError(f"unexpected orderbook msg type: {msg_type!r}")

    data = msg["data"]
    if not isinstance(data, dict):
        raise ValueError(f"expected dict data, got {type(data).__name__}")

    raw_bids = data.get("b", [])
    raw_asks = data.get("a", [])
    if not isinstance(raw_bids, list) or not isinstance(raw_asks, list):
        raise ValueError("b and a fields must be lists")

    bids: list[tuple[float, float]] = [(float(p), float(s)) for p, s in raw_bids]
    asks: list[tuple[float, float]] = [(float(p), float(s)) for p, s in raw_asks]

    u_raw = data["u"]
    ts_raw = msg["ts"]
    if not isinstance(u_raw, (int, str, float)) or not isinstance(ts_raw, (int, str, float)):
        raise ValueError("u and ts must be numeric or string-numeric")
    update_id = int(u_raw)
    ts_ms = int(ts_raw)
    ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)

    return msg_type, bids, asks, update_id, ts
