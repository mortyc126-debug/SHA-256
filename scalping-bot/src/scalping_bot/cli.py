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

DEFAULT_FEATURE_COLS = [
    "flow_imbalance",
    "trade_rate",
    "rv_w60",
    "rv_w300",
    "vwap_w30",
    "vwap_w300",
    "cum_delta_w30",
    "cum_delta_w300",
    "price_range_w300",
    "hour_sin",
    "hour_cos",
    "minute_sin",
    "minute_cos",
]


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

    train = sub.add_parser("train", help="Fit Distinguisher with walk-forward validation.")
    train.add_argument("--symbol", default=None)
    train.add_argument("--start", type=_parse_date, required=True)
    train.add_argument("--end", type=_parse_date, required=True)
    train.add_argument("--data-dir", type=Path, default=None)
    train.add_argument("--bar-seconds", type=float, default=1.0)
    train.add_argument("--horizon-bars", type=int, default=30)
    train.add_argument("--threshold-bps", type=float, default=2.0)
    train.add_argument("--n-splits", type=int, default=4)
    train.add_argument("--n-pairwise", type=int, default=10)
    train.add_argument("--enter-threshold", type=float, default=0.55)

    backtest = sub.add_parser("backtest", help="Walk-forward backtest with realistic costs.")
    backtest.add_argument("--symbol", default=None)
    backtest.add_argument("--start", type=_parse_date, required=True)
    backtest.add_argument("--end", type=_parse_date, required=True)
    backtest.add_argument("--data-dir", type=Path, default=None)
    backtest.add_argument("--bar-seconds", type=float, default=1.0)
    backtest.add_argument("--horizon-bars", type=int, default=30)
    backtest.add_argument("--threshold-bps", type=float, default=2.0)
    backtest.add_argument("--n-splits", type=int, default=4)
    backtest.add_argument("--n-pairwise", type=int, default=10)
    backtest.add_argument("--starting-capital", type=float, default=100.0)
    backtest.add_argument("--leverage", type=float, default=3.0)
    backtest.add_argument("--enter-threshold", type=float, default=0.45)
    backtest.add_argument("--exit-threshold", type=float, default=0.50)
    backtest.add_argument("--take-profit-bps", type=float, default=5.0)
    backtest.add_argument("--stop-loss-bps", type=float, default=8.0)
    backtest.add_argument("--max-hold-bars", type=int, default=60)
    backtest.add_argument("--kelly-fraction", type=float, default=0.20)
    backtest.add_argument(
        "--maker",
        action="store_true",
        help="Assume maker fills (rebate). Default: taker (cost).",
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


def _cmd_train(args: argparse.Namespace) -> int:
    from scalping_bot.features import build_feature_matrix, load_trades_range
    from scalping_bot.models import (
        Distinguisher,
        directional_metrics,
        walk_forward_splits,
    )

    settings = get_settings()
    settings.ensure_dirs()
    log: structlog.stdlib.BoundLogger = setup_logging(log_level=settings.log_level)

    symbol = args.symbol or settings.symbol
    data_dir = Path(args.data_dir) if args.data_dir else settings.data_dir / "raw"

    log.info(
        "cli.train.loading",
        symbol=symbol,
        start=args.start.isoformat(),
        end=args.end.isoformat(),
    )
    trades = load_trades_range(data_dir, symbol, args.start, args.end)
    if trades.is_empty():
        log.error("cli.train.no_data")
        return 1
    log.info("cli.train.ticks_loaded", ticks=len(trades))

    fm = build_feature_matrix(
        trades,
        bar_seconds=args.bar_seconds,
        label_horizon_bars=args.horizon_bars,
        label_threshold_bps=args.threshold_bps,
    )
    label_col = f"label_{args.horizon_bars}"
    log.info("cli.train.features_built", bars=len(fm), cols=fm.width)

    feature_cols = [c for c in DEFAULT_FEATURE_COLS if c in fm.columns]

    results = []
    for split in walk_forward_splits(n_rows=len(fm), n_splits=args.n_splits):
        train_df = fm[split.train_start : split.train_end]
        val_df = fm[split.val_start : split.val_end]

        d = Distinguisher(
            feature_cols=feature_cols,
            label_col=label_col,
            n_pairwise=args.n_pairwise,
        )
        d.fit(train_df)

        proba = d.predict_proba(val_df)
        classes = d.classes_.tolist()
        proba_up = proba[:, classes.index(1)] if 1 in classes else None
        proba_down = proba[:, classes.index(-1)] if -1 in classes else None
        if proba_up is None or proba_down is None:
            log.warning("cli.train.fold_skipped_missing_class", fold=split.fold)
            continue

        y_val = val_df[label_col].to_numpy()
        metrics = directional_metrics(
            y_true=y_val,
            proba_up=proba_up,
            proba_down=proba_down,
            enter_threshold=args.enter_threshold,
        )
        log.info(
            "cli.train.fold_done",
            fold=split.fold,
            train_rows=split.train_end - split.train_start,
            val_rows=split.val_end - split.val_start,
            auc_up=round(metrics.auc_up_vs_rest, 4),
            auc_down=round(metrics.auc_down_vs_rest, 4),
            coverage=round(metrics.coverage, 4),
            directional_accuracy=round(metrics.directional_accuracy, 4),
            precision_up=round(metrics.precision_up, 4),
            precision_down=round(metrics.precision_down, 4),
            n_signals=metrics.n_signals,
        )
        results.append(metrics)

    if not results:
        log.error("cli.train.no_folds")
        return 1

    avg_auc_up = sum(r.auc_up_vs_rest for r in results) / len(results)
    avg_auc_down = sum(r.auc_down_vs_rest for r in results) / len(results)
    avg_coverage = sum(r.coverage for r in results) / len(results)
    avg_acc = sum(
        r.directional_accuracy for r in results if r.directional_accuracy == r.directional_accuracy
    ) / max(
        1, sum(1 for r in results if r.directional_accuracy == r.directional_accuracy)
    )
    log.info(
        "cli.train.summary",
        folds=len(results),
        avg_auc_up=round(avg_auc_up, 4),
        avg_auc_down=round(avg_auc_down, 4),
        avg_coverage=round(avg_coverage, 4),
        avg_directional_accuracy=round(avg_acc, 4),
        gate_passed=min(avg_auc_up, avg_auc_down) > 0.55,
    )
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    from scalping_bot.backtest import (
        StrategyConfig,
        run_walk_forward_backtest,
    )
    from scalping_bot.features import build_feature_matrix, load_trades_range

    settings = get_settings()
    settings.ensure_dirs()
    log: structlog.stdlib.BoundLogger = setup_logging(log_level=settings.log_level)

    symbol = args.symbol or settings.symbol
    data_dir = Path(args.data_dir) if args.data_dir else settings.data_dir / "raw"

    log.info("cli.backtest.loading", start=args.start.isoformat(), end=args.end.isoformat())
    trades = load_trades_range(data_dir, symbol, args.start, args.end)
    if trades.is_empty():
        log.error("cli.backtest.no_data")
        return 1

    fm = build_feature_matrix(
        trades,
        bar_seconds=args.bar_seconds,
        label_horizon_bars=args.horizon_bars,
        label_threshold_bps=args.threshold_bps,
    )
    label_col = f"label_{args.horizon_bars}"
    feature_cols = [c for c in DEFAULT_FEATURE_COLS if c in fm.columns]
    log.info(
        "cli.backtest.features_built",
        bars=len(fm),
        feature_cols=len(feature_cols),
    )

    cfg = StrategyConfig(
        enter_threshold=args.enter_threshold,
        exit_threshold=args.exit_threshold,
        take_profit_bps=args.take_profit_bps,
        stop_loss_bps=args.stop_loss_bps,
        max_hold_bars=args.max_hold_bars,
        kelly_fraction=args.kelly_fraction,
    )

    fold_results, aggregate = run_walk_forward_backtest(
        feature_matrix=fm,
        feature_cols=feature_cols,
        label_col=label_col,
        n_splits=args.n_splits,
        n_pairwise=args.n_pairwise,
        starting_capital_usd=args.starting_capital,
        leverage=args.leverage,
        strategy_config=cfg,
        bar_seconds=args.bar_seconds,
        use_taker=not args.maker,
    )

    for fr in fold_results:
        s = fr.summary
        log.info(
            "cli.backtest.fold",
            fold=fr.fold,
            n_trades=s.n_trades,
            win_rate=round(s.win_rate, 4),
            total_pnl_usd=round(s.total_pnl_usd, 2),
            total_return_pct=round(s.total_return_pct, 4),
            max_drawdown_pct=round(s.max_drawdown_pct, 4),
            profit_factor=round(s.profit_factor, 3) if s.profit_factor != float("inf") else "inf",
            sharpe_per_trade=round(s.sharpe_per_trade, 4),
            sharpe_annualized=round(s.sharpe_annualized, 3) if s.sharpe_annualized else None,
            avg_holding_seconds=round(s.avg_holding_seconds, 1),
        )

    log.info(
        "cli.backtest.aggregate",
        n_trades=aggregate.n_trades,
        win_rate=round(aggregate.win_rate, 4),
        total_pnl_usd=round(aggregate.total_pnl_usd, 2),
        total_fees_usd=round(aggregate.total_fees_usd, 2),
        total_return_pct=round(aggregate.total_return_pct, 4),
        max_drawdown_pct=round(aggregate.max_drawdown_pct, 4),
        profit_factor=(
            round(aggregate.profit_factor, 3)
            if aggregate.profit_factor != float("inf")
            else "inf"
        ),
        sharpe_annualized=(
            round(aggregate.sharpe_annualized, 3) if aggregate.sharpe_annualized else None
        ),
        gate_passed=aggregate.total_return_pct > 0
        and (aggregate.sharpe_annualized or 0) > 1.5,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "collect":
        return _cmd_collect(args)
    if args.command == "download":
        return _cmd_download(args)
    if args.command == "train":
        return _cmd_train(args)
    if args.command == "backtest":
        return _cmd_backtest(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
