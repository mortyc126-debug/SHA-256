"""Paper broker — mock order execution that mimics live trading.

Wraps `BacktestEngine` for state (position, equity, trades) but adds a
"current price" mark and an order-submission API the live runner can
call. Fills are immediate at the configured fill price (default: trade
mid implied from latest bar's close + slippage).

This is intentionally simple — for paper trading we want *something
that records hypothetical trades correctly* and lets us compare paper
P&L vs backtest P&L. Realism extras (queue position, partial fills,
cancellations) come later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from scalping_bot.backtest.engine import BacktestEngine, FeeModel, Side
from scalping_bot.risk.kill_switch import KillSwitch
from scalping_bot.risk.limits import (
    RiskLimits,
    check_leverage,
    check_position_size,
)


@dataclass
class PaperBroker:
    """Paper broker built on the BacktestEngine + risk subsystem."""

    starting_capital_usd: float = 100.0
    leverage: float = 3.0
    fee_model: FeeModel = field(default_factory=FeeModel)
    use_taker: bool = True

    _engine: BacktestEngine = field(init=False)
    _kill_switch: KillSwitch = field(init=False, default_factory=KillSwitch)

    def __post_init__(self) -> None:
        leverage_check = check_leverage(self.leverage)
        if not leverage_check.allowed:
            raise ValueError(leverage_check.reason)

        self._engine = BacktestEngine(
            starting_capital_usd=self.starting_capital_usd,
            leverage=self.leverage,
            fee_model=self.fee_model,
            use_taker=self.use_taker,
        )

    # --- Order API ----------------------------------------------------------

    def open_long(
        self,
        ts: datetime,
        price: float,
        size_fraction_of_equity: float,
    ) -> bool:
        return self._submit_open(Side.LONG, ts, price, size_fraction_of_equity)

    def open_short(
        self,
        ts: datetime,
        price: float,
        size_fraction_of_equity: float,
    ) -> bool:
        return self._submit_open(Side.SHORT, ts, price, size_fraction_of_equity)

    def close(self, ts: datetime, price: float, reason: str) -> bool:
        if not self._kill_switch.can_trade():
            # Allow closes when killed (we always want to flatten on emergency)
            pass
        return self._engine.close_position(ts, price, reason) is not None

    # --- Mark-to-market ----------------------------------------------------

    def mark(self, price: float) -> None:
        eq = self._engine.mark_to_market(price)
        # Drawdown circuit breaker
        if self._engine.drawdown_pct > RiskLimits.KILL_SWITCH_DRAWDOWN_PCT:
            self._kill_switch.trigger_kill(
                "drawdown_exceeded",
                details={
                    "equity": eq,
                    "drawdown_pct": self._engine.drawdown_pct,
                },
            )

    # --- State queries ------------------------------------------------------

    @property
    def equity(self) -> float:
        return self._engine.equity

    @property
    def can_trade(self) -> bool:
        return self._kill_switch.can_trade()

    @property
    def has_position(self) -> bool:
        return self._engine.position is not None

    @property
    def position(self) -> object | None:
        return self._engine.position

    @property
    def trades(self) -> tuple[object, ...]:
        return self._engine.trades

    @property
    def kill_switch(self) -> KillSwitch:
        return self._kill_switch

    @property
    def engine(self) -> BacktestEngine:
        """Direct engine access for read-only inspection in tests."""
        return self._engine

    # --- Internals ---------------------------------------------------------

    def _submit_open(
        self,
        side: Side,
        ts: datetime,
        price: float,
        size_fraction_of_equity: float,
    ) -> bool:
        if not self._kill_switch.can_trade():
            return False
        if size_fraction_of_equity <= 0 or price <= 0:
            return False

        notional = self._engine.equity * size_fraction_of_equity * self.leverage
        size_check = check_position_size(notional, self._engine.equity)
        if not size_check.allowed:
            self._kill_switch.trigger_pause(
                "position_size_blocked",
                duration_seconds=RiskLimits.CONSECUTIVE_LOSS_COOLDOWN_SECONDS,
                details={"reason": size_check.reason},
            )
            return False

        return self._engine.open_position(side, ts, price, size_fraction_of_equity)
