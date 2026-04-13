"""Tests for historical downloader and converter.

Network is mocked via httpx.MockTransport. Real archive content is
synthesized in-memory with the exact schema Bybit uses.
"""

from __future__ import annotations

import gzip
import io
import json
import zipfile
from datetime import date
from pathlib import Path

import httpx
import polars as pl
import pytest

from scalping_bot.historical import downloader
from scalping_bot.historical.converter import (
    convert_orderbook_to_parquet,
    convert_trades_to_parquet,
)
from scalping_bot.historical.downloader import (
    download_orderbook_day,
    download_trades_day,
    orderbook_url,
    trades_url,
)

# --- URL construction -------------------------------------------------------


def test_trades_url() -> None:
    url = trades_url("BTCUSDT", date(2025, 6, 15))
    assert url == "https://public.bybit.com/trading/BTCUSDT/BTCUSDT2025-06-15.csv.gz"


def test_orderbook_url() -> None:
    url = orderbook_url("BTCUSDT", date(2025, 6, 15))
    assert (
        url
        == "https://quote-saver.bycsi.com/orderbook/linear/BTCUSDT/2025-06-15_BTCUSDT_ob200.data.zip"
    )


# --- Download mocking -------------------------------------------------------


def _mock_transport(payload: bytes) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    return httpx.MockTransport(handler)


def _mock_404() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    return httpx.MockTransport(handler)


def test_download_trades_skips_existing(tmp_path: Path) -> None:
    sym = "BTCUSDT"
    d = date(2025, 6, 1)
    dest_dir = tmp_path / "trades"
    existing = dest_dir / sym / f"{d.isoformat()}.csv.gz"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already here")

    # Inject a client whose transport would raise if hit.
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not download when destination exists")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download_trades_day(
            symbol=sym, d=d, dest_dir=dest_dir, overwrite=False, client=client
        )
    assert result is None


def test_download_trades_writes_file(tmp_path: Path) -> None:
    payload = b"hello-world"
    sym = "BTCUSDT"
    d = date(2025, 6, 1)

    with httpx.Client(transport=_mock_transport(payload)) as client:
        result = download_trades_day(
            symbol=sym, d=d, dest_dir=tmp_path / "trades", overwrite=False, client=client
        )
    assert result is not None
    assert result.exists()
    assert result.read_bytes() == payload


def test_download_raises_on_http_error(tmp_path: Path) -> None:
    with httpx.Client(transport=_mock_404()) as client, pytest.raises(httpx.HTTPStatusError):
        download_trades_day(
            symbol="BTCUSDT",
            d=date(2025, 6, 1),
            dest_dir=tmp_path / "trades",
            client=client,
        )


def test_download_orderbook_writes_file(tmp_path: Path) -> None:
    payload = b"PK\x03\x04-fake-zip"
    with httpx.Client(transport=_mock_transport(payload)) as client:
        result = download_orderbook_day(
            symbol="BTCUSDT",
            d=date(2025, 6, 1),
            dest_dir=tmp_path / "ob",
            client=client,
        )
    assert result is not None
    assert result.read_bytes() == payload


# --- Trades converter -------------------------------------------------------


def _fake_trades_csv() -> bytes:
    """Make a fake Bybit trades CSV matching the public.bybit.com schema."""
    header = (
        "timestamp,symbol,side,size,price,tickDirection,trdMatchID,"
        "grossValue,homeNotional,foreignNotional\n"
    )
    rows = [
        "1735689600.1234,BTCUSDT,Buy,0.005,93530.00,PlusTick,id1,467.65,0.005,467.65",
        "1735689601.5678,BTCUSDT,Sell,0.010,93525.50,MinusTick,id2,935.25,0.010,935.25",
        "1735689602.9012,BTCUSDT,Buy,0.001,93540.00,PlusTick,id3,93.54,0.001,93.54",
    ]
    body = "\n".join(rows) + "\n"
    return gzip.compress((header + body).encode())


def test_convert_trades_to_parquet(tmp_path: Path) -> None:
    gz_path = tmp_path / "sample.csv.gz"
    gz_path.write_bytes(_fake_trades_csv())

    out = tmp_path / "out"
    result_dir = convert_trades_to_parquet(gz_path, symbol="BTCUSDT", out_root=out)
    assert result_dir.exists()
    files = list(result_dir.glob("BTCUSDT_*.parquet"))
    assert len(files) == 1

    df = pl.read_parquet(files[0])
    assert len(df) == 3
    assert set(df.columns) == {"ts", "trade_time_ms", "side", "price", "size", "trade_id"}
    assert df["side"].to_list() == ["Buy", "Sell", "Buy"]
    assert df["trade_id"].to_list() == ["id1", "id2", "id3"]


def test_convert_trades_appends_on_second_call(tmp_path: Path) -> None:
    gz_path = tmp_path / "sample.csv.gz"
    gz_path.write_bytes(_fake_trades_csv())
    out = tmp_path / "out"

    convert_trades_to_parquet(gz_path, symbol="BTCUSDT", out_root=out)
    convert_trades_to_parquet(gz_path, symbol="BTCUSDT", out_root=out)

    files = list((out / "trades").rglob("*.parquet"))
    df = pl.read_parquet(files[0])
    assert len(df) == 6  # appended twice


# --- Orderbook converter ----------------------------------------------------


def _fake_orderbook_zip() -> bytes:
    """Craft a zip containing JSONL lines matching Bybit's orderbook format."""
    records = [
        {
            "ts": 1748736001000,
            "cts": 1748736001010,
            "type": "snapshot",
            "data": {
                "s": "BTCUSDT",
                "b": [["100000.0", "1.0"], ["99999.5", "2.0"]],
                "a": [["100001.0", "0.5"]],
                "u": 1,
                "seq": 1,
            },
        },
        {
            "ts": 1748736001100,
            "cts": 1748736001110,
            "type": "delta",
            "data": {
                "s": "BTCUSDT",
                "b": [],
                "a": [["100001.0", "0.0"], ["100001.5", "3.0"]],
                "u": 2,
                "seq": 2,
            },
        },
        {
            "ts": 1748736001200,
            "cts": 1748736001210,
            "type": "delta",
            "data": {
                "s": "BTCUSDT",
                "b": [["99999.0", "7.0"]],
                "a": [],
                "u": 3,
                "seq": 3,
            },
        },
    ]
    jsonl = ("\n".join(json.dumps(r) for r in records) + "\n").encode()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("2025-06-01_BTCUSDT_ob200.data", jsonl)
    return buf.getvalue()


def test_convert_orderbook_to_parquet(tmp_path: Path) -> None:
    zip_path = tmp_path / "sample.zip"
    zip_path.write_bytes(_fake_orderbook_zip())

    out = tmp_path / "out"
    convert_orderbook_to_parquet(zip_path, symbol="BTCUSDT", out_root=out)

    snap_files = list((out / "orderbook_snapshots").rglob("*.parquet"))
    delta_files = list((out / "orderbook").rglob("*.parquet"))
    assert len(snap_files) == 1
    assert len(delta_files) == 1

    snap_df = pl.read_parquet(snap_files[0])
    delta_df = pl.read_parquet(delta_files[0])
    assert len(snap_df) == 1
    assert len(delta_df) == 2
    assert "update_id" in snap_df.columns
    assert "bids" in snap_df.columns
    assert "asks" in snap_df.columns


def test_convert_orderbook_skips_malformed_records(tmp_path: Path) -> None:
    """A mixture of valid and malformed records should not crash; malformed ignored."""
    records_jsonl = b'{"type":"snapshot","data":{"s":"BTCUSDT","b":[["100","1"]],"a":[["101","0.5"]],"u":1},"ts":1748736001000}\n'
    records_jsonl += b"not-a-json-line\n"
    records_jsonl += b'{"type":"delta","ts":"bad","data":{"u":2,"b":[],"a":[]}}\n'  # bad ts
    records_jsonl += b'{"type":"delta","ts":1748736001100,"data":{"s":"BTCUSDT","b":[],"a":[["100.5","0"]],"u":2,"seq":2}}\n'

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("2025-06-01_BTCUSDT_ob200.data", records_jsonl)
    zip_path = tmp_path / "sample.zip"
    zip_path.write_bytes(buf.getvalue())

    out = tmp_path / "out"
    convert_orderbook_to_parquet(zip_path, symbol="BTCUSDT", out_root=out)

    snap_count = sum(
        len(pl.read_parquet(p)) for p in (out / "orderbook_snapshots").rglob("*.parquet")
    )
    delta_count = sum(
        len(pl.read_parquet(p)) for p in (out / "orderbook").rglob("*.parquet")
    )
    assert snap_count == 1
    assert delta_count == 1  # one malformed + one good


def test_convert_empty_zip_is_safe(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass
    zip_path = tmp_path / "empty.zip"
    zip_path.write_bytes(buf.getvalue())

    result = convert_orderbook_to_parquet(zip_path, symbol="BTCUSDT", out_root=tmp_path / "out")
    assert result == Path()


# --- Module exports ---------------------------------------------------------


def test_public_api_exports() -> None:
    from scalping_bot import historical

    assert callable(historical.download_trades_day)
    assert callable(historical.download_orderbook_day)
    assert callable(historical.convert_trades_to_parquet)
    assert callable(historical.convert_orderbook_to_parquet)
    assert callable(historical.trades_url)
    assert callable(historical.orderbook_url)


def test_constants_sane() -> None:
    assert downloader.TRADES_BASE.startswith("https://")
    assert downloader.ORDERBOOK_BASE.startswith("https://")
    assert downloader.DEFAULT_CHUNK_BYTES > 0
    assert downloader.DEFAULT_TIMEOUT_SECONDS > 0
