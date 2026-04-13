"""HTTP downloaders for Bybit public historical archives.

Files are streamed to disk in chunks to avoid loading the whole archive
into memory (orderbook archives are ~290 MB per day per symbol).

A simple `resume` mechanism skips files that already exist at the
destination path unless `overwrite=True`. This lets a long download
pick up where it left off.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final

import httpx

TRADES_BASE: Final[str] = "https://public.bybit.com/trading"
ORDERBOOK_BASE: Final[str] = "https://quote-saver.bycsi.com/orderbook/linear"
DEFAULT_CHUNK_BYTES: Final[int] = 1 << 20  # 1 MiB
DEFAULT_TIMEOUT_SECONDS: Final[float] = 60.0


def trades_url(symbol: str, d: date) -> str:
    """URL for a daily trades archive (CSV gzip)."""
    return f"{TRADES_BASE}/{symbol}/{symbol}{d.isoformat()}.csv.gz"


def orderbook_url(symbol: str, d: date) -> str:
    """URL for a daily orderbook archive (ZIP of JSONL)."""
    return f"{ORDERBOOK_BASE}/{symbol}/{d.isoformat()}_{symbol}_ob200.data.zip"


def _stream_download(
    url: str,
    dest: Path,
    client: httpx.Client | None = None,
    chunk_size: int = DEFAULT_CHUNK_BYTES,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> int:
    """Stream `url` into `dest`. Returns bytes written.

    If `client` is None a fresh one is constructed and closed for this call.
    Passing a shared client lets callers batch many downloads over one
    connection pool (and lets tests inject a MockTransport).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(dest.suffix + ".part")
    bytes_written = 0

    owned_client = client is None
    active_client = client if client is not None else httpx.Client(timeout=timeout)
    try:
        with active_client.stream("GET", url) as resp:
            resp.raise_for_status()
            with tmp_path.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=chunk_size):
                    if chunk:
                        fh.write(chunk)
                        bytes_written += len(chunk)
    finally:
        if owned_client:
            active_client.close()

    tmp_path.replace(dest)
    return bytes_written


def download_trades_day(
    symbol: str,
    d: date,
    dest_dir: Path,
    overwrite: bool = False,
    client: httpx.Client | None = None,
) -> Path | None:
    """Download one day of trades. Returns path on success, None if skipped.

    Raises httpx.HTTPStatusError on 4xx/5xx.
    """
    url = trades_url(symbol, d)
    dest = Path(dest_dir) / f"{symbol}" / f"{d.isoformat()}.csv.gz"

    if dest.exists() and not overwrite:
        return None

    _stream_download(url, dest, client=client)
    return dest


def download_orderbook_day(
    symbol: str,
    d: date,
    dest_dir: Path,
    overwrite: bool = False,
    client: httpx.Client | None = None,
) -> Path | None:
    """Download one day of orderbook archive. Returns path on success, None if skipped."""
    url = orderbook_url(symbol, d)
    dest = Path(dest_dir) / f"{symbol}" / f"{d.isoformat()}.zip"

    if dest.exists() and not overwrite:
        return None

    _stream_download(url, dest, client=client)
    return dest
