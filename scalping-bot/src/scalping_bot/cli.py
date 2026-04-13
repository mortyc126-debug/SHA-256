"""Command-line entry point.

Usage:
    python -m scalping_bot collect                  # use settings defaults
    python -m scalping_bot collect --symbol ETHUSDT
    python -m scalping_bot collect --duration 3600  # stop after 1h
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path
from types import FrameType

from scalping_bot.config import get_settings
from scalping_bot.market_data import Collector
from scalping_bot.utils import setup_logging


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scalping_bot")
    sub = p.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Collect market data to Parquet files")
    collect.add_argument(
        "--symbol",
        default=None,
        help="Symbol override (default from settings, e.g. BTCUSDT).",
    )
    collect.add_argument(
        "--depth",
        type=int,
        default=50,
        help="Orderbook depth: 1, 50, 200 or 500 (Bybit-supported). Default: 50.",
    )
    collect.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional run duration in seconds. If omitted, runs until Ctrl+C.",
    )
    collect.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Data directory override (default from settings).",
    )
    collect.add_argument(
        "--testnet",
        action="store_true",
        help="Use Bybit testnet instead of mainnet public streams.",
    )

    return p


def _cmd_collect(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.ensure_dirs()

    symbol = args.symbol or settings.symbol
    data_dir = Path(args.data_dir) if args.data_dir else settings.data_dir / "raw"

    log = setup_logging(log_level=settings.log_level)
    log.info(
        "cli.collect.starting",
        symbol=symbol,
        depth=args.depth,
        data_dir=str(data_dir),
        testnet=args.testnet,
        duration=args.duration,
    )

    collector = Collector(
        symbol=symbol,
        data_dir=data_dir,
        depth=args.depth,
        testnet=args.testnet,
    )

    def _handle_signal(signum: int, frame: FrameType | None) -> None:
        log.info("cli.signal", signum=signum)
        collector.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        collector.run(duration_seconds=args.duration)
    except Exception as exc:
        log.error("cli.collect.failed", error=str(exc), error_type=type(exc).__name__)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "collect":
        return _cmd_collect(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
