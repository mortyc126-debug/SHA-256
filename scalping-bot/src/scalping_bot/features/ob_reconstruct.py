"""Reconstruct orderbook state from saved snapshot+delta Parquets and
sample features at a regular time grid.

Bybit publishes ~1 snapshot per hour + stream of deltas. To compute OBI
and other features, we walk the delta stream through `OrderbookState`
and sample features at bar boundaries.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

import polars as pl

from scalping_bot.market_data.orderbook import OrderbookState, SequenceGapError


def _row_bids_asks(
    row: dict[str, Any],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    bids_raw = cast("list[list[float]]", row.get("bids") or [])
    asks_raw = cast("list[list[float]]", row.get("asks") or [])
    bids = [(float(p), float(s)) for p, s in bids_raw]
    asks = [(float(p), float(s)) for p, s in asks_raw]
    return bids, asks


def reconstruct_and_sample(
    snapshot_df: pl.DataFrame,
    delta_df: pl.DataFrame,
    bar_seconds: float = 1.0,
    levels_list: tuple[int, ...] = (5, 10, 25),
) -> pl.DataFrame:
    """Replay deltas onto initial snapshot; emit one feature row per bar.

    Features per bar (as of last update within the bar):
        best_bid, best_ask, mid, spread_bps
        obi_{n}, depth_bid_{n}, depth_ask_{n}, depth_skew_{n}
    """
    if snapshot_df.is_empty() and delta_df.is_empty():
        return pl.DataFrame()

    book = OrderbookState(symbol="", depth=max(levels_list))

    # Apply the earliest snapshot to seed, then process subsequent messages
    # in strict update_id order.
    events: list[tuple[int, datetime, str, list[tuple[float, float]], list[tuple[float, float]]]] = []
    for row in snapshot_df.iter_rows(named=True):
        events.append((row["update_id"], row["ts"], "snapshot", *_row_bids_asks(row)))
    for row in delta_df.iter_rows(named=True):
        events.append((row["update_id"], row["ts"], "delta", *_row_bids_asks(row)))

    events.sort(key=lambda e: e[0])

    rows: list[dict[str, object]] = []
    current_bar_start: datetime | None = None

    def _emit_bar(ts: datetime) -> None:
        """Emit a feature row for the book state at time `ts`."""
        bb = book.best_bid()
        ba = book.best_ask()
        if bb is None or ba is None:
            return

        mid = (bb[0] + ba[0]) / 2
        spread_bps = (ba[0] - bb[0]) / mid * 10_000.0 if mid > 0 else None

        row: dict[str, object] = {
            "ts_bar": ts,
            "best_bid": bb[0],
            "best_ask": ba[0],
            "mid": mid,
            "spread_bps": spread_bps,
        }
        # Use OrderbookState helpers for consistent computation
        for n in levels_list:
            top_bids = book.top_n_bids(n)
            top_asks = book.top_n_asks(n)
            dbid = sum(size for _, size in top_bids)
            dask = sum(size for _, size in top_asks)
            total = dbid + dask
            row[f"obi_{n}"] = (dbid - dask) / total if total > 0 else None
            row[f"depth_bid_{n}"] = dbid
            row[f"depth_ask_{n}"] = dask
            if dbid > 0 and dask > 0:
                import math

                row[f"depth_skew_{n}"] = math.log(dbid / dask)
            else:
                row[f"depth_skew_{n}"] = None
        rows.append(row)

    step = timedelta(seconds=bar_seconds)

    for uid, ts, kind, bids, asks in events:
        if current_bar_start is None:
            # Seed: floor to bar boundary
            current_bar_start = ts.replace(microsecond=0)
            if bar_seconds < 1:
                # crude sub-second handling: align to the nearest multiple
                ms = int(ts.microsecond / (bar_seconds * 1e6)) * int(bar_seconds * 1e6)
                current_bar_start = ts.replace(microsecond=ms)

        # Emit rows for bars we've crossed since last event
        while ts - current_bar_start >= step:
            current_bar_start = current_bar_start + step
            _emit_bar(current_bar_start)

        try:
            if kind == "snapshot":
                book.apply_snapshot(bids=bids, asks=asks, update_id=uid, ts=ts)
            else:
                book.apply_delta(bids=bids, asks=asks, update_id=uid, ts=ts)
        except SequenceGapError:
            # Bybit always sends a fresh snapshot at some cadence; skip until
            # we see one. We reset the book to force re-seed.
            book = OrderbookState(symbol="", depth=max(levels_list))

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).sort("ts_bar")


__all__ = ["reconstruct_and_sample"]
