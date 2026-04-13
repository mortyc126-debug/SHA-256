"""Convert downloaded Bybit archives to our canonical Parquet layout.

Trades CSV schema (Bybit public.bybit.com):
    timestamp, symbol, side, size, price, tickDirection, trdMatchID,
    grossValue, homeNotional, foreignNotional

Timestamps are Unix seconds with sub-second precision (fractional).

Orderbook ZIP archives contain JSONL with records of shape:
    {
      "ts": 1748736001234,            # server timestamp (ms)
      "cts": 1748736001235,           # client timestamp (ms)
      "type": "snapshot" | "delta",
      "data": {
          "s": "BTCUSDT",
          "b": [["price","size"], ...],
          "a": [["price","size"], ...],
          "u": 12345, "seq": 98765
      }
    }

Output layout (to match live collector):
    data_dir/trades/date=YYYY-MM-DD/SYMBOL_HH.parquet
    data_dir/orderbook/date=YYYY-MM-DD/SYMBOL_HH.parquet
    data_dir/orderbook_snapshots/date=YYYY-MM-DD/SYMBOL_HH.parquet
"""

from __future__ import annotations

import gzip
import json
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

BATCH_ROWS = 50_000
"""Flush every N rows to bound peak memory to ~10-50 MB per batch."""


def convert_trades_to_parquet(
    csv_gz_path: Path,
    symbol: str,
    out_root: Path,
) -> Path:
    """Parse a Bybit trades CSV gz file and write an hourly-partitioned Parquet.

    All rows go under the same date partition. For typical daily files the
    first timestamp's date defines the partition. Files are written as one
    Parquet per hour (like the live collector).

    Returns the date directory that was written to.
    """
    # polars accepts compressed bytes directly
    raw_bytes = gzip.decompress(Path(csv_gz_path).read_bytes())
    df = pl.read_csv(
        raw_bytes,
        has_header=True,
        schema_overrides={
            "timestamp": pl.Float64(),
            "symbol": pl.Utf8(),
            "side": pl.Utf8(),
            "size": pl.Float64(),
            "price": pl.Float64(),
            "trdMatchID": pl.Utf8(),
        },
    )

    # Convert timestamps (seconds with fractional) to UTC datetime microseconds
    df = df.with_columns(
        ts=pl.from_epoch(
            (pl.col("timestamp") * 1_000_000).cast(pl.Int64),
            time_unit="us",
        ).dt.replace_time_zone("UTC"),
        trade_time_ms=(pl.col("timestamp") * 1000).cast(pl.Int64),
    )

    out = df.select(
        [
            "ts",
            "trade_time_ms",
            pl.col("side"),
            pl.col("price").cast(pl.Float64),
            pl.col("size").cast(pl.Float64),
            pl.col("trdMatchID").alias("trade_id"),
        ]
    )

    if out.is_empty():
        return Path()

    # Files are typically a single UTC day. But the day might span multiple
    # hourly partitions. Add helpers and write per (date, hour).
    out = out.with_columns(
        _date_str=pl.col("ts").dt.strftime("%Y-%m-%d"),
        _hour_str=pl.col("ts").dt.strftime("%H"),
    )

    stream_dir = Path(out_root) / "trades"
    first_date_dir: Path | None = None

    for (date_str, hour_str), group in out.group_by(["_date_str", "_hour_str"]):
        date_dir = stream_dir / f"date={date_str}"
        date_dir.mkdir(parents=True, exist_ok=True)
        dest = date_dir / f"{symbol}_{hour_str}.parquet"
        write_df = group.drop(["_date_str", "_hour_str"])

        if dest.exists():
            existing = pl.read_parquet(dest)
            write_df = pl.concat([existing, write_df], how="vertical_relaxed")

        write_df.write_parquet(dest, compression="snappy")
        if first_date_dir is None:
            first_date_dir = date_dir

    return first_date_dir if first_date_dir is not None else Path()


def _iter_orderbook_records(zip_path: Path) -> Iterator[dict[str, object]]:
    """Yield JSONL records from a Bybit orderbook ZIP one at a time.

    Streaming — memory stays bounded regardless of archive size. These
    archives expand to multi-GB JSONL from ~300 MB zip, so materializing
    them is not an option on typical laptops.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        if not names:
            return
        with zf.open(names[0]) as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _ob_row_from_record(rec: dict[str, object]) -> dict[str, object] | None:
    """Convert one JSONL record into a flat Parquet row. Returns None on malformed."""
    try:
        ts_raw = rec.get("ts") or rec.get("cts")
        if not isinstance(ts_raw, (int, float, str)):
            return None
        ts_ms = int(ts_raw)

        data = rec["data"]
        if not isinstance(data, dict):
            return None

        bids_raw = data.get("b", []) or []
        asks_raw = data.get("a", []) or []
        bids = [[float(p), float(s)] for p, s in bids_raw]
        asks = [[float(p), float(s)] for p, s in asks_raw]
        update_id = int(data["u"])
        msg_type = str(rec.get("type", "delta"))
    except (KeyError, ValueError, TypeError):
        return None

    return {
        "ts": datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC),
        "update_id": update_id,
        "type": msg_type,
        "bids": bids,
        "asks": asks,
    }


def convert_orderbook_to_parquet(
    zip_path: Path,
    symbol: str,
    out_root: Path,
) -> Path:
    """Stream a Bybit orderbook ZIP into hourly Parquet files.

    Splits records into two streams:
      - `orderbook`           : delta records
      - `orderbook_snapshots` : snapshot records

    Memory is bounded: we buffer `BATCH_ROWS` rows, flush, clear.
    """
    buffer: list[dict[str, object]] = []
    first_date_dir: Path | None = None

    for rec in _iter_orderbook_records(zip_path):
        row = _ob_row_from_record(rec)
        if row is None:
            continue
        buffer.append(row)
        if len(buffer) >= BATCH_ROWS:
            written = _flush_ob_batch(buffer, symbol, out_root)
            if written is not None and first_date_dir is None:
                first_date_dir = written
            buffer.clear()

    if buffer:
        written = _flush_ob_batch(buffer, symbol, out_root)
        if written is not None and first_date_dir is None:
            first_date_dir = written

    return first_date_dir if first_date_dir is not None else Path()


def _flush_ob_batch(
    rows: list[dict[str, object]],
    symbol: str,
    out_root: Path,
) -> Path | None:
    """Write a batch of orderbook rows, split by type and hour. Returns a representative dir."""
    if not rows:
        return None

    df = pl.DataFrame(rows).with_columns(
        _date_str=pl.col("ts").dt.strftime("%Y-%m-%d"),
        _hour_str=pl.col("ts").dt.strftime("%H"),
    )

    first_dir: Path | None = None

    for msg_type, stream in (("snapshot", "orderbook_snapshots"), ("delta", "orderbook")):
        sub = df.filter(pl.col("type") == msg_type)
        if sub.is_empty():
            continue

        for (date_str, hour_str), group in sub.group_by(["_date_str", "_hour_str"]):
            date_dir = Path(out_root) / stream / f"date={date_str}"
            date_dir.mkdir(parents=True, exist_ok=True)
            dest = date_dir / f"{symbol}_{hour_str}.parquet"
            write_df = group.drop(["_date_str", "_hour_str", "type"])

            if dest.exists():
                existing = pl.read_parquet(dest)
                write_df = pl.concat([existing, write_df], how="vertical_relaxed")

            write_df.write_parquet(dest, compression="snappy")
            if first_dir is None:
                first_dir = date_dir

    return first_dir
