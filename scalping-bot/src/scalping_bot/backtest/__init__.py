"""Backtest engine — strategy simulation with realistic fees and slippage."""

from scalping_bot.backtest.engine import BacktestEngine, Position, Side
from scalping_bot.backtest.metrics import BacktestSummary, summarize_trades
from scalping_bot.backtest.runner import run_walk_forward_backtest
from scalping_bot.backtest.strategy import StrategyConfig, ThresholdStrategy

__all__ = [
    "BacktestEngine",
    "BacktestSummary",
    "Position",
    "Side",
    "StrategyConfig",
    "ThresholdStrategy",
    "run_walk_forward_backtest",
    "summarize_trades",
]
