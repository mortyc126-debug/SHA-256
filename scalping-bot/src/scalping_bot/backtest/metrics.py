"""Trading performance metrics computed from a list of completed trades."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from scalping_bot.backtest.engine import CompletedTrade

# Bars per trading year. Crypto is 24/7: 365 days * 86400 sec.
SECONDS_PER_YEAR: float = 365 * 86_400


@dataclass(frozen=True)
class BacktestSummary:
    n_trades: int
    n_wins: int
    n_losses: int
    win_rate: float
    avg_pnl_usd: float
    median_pnl_usd: float
    total_pnl_usd: float
    total_fees_usd: float
    profit_factor: float
    """Sum of winners / abs(sum of losers). Inf if no losers."""
    avg_holding_seconds: float
    sharpe_per_trade: float
    """Trade-level Sharpe (mean / std of per-trade PnL pct)."""
    sharpe_annualized: float | None
    """Annualized assuming bars-per-year cadence; None if undefined."""
    starting_capital_usd: float
    final_equity_usd: float
    total_return_pct: float
    max_drawdown_pct: float


def summarize_trades(
    trades: Iterable[CompletedTrade],
    starting_capital_usd: float,
    bar_seconds: float = 1.0,
) -> BacktestSummary:
    """Compute headline metrics from a sequence of completed trades."""
    trade_list = list(trades)
    n = len(trade_list)

    if n == 0:
        return BacktestSummary(
            n_trades=0,
            n_wins=0,
            n_losses=0,
            win_rate=0.0,
            avg_pnl_usd=0.0,
            median_pnl_usd=0.0,
            total_pnl_usd=0.0,
            total_fees_usd=0.0,
            profit_factor=0.0,
            avg_holding_seconds=0.0,
            sharpe_per_trade=0.0,
            sharpe_annualized=None,
            starting_capital_usd=starting_capital_usd,
            final_equity_usd=starting_capital_usd,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
        )

    pnls = [t.pnl_usd for t in trade_list]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    sum_wins = sum(wins)
    sum_losses = sum(losses)
    profit_factor = sum_wins / abs(sum_losses) if sum_losses < 0 else float("inf")

    fees = sum(t.fees_usd for t in trade_list)
    total_pnl = sum(pnls)
    final_eq = starting_capital_usd + total_pnl

    # Trade returns as fraction of starting capital (consistent unit)
    trade_returns = [p / starting_capital_usd for p in pnls]
    mean_ret = sum(trade_returns) / n
    var_ret = sum((r - mean_ret) ** 2 for r in trade_returns) / n
    std_ret = math.sqrt(var_ret)
    sharpe_per_trade = mean_ret / std_ret if std_ret > 0 else 0.0

    holdings = [
        (t.exit_ts - t.entry_ts).total_seconds() for t in trade_list
    ]
    avg_hold_s = sum(holdings) / n if holdings else 0.0

    sharpe_ann: float | None = None
    if std_ret > 0 and avg_hold_s > 0:
        trades_per_year = SECONDS_PER_YEAR / avg_hold_s
        sharpe_ann = sharpe_per_trade * math.sqrt(trades_per_year)

    # Equity curve drawdown
    equity = starting_capital_usd
    peak = equity
    max_dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    sorted_pnls = sorted(pnls)
    median_pnl = (
        sorted_pnls[n // 2]
        if n % 2 == 1
        else (sorted_pnls[n // 2 - 1] + sorted_pnls[n // 2]) / 2
    )

    return BacktestSummary(
        n_trades=n,
        n_wins=len(wins),
        n_losses=len(losses),
        win_rate=len(wins) / n,
        avg_pnl_usd=total_pnl / n,
        median_pnl_usd=median_pnl,
        total_pnl_usd=total_pnl,
        total_fees_usd=fees,
        profit_factor=profit_factor,
        avg_holding_seconds=avg_hold_s,
        sharpe_per_trade=sharpe_per_trade,
        sharpe_annualized=sharpe_ann,
        starting_capital_usd=starting_capital_usd,
        final_equity_usd=final_eq,
        total_return_pct=total_pnl / starting_capital_usd,
        max_drawdown_pct=max_dd,
    )
