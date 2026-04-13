"""Orderbook-based microstructure features.

Input is a DataFrame of orderbook snapshots with schema:
    ts          : datetime[UTC]
    update_id   : int64
    bids        : list[list[f64]]  — [[price, size], ...]
    asks        : list[list[f64]]  — [[price, size], ...]

Features computed per snapshot:
    best_bid, best_ask, mid, spread_bps
    obi_n           = (bid_vol_topN - ask_vol_topN) / (bid_vol_topN + ask_vol_topN)
    depth_bid_n     = sum of size on top N bid levels
    depth_ask_n     = sum of size on top N ask levels
    depth_skew_n    = log(depth_bid_n / depth_ask_n)

Then aligned to bar grid by `align_to_bars`, averaging within each bar.
"""

from __future__ import annotations

import polars as pl


def _top_n_sum(levels: list[list[float]], n: int, side: str) -> float:
    """Sum of sizes on top-N levels. `side` determines sort order."""
    if not levels:
        return 0.0
    if side == "bid":
        sorted_levels = sorted(levels, key=lambda x: -x[0])
    else:
        sorted_levels = sorted(levels, key=lambda x: x[0])
    return float(sum(row[1] for row in sorted_levels[:n] if row[1] > 0))


def _best_price(levels: list[list[float]], side: str) -> float | None:
    """Best bid (max price) or best ask (min price)."""
    if not levels:
        return None
    valid = [row for row in levels if row[1] > 0]
    if not valid:
        return None
    if side == "bid":
        return max(row[0] for row in valid)
    return min(row[0] for row in valid)


def snapshot_features(
    snapshots: pl.DataFrame,
    levels_list: tuple[int, ...] = (5, 10, 25),
) -> pl.DataFrame:
    """Add per-snapshot microstructure features.

    Returns a frame with columns:
        ts, update_id, best_bid, best_ask, mid, spread_bps,
        obi_{n}, depth_bid_{n}, depth_ask_{n}, depth_skew_{n} for each n
    """
    if snapshots.is_empty():
        return snapshots

    if not {"ts", "bids", "asks"}.issubset(snapshots.columns):
        raise ValueError("snapshots must have columns ts, bids, asks")

    bids_series = snapshots["bids"].to_list()
    asks_series = snapshots["asks"].to_list()

    best_bids: list[float | None] = []
    best_asks: list[float | None] = []
    mids: list[float | None] = []
    spreads: list[float | None] = []
    obi_by_n: dict[int, list[float | None]] = {n: [] for n in levels_list}
    depth_bid_by_n: dict[int, list[float]] = {n: [] for n in levels_list}
    depth_ask_by_n: dict[int, list[float]] = {n: [] for n in levels_list}

    for bids, asks in zip(bids_series, asks_series, strict=True):
        bb = _best_price(bids or [], "bid")
        ba = _best_price(asks or [], "ask")
        best_bids.append(bb)
        best_asks.append(ba)
        if bb is None or ba is None or bb >= ba:
            mids.append(None)
            spreads.append(None)
        else:
            mid = (bb + ba) / 2
            mids.append(mid)
            spreads.append((ba - bb) / mid * 10_000.0)

        for n in levels_list:
            dbid = _top_n_sum(bids or [], n, "bid")
            dask = _top_n_sum(asks or [], n, "ask")
            depth_bid_by_n[n].append(dbid)
            depth_ask_by_n[n].append(dask)
            total = dbid + dask
            if total > 0:
                obi_by_n[n].append((dbid - dask) / total)
            else:
                obi_by_n[n].append(None)

    out_cols: dict[str, object] = {
        "ts": snapshots["ts"],
        "update_id": snapshots["update_id"] if "update_id" in snapshots.columns else None,
        "best_bid": best_bids,
        "best_ask": best_asks,
        "mid": mids,
        "spread_bps": spreads,
    }
    if out_cols["update_id"] is None:
        del out_cols["update_id"]

    for n in levels_list:
        out_cols[f"obi_{n}"] = obi_by_n[n]
        out_cols[f"depth_bid_{n}"] = depth_bid_by_n[n]
        out_cols[f"depth_ask_{n}"] = depth_ask_by_n[n]

    df = pl.DataFrame(out_cols)

    # Depth skew = log(bid/ask); safe against zeros
    for n in levels_list:
        df = df.with_columns(
            pl.when((pl.col(f"depth_bid_{n}") > 0) & (pl.col(f"depth_ask_{n}") > 0))
            .then((pl.col(f"depth_bid_{n}") / pl.col(f"depth_ask_{n}")).log())
            .otherwise(None)
            .alias(f"depth_skew_{n}")
        )
    return df


def align_to_bars(
    snapshot_features_df: pl.DataFrame,
    bar_seconds: float = 1.0,
) -> pl.DataFrame:
    """Aggregate per-snapshot features to fixed-width time bars (mean).

    One row per bar. Columns preserved (except update_id which is dropped),
    numeric ones averaged, `ts` becomes `ts_bar` at the left edge.
    """
    if snapshot_features_df.is_empty():
        return snapshot_features_df.rename({"ts": "ts_bar"}) if "ts" in snapshot_features_df.columns else snapshot_features_df

    interval = f"{int(bar_seconds * 1000)}ms"

    numeric = [
        c
        for c, dt in snapshot_features_df.schema.items()
        if dt.is_numeric() and c != "update_id"
    ]

    return (
        snapshot_features_df.sort("ts")
        .group_by_dynamic("ts", every=interval, closed="left", label="left")
        .agg([pl.col(c).mean().alias(c) for c in numeric])
        .rename({"ts": "ts_bar"})
    )


def join_to_feature_matrix(
    trade_features: pl.DataFrame,
    ob_features: pl.DataFrame,
    on: str = "ts_bar",
) -> pl.DataFrame:
    """Left-join orderbook features onto the trade-bar feature matrix.

    Forward-fills orderbook columns so bars without a concurrent snapshot
    carry the most recent known value.
    """
    if ob_features.is_empty():
        return trade_features

    joined = trade_features.sort(on).join(
        ob_features.sort(on), on=on, how="left"
    )

    ob_cols = [c for c in ob_features.columns if c != on]
    return joined.with_columns(
        [pl.col(c).forward_fill() for c in ob_cols]
    )


__all__ = [
    "align_to_bars",
    "join_to_feature_matrix",
    "snapshot_features",
]
