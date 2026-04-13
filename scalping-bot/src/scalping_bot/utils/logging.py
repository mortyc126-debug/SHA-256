"""Structured logging via structlog.

JSON output on stdout by default. Every log line is a single JSON object
with ISO-8601 UTC timestamp, log level, event name, and arbitrary
context fields. This format is parseable by grep, jq, ELK stacks, or
any structured log tool without preprocessing.

Usage:
    from scalping_bot.utils import setup_logging
    log = setup_logging(log_level="INFO")
    log.info("trade_executed", side="long", price=68000.5, size_usd=30.0)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.stdlib import BoundLogger


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    json_output: bool = True,
) -> BoundLogger:
    """Configure structlog and return the root logger.

    Args:
        log_level: One of DEBUG/INFO/WARNING/ERROR.
        log_dir: Optional directory for file logs (not yet used).
        json_output: If True, output JSON; if False, human-readable.

    Returns:
        A bound logger ready for use. Child loggers via `.bind(component=...)`.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer: Any = structlog.processors.JSONRenderer(sort_keys=True)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logger: BoundLogger = structlog.get_logger()
    return logger
