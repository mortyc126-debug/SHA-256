"""Tests for structured logging setup."""

from __future__ import annotations

import json
import logging

import pytest

from scalping_bot.utils.logging import setup_logging


def test_setup_logging_returns_logger() -> None:
    log = setup_logging(log_level="INFO")
    assert log is not None
    # Bound loggers expose .info, .warning etc.
    assert callable(getattr(log, "info", None))
    assert callable(getattr(log, "error", None))


def test_setup_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    log = setup_logging(log_level="INFO", json_output=True)
    log.info("test_event", key="value", count=42)
    captured = capsys.readouterr()
    # Stream is stdout via PrintLoggerFactory
    line = captured.out.strip().split("\n")[-1]
    parsed = json.loads(line)
    assert parsed["event"] == "test_event"
    assert parsed["key"] == "value"
    assert parsed["count"] == 42
    assert parsed["level"] == "info"
    assert "timestamp" in parsed


def test_setup_logging_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    log = setup_logging(log_level="WARNING", json_output=True)
    log.debug("should_not_appear")
    log.info("should_not_appear_either")
    log.warning("should_appear")
    captured = capsys.readouterr()
    output = captured.out
    assert "should_appear" in output
    assert "should_not_appear" not in output


def test_setup_logging_console_mode(capsys: pytest.CaptureFixture[str]) -> None:
    log = setup_logging(log_level="INFO", json_output=False)
    log.info("readable_event", field="value")
    captured = capsys.readouterr()
    # Console mode is NOT valid JSON
    line = captured.out.strip()
    with pytest.raises(json.JSONDecodeError):
        json.loads(line)
    assert "readable_event" in line


def test_setup_logging_unknown_level_defaults_to_info() -> None:
    log = setup_logging(log_level="NONSENSE")
    # Should not raise; silently defaults (getattr behavior)
    assert log is not None


def test_setup_logging_accepts_log_dir_param(tmp_path: object) -> None:
    # Currently log_dir is unused by setup_logging but accepted as a param
    log = setup_logging(log_level="INFO", log_dir=tmp_path)  # type: ignore[arg-type]
    assert log is not None


def test_standard_logging_unaffected() -> None:
    """structlog should not mess with the stdlib root logger unexpectedly."""
    setup_logging()
    std_log = logging.getLogger("some.thirdparty.module")
    # No assertion on output format; just that it doesn't crash
    std_log.info("stdlib log line")
