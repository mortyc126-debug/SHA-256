"""Tests for CLI argparse layer (does not start real WebSocket)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scalping_bot import cli


def test_build_parser_has_collect_subcommand() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["collect"])
    assert args.command == "collect"
    assert args.depth == 50
    assert args.testnet is False


def test_collect_custom_args() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(
        [
            "collect",
            "--symbol",
            "ETHUSDT",
            "--depth",
            "200",
            "--duration",
            "3600",
            "--testnet",
        ]
    )
    assert args.symbol == "ETHUSDT"
    assert args.depth == 200
    assert args.duration == pytest.approx(3600.0)
    assert args.testnet is True


def test_main_without_subcommand_returns_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse exits with SystemExit(2) for missing required subcommand
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code == 2


def test_cmd_collect_catches_exceptions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If Collector.run() raises, CLI should return 1 not crash."""

    class _BoomCollector:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, duration_seconds: float | None = None) -> None:
            raise RuntimeError("boom")

        def stop(self) -> None:
            pass

    monkeypatch.setattr(cli, "Collector", _BoomCollector)
    monkeypatch.setenv("SCALPING_BOT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SCALPING_BOT_LOG_DIR", str(tmp_path / "logs"))
    # Reset cached settings so env override takes effect
    from scalping_bot.config.settings import get_settings

    get_settings.cache_clear()

    rc = cli.main(["collect", "--duration", "0"])
    assert rc == 1


class TestDownloadCLI:
    def test_download_parses_args(self) -> None:
        parser = cli._build_parser()
        args = parser.parse_args(
            [
                "download",
                "--kind",
                "trades",
                "--symbol",
                "BTCUSDT",
                "--start",
                "2025-06-01",
                "--end",
                "2025-06-02",
            ]
        )
        assert args.command == "download"
        assert args.kind == "trades"
        assert args.start == date(2025, 6, 1)
        assert args.end == date(2025, 6, 2)
        assert args.no_convert is False
        assert args.overwrite is False

    def test_download_rejects_reversed_dates(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from scalping_bot.config.settings import get_settings

        monkeypatch.setenv("SCALPING_BOT_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SCALPING_BOT_LOG_DIR", str(tmp_path / "logs"))
        get_settings.cache_clear()

        rc = cli.main(
            [
                "download",
                "--kind",
                "trades",
                "--start",
                "2025-06-10",
                "--end",
                "2025-06-01",
            ]
        )
        assert rc == 1

    def test_download_trades_happy_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Fully end-to-end with mocked download + real converter."""
        import gzip

        from scalping_bot.config.settings import get_settings

        monkeypatch.setenv("SCALPING_BOT_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SCALPING_BOT_LOG_DIR", str(tmp_path / "logs"))
        get_settings.cache_clear()

        # Stub out the network-touching downloader by monkey-patching the
        # function reference inside the cli module.
        def fake_download_trades(
            symbol: str, d: date, dest_dir: Path, overwrite: bool = False
        ) -> Path:
            dest_dir = Path(dest_dir)
            dest = dest_dir / symbol / f"{d.isoformat()}.csv.gz"
            dest.parent.mkdir(parents=True, exist_ok=True)
            header = (
                "timestamp,symbol,side,size,price,tickDirection,trdMatchID,"
                "grossValue,homeNotional,foreignNotional\n"
            )
            body = "1735689600.123,BTCUSDT,Buy,0.01,93530.0,PlusTick,id1,935.3,0.01,935.3\n"
            dest.write_bytes(gzip.compress((header + body).encode()))
            return dest

        monkeypatch.setattr(cli, "download_trades_day", fake_download_trades)

        rc = cli.main(
            [
                "download",
                "--kind",
                "trades",
                "--symbol",
                "BTCUSDT",
                "--start",
                "2025-06-01",
                "--end",
                "2025-06-01",
            ]
        )
        assert rc == 0
        # Converted Parquet should exist under data/raw
        files = list((tmp_path / "data" / "raw" / "trades").rglob("*.parquet"))
        assert files

    def test_download_orderbook_error_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import httpx

        from scalping_bot.config.settings import get_settings

        monkeypatch.setenv("SCALPING_BOT_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SCALPING_BOT_LOG_DIR", str(tmp_path / "logs"))
        get_settings.cache_clear()

        def fake_download_orderbook(*args: Any, **kwargs: Any) -> None:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("404", request=request, response=response)

        monkeypatch.setattr(cli, "download_orderbook_day", fake_download_orderbook)

        rc = cli.main(
            [
                "download",
                "--kind",
                "orderbook",
                "--start",
                "2025-06-01",
                "--end",
                "2025-06-01",
                "--no-convert",
            ]
        )
        assert rc == 1

    def test_download_unknown_kind_raises_in_helper(self) -> None:
        import structlog

        with pytest.raises(ValueError, match="unknown kind"):
            cli._download_and_convert(
                kind="bogus",
                symbol="BTCUSDT",
                d=date(2025, 6, 1),
                raw_dir=Path("/tmp"),
                out_dir=Path("/tmp"),
                convert=False,
                keep_archives=True,
                overwrite=False,
                log=structlog.get_logger(),
            )
