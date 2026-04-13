"""Per-bar trade simulation with realistic Bybit-perpetual fees.

Cost model (Bybit USDT perpetual, April 2026):
    - Maker fee:  +0.005% rebate (we earn)
    - Taker fee:  -0.055% (we pay)
    - Slippage:   half-spread + size-impact (default linear in size)
    - Funding:    paid every 8h on open positions; we pay/earn based on
                  funding rate sign and our side. For backtest we apply
                  it as a per-second cost equal to (funding_rate * 3 / 8h)
                  approximately. Configurable; default 0.

The engine processes bars one at a time. The strategy decides actions;
the engine executes them and tracks position, P&L, and trade history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Final


class Side(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """An open position. Closed when exit_price is set."""

    side: Side
    entry_ts: datetime
    entry_price: float
    notional_usd: float
    """Position notional at entry (size_btc * entry_price)."""
    fee_paid_usd: float
    """Cumulative fees paid (entry only until close)."""

    def unrealized_pnl(self, mark_price: float) -> float:
        """P&L in USD if we closed at mark_price right now."""
        if mark_price <= 0:
            return 0.0
        size_btc = self.notional_usd / self.entry_price
        if self.side == Side.LONG:
            return (mark_price - self.entry_price) * size_btc
        return (self.entry_price - mark_price) * size_btc


@dataclass(frozen=True)
class CompletedTrade:
    """A round-trip trade record for analytics."""

    side: Side
    entry_ts: datetime
    exit_ts: datetime
    entry_price: float
    exit_price: float
    notional_usd: float
    fees_usd: float
    pnl_usd: float
    """Realized P&L net of fees."""
    reason_close: str


# Default Bybit BTCUSDT perpetual costs (April 2026)
TAKER_FEE_RATE: Final[float] = 0.00055
MAKER_FEE_RATE: Final[float] = -0.00005  # rebate
DEFAULT_SLIPPAGE_BPS: Final[float] = 1.0  # 1 bp = 0.01% per side


@dataclass
class FeeModel:
    """Configurable fee + slippage model."""

    taker_fee_rate: float = TAKER_FEE_RATE
    maker_fee_rate: float = MAKER_FEE_RATE
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS

    def entry_cost(self, notional_usd: float, taker: bool) -> float:
        """Cost in USD to open a position of `notional_usd`."""
        fee_rate = self.taker_fee_rate if taker else self.maker_fee_rate
        slip = self.slippage_bps / 10_000.0 if taker else 0.0
        return notional_usd * (fee_rate + slip)

    def exit_cost(self, notional_usd: float, taker: bool) -> float:
        """Cost in USD to close a position of `notional_usd`."""
        return self.entry_cost(notional_usd, taker)


@dataclass
class BacktestEngine:
    """Per-bar simulation of trading actions with realistic costs."""

    starting_capital_usd: float = 100.0
    leverage: float = 3.0
    fee_model: FeeModel = field(default_factory=FeeModel)
    use_taker: bool = True

    # Internal state (reset on `reset()`)
    _equity: float = field(init=False, default=0.0)
    _peak_equity: float = field(init=False, default=0.0)
    _position: Position | None = field(init=False, default=None)
    _trades: list[CompletedTrade] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self._equity = self.starting_capital_usd
        self._peak_equity = self.starting_capital_usd

    def reset(self) -> None:
        """Reset all internal state to fresh starting capital."""
        self._equity = self.starting_capital_usd
        self._peak_equity = self.starting_capital_usd
        self._position = None
        self._trades.clear()

    # --- State queries ------------------------------------------------------

    @property
    def equity(self) -> float:
        return self._equity

    @property
    def position(self) -> Position | None:
        return self._position

    @property
    def trades(self) -> tuple[CompletedTrade, ...]:
        return tuple(self._trades)

    @property
    def drawdown_pct(self) -> float:
        if self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - self._equity) / self._peak_equity)

    # --- Actions ------------------------------------------------------------

    def open_position(
        self,
        side: Side,
        ts: datetime,
        price: float,
        size_fraction_of_equity: float,
    ) -> bool:
        """Open a new position. Returns False if blocked by an existing one.

        size_fraction_of_equity is in [0, 1]; actual notional is multiplied
        by leverage.
        """
        if self._position is not None:
            return False
        if size_fraction_of_equity <= 0 or price <= 0:
            return False

        notional = self._equity * size_fraction_of_equity * self.leverage
        if notional <= 0:
            return False

        fee = self.fee_model.entry_cost(notional, taker=self.use_taker)
        self._equity -= fee
        self._position = Position(
            side=side,
            entry_ts=ts,
            entry_price=price,
            notional_usd=notional,
            fee_paid_usd=fee,
        )
        return True

    def close_position(self, ts: datetime, price: float, reason: str) -> CompletedTrade | None:
        """Close any open position. Returns the completed trade, or None."""
        if self._position is None or price <= 0:
            return None

        exit_fee = self.fee_model.exit_cost(self._position.notional_usd, taker=self.use_taker)
        gross_pnl = self._position.unrealized_pnl(price)
        net_pnl = gross_pnl - exit_fee

        self._equity += net_pnl
        self._peak_equity = max(self._peak_equity, self._equity)

        completed = CompletedTrade(
            side=self._position.side,
            entry_ts=self._position.entry_ts,
            exit_ts=ts,
            entry_price=self._position.entry_price,
            exit_price=price,
            notional_usd=self._position.notional_usd,
            fees_usd=self._position.fee_paid_usd + exit_fee,
            pnl_usd=net_pnl,
            reason_close=reason,
        )
        self._trades.append(completed)
        self._position = None
        return completed

    def mark_to_market(self, price: float) -> float:
        """Update peak-equity tracking against an open mark price.

        Returns current unrealized equity (closed equity + unrealized).
        """
        unreal = 0.0
        if self._position is not None and price > 0:
            unreal = self._position.unrealized_pnl(price)
        eq_now = self._equity + unreal
        self._peak_equity = max(self._peak_equity, eq_now)
        return eq_now
