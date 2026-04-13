"""Trailing stop manager — locks profit as price moves favorably.

Logic per long position (mirror for short):
  1. Initial SL at entry - initial_sl_bps.
  2. If price reaches entry + breakeven_trigger_bps, move SL to entry.
  3. If price keeps rising, trail SL behind the high-water-mark by
     trail_distance_bps (SL never moves backwards).

This converts "wins/losses 50/50" into "wins or break-even mostly".
At the cost of: early exits clip large winners; initial SL still hits
on the first sharp adverse move.
"""

from __future__ import annotations

from dataclasses import dataclass

from scalping_bot.backtest.engine import Side


@dataclass
class TrailingStopConfig:
    initial_sl_bps: float = 30.0
    """Stop distance from entry in basis points before any profit move."""

    breakeven_trigger_bps: float = 5.0
    """Once profit reaches this, SL moves to entry (locks 0)."""

    trail_distance_bps: float = 5.0
    """After breakeven, SL trails this far behind the best price."""

    initial_lock_bps: float = 1.0
    """When breakeven is first triggered, also lock this much profit."""


@dataclass
class TrailingStopState:
    entry_price: float
    side: Side
    best_price: float
    current_stop: float
    breakeven_triggered: bool = False

    @classmethod
    def open(cls, side: Side, entry_price: float, cfg: TrailingStopConfig) -> TrailingStopState:
        if side == Side.LONG:
            initial_stop = entry_price * (1 - cfg.initial_sl_bps / 10_000.0)
        else:
            initial_stop = entry_price * (1 + cfg.initial_sl_bps / 10_000.0)
        return cls(
            entry_price=entry_price,
            side=side,
            best_price=entry_price,
            current_stop=initial_stop,
            breakeven_triggered=False,
        )

    def update(self, current_price: float, cfg: TrailingStopConfig) -> bool:
        """Update internal state given the new price.

        Returns True if `current_price` has hit the stop (caller should close).
        Stop only moves on new highs (long) or new lows (short).
        """
        if self.side == Side.LONG:
            new_high = current_price > self.best_price
            self.best_price = max(self.best_price, current_price)
            if current_price <= self.current_stop:
                return True
            profit_bps = (self.best_price - self.entry_price) / self.entry_price * 10_000.0
            if profit_bps < cfg.breakeven_trigger_bps:
                return False
            if not self.breakeven_triggered:
                lock = self.entry_price * (1 + cfg.initial_lock_bps / 10_000.0)
                trail = self.best_price * (1 - cfg.trail_distance_bps / 10_000.0)
                self.current_stop = max(self.current_stop, lock, trail)
                self.breakeven_triggered = True
            elif new_high:
                trail = self.best_price * (1 - cfg.trail_distance_bps / 10_000.0)
                self.current_stop = max(self.current_stop, trail)
            return False
        # SHORT
        new_low = current_price < self.best_price
        self.best_price = min(self.best_price, current_price)
        if current_price >= self.current_stop:
            return True
        profit_bps = (self.entry_price - self.best_price) / self.entry_price * 10_000.0
        if profit_bps < cfg.breakeven_trigger_bps:
            return False
        if not self.breakeven_triggered:
            lock = self.entry_price * (1 - cfg.initial_lock_bps / 10_000.0)
            trail = self.best_price * (1 + cfg.trail_distance_bps / 10_000.0)
            self.current_stop = min(self.current_stop, lock, trail)
            self.breakeven_triggered = True
        elif new_low:
            trail = self.best_price * (1 + cfg.trail_distance_bps / 10_000.0)
            self.current_stop = min(self.current_stop, trail)
        return False

    def realized_profit_bps_if_stopped(self) -> float:
        """If we were stopped at current_stop, how many bps did we lock in?"""
        if self.side == Side.LONG:
            return (self.current_stop - self.entry_price) / self.entry_price * 10_000.0
        return (self.entry_price - self.current_stop) / self.entry_price * 10_000.0
