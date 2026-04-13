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
from datetime import date, datetime, timedelta
from pathlib import Path
from types import FrameType

import httpx
import structlog

from scalping_bot.config import get_settings
from scalping_bot.historical import (
    convert_orderbook_to_parquet,
    convert_trades_to_parquet,
    download_orderbook_day,
    download_trades_day,
)
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

    download = sub.add_parser(
        "download",
        help="Download historical archives from Bybit public endpoints.",
    )
    download.add_argument(
        "--kind",
        choices=["trades", "orderbook", "both"],
        default="both",
        help="Which archive to download (default: both).",
    )
    download.add_argument("--symbol", default=None, help="Symbol (default from settings).")
    download.add_argument(
        "--start",
        type=_parse_date,
        required=True,
        help="Start date YYYY-MM-DD (inclusive).",
    )
    download.add_argument(
        "--end",
        type=_parse_date,
        required=True,
        help="End date YYYY-MM-DD (inclusive).",
    )
    download.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Directory for raw archives (default: data/archives).",
    )
    download.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory for converted Parquet (default: data/raw).",
    )
    download.add_argument(
        "--no-convert",
        action="store_true",
        help="Only download; skip Parquet conversion.",
    )
    download.add_argument(
        "--keep-archives",
        action="store_true",
        help="Keep downloaded archives after conversion (default: delete).",
    )
    download.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download files that already exist locally.",
    )

    return p


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


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


def _cmd_download(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.ensure_dirs()
    log: structlog.stdlib.BoundLogger = setup_logging(log_level=settings.log_level)

    symbol = args.symbol or settings.symbol
    raw_dir = Path(args.raw_dir) if args.raw_dir else settings.data_dir / "archives"
    out_dir = Path(args.out_dir) if args.out_dir else settings.data_dir / "raw"

    if args.start > args.end:
        log.error("cli.download.bad_range", start=args.start.isoformat(), end=args.end.isoformat())
        return 1

    kinds = ["trades", "orderbook"] if args.kind == "both" else [args.kind]

    days = (args.end - args.start).days + 1
    log.info(
        "cli.download.starting",
        symbol=symbol,
        kinds=kinds,
        start=args.start.isoformat(),
        end=args.end.isoformat(),
        days=days,
        raw_dir=str(raw_dir),
        out_dir=str(out_dir),
    )

    successes = 0
    failures: list[tuple[str, date, str]] = []

    for kind in kinds:
        current = args.start
        while current <= args.end:
            try:
                path = _download_and_convert(
                    kind=kind,
                    symbol=symbol,
                    d=current,
                    raw_dir=raw_dir,
                    out_dir=out_dir,
                    convert=not args.no_convert,
                    keep_archives=args.keep_archives,
                    overwrite=args.overwrite,
                    log=log,
                )
                if path is not None:
                    successes += 1
            except httpx.HTTPStatusError as exc:
                failures.append((kind, current, f"http {exc.response.status_code}"))
                log.warning(
                    "cli.download.http_error",
                    kind=kind,
                    date=current.isoformat(),
                    status=exc.response.status_code,
                )
            except (OSError, ValueError) as exc:
                failures.append((kind, current, str(exc)))
                log.warning(
                    "cli.download.failed",
                    kind=kind,
                    date=current.isoformat(),
                    error=str(exc),
                )
            current += timedelta(days=1)

    log.info(
        "cli.download.done",
        successes=successes,
        failures=len(failures),
        failure_list=[{"kind": k, "date": d.isoformat(), "reason": r} for k, d, r in failures],
    )
    return 0 if not failures else 1


def _download_and_convert(
    kind: str,
    symbol: str,
    d: date,
    raw_dir: Path,
    out_dir: Path,
    convert: bool,
    keep_archives: bool,
    overwrite: bool,
    log: structlog.stdlib.BoundLogger,
) -> Path | None:
    if kind == "trades":
        archive = download_trades_day(symbol=symbol, d=d, dest_dir=raw_dir / "trades", overwrite=overwrite)
        downloaded_now = archive is not None
        archive = archive or (raw_dir / "trades" / symbol / f"{d.isoformat()}.csv.gz")
        if convert:
            convert_trades_to_parquet(csv_gz_path=archive, symbol=symbol, out_root=out_dir)
        if downloaded_now and not keep_archives:
            archive.unlink(missing_ok=True)
        log.info("cli.download.day_done", kind=kind, date=d.isoformat(), downloaded=downloaded_now)
        return archive

    if kind == "orderbook":
        archive = download_orderbook_day(
            symbol=symbol, d=d, dest_dir=raw_dir / "orderbook", overwrite=overwrite
        )
        downloaded_now = archive is not None
        archive = archive or (raw_dir / "orderbook" / symbol / f"{d.isoformat()}.zip")
        if convert:
            convert_orderbook_to_parquet(zip_path=archive, symbol=symbol, out_root=out_dir)
        if downloaded_now and not keep_archives:
            archive.unlink(missing_ok=True)
        log.info("cli.download.day_done", kind=kind, date=d.isoformat(), downloaded=downloaded_now)
        return archive

    raise ValueError(f"unknown kind: {kind!r}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "collect":
        return _cmd_collect(args)
    if args.command == "download":
        return _cmd_download(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
