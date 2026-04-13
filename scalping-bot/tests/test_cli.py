"""Tests for CLI argparse layer (does not start real WebSocket)."""

from __future__ import annotations

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
