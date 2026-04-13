"""Threshold-based strategy: turn Distinguisher probabilities into actions.

Logic per bar:
  - If no position and P(up) >= enter_threshold and P(up) > P(down):
      open LONG sized by (P_up - P_down) * kelly_fraction
  - If no position and P(down) >= enter_threshold and P(down) > P(up):
      open SHORT analogously
  - If a position is open:
      - holding_time_bars >= max_hold_bars  -> close (TIME)
      - unrealized_pnl_pct >= take_profit   -> close (TP)
      - unrealized_pnl_pct <= -stop_loss    -> close (SL)
      - opposite-direction signal above exit_threshold -> close (REVERSAL)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from scalping_bot.backtest.engine import BacktestEngine, Side


class Action(Enum):
    HOLD = "hold"
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE = "close"


@dataclass
class StrategyConfig:
    enter_threshold: float = 0.45
    """Minimum P(direction) required to open a position."""

    exit_threshold: float = 0.50
    """Minimum P(opposite direction) that closes an open position."""

    take_profit_bps: float = 5.0
    """Close on profit reaching this many basis points (5 = 0.05%)."""

    stop_loss_bps: float = 8.0
    """Close on loss reaching this many basis points."""

    max_hold_bars: int = 60
    """Close after holding this many bars regardless of P&L."""

    kelly_fraction: float = 0.20
    """Multiplier on confidence-based sizing. 0.20 = "20% Kelly"."""

    min_size_fraction: float = 0.05
    """Floor on equity fraction per trade. Below this we don't open."""


@dataclass
class ThresholdStrategy:
    """Stateful (within a backtest run) threshold strategy."""

    config: StrategyConfig

    # Per-position holding counter; reset on each open
    _bars_in_position: int = 0

    def reset(self) -> None:
        self._bars_in_position = 0

    def step(
        self,
        engine: BacktestEngine,
        ts: datetime,
        price: float,
        proba_up: float,
        proba_down: float,
    ) -> Action:
        """Evaluate this bar and act on the engine. Returns the action taken."""
        cfg = self.config

        # --- Manage existing position -----------------------------------------
        if engine.position is not None:
            self._bars_in_position += 1
            pos = engine.position

            # P&L in pct
            if pos.side == Side.LONG:
                pnl_pct = (price - pos.entry_price) / pos.entry_price
            else:
                pnl_pct = (pos.entry_price - price) / pos.entry_price

            # 1. Stop loss
            if pnl_pct <= -cfg.stop_loss_bps / 10_000.0:
                engine.close_position(ts, price, "stop_loss")
                self._bars_in_position = 0
                return Action.CLOSE
            # 2. Take profit
            if pnl_pct >= cfg.take_profit_bps / 10_000.0:
                engine.close_position(ts, price, "take_profit")
                self._bars_in_position = 0
                return Action.CLOSE
            # 3. Time exit
            if self._bars_in_position >= cfg.max_hold_bars:
                engine.close_position(ts, price, "time_exit")
                self._bars_in_position = 0
                return Action.CLOSE
            # 4. Reversal
            if pos.side == Side.LONG and proba_down >= cfg.exit_threshold:
                engine.close_position(ts, price, "reversal_down")
                self._bars_in_position = 0
                return Action.CLOSE
            if pos.side == Side.SHORT and proba_up >= cfg.exit_threshold:
                engine.close_position(ts, price, "reversal_up")
                self._bars_in_position = 0
                return Action.CLOSE
            return Action.HOLD

        # --- No position: maybe open ------------------------------------------
        if proba_up >= cfg.enter_threshold and proba_up > proba_down:
            confidence = proba_up - proba_down
            size = max(cfg.min_size_fraction, min(1.0, confidence * cfg.kelly_fraction))
            if engine.open_position(Side.LONG, ts, price, size):
                self._bars_in_position = 0
                return Action.OPEN_LONG

        if proba_down >= cfg.enter_threshold and proba_down > proba_up:
            confidence = proba_down - proba_up
            size = max(cfg.min_size_fraction, min(1.0, confidence * cfg.kelly_fraction))
            if engine.open_position(Side.SHORT, ts, price, size):
                self._bars_in_position = 0
                return Action.OPEN_SHORT

        return Action.HOLD
