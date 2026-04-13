"""P&L accounting with UTC day boundaries and drawdown tracking.

All operations are in USD (quoted amounts on BTCUSDT perpetual).
Times are UTC-aware datetimes; naive datetimes are rejected to prevent
the class of bugs where "today" silently means different things on
different machines.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


def _ensure_utc(ts: datetime) -> datetime:
    """Reject naive datetimes, normalize any tz-aware datetime to UTC."""
    if ts.tzinfo is None:
        raise ValueError(f"naive datetime is not allowed, got {ts!r}")
    return ts.astimezone(UTC)


@dataclass(frozen=True)
class Trade:
    """A closed trade. Entry and exit both executed; P&L realized."""

    timestamp: datetime
    """Time of trade close (UTC-aware)."""

    side: str
    """'long' or 'short'."""

    entry_price: float
    exit_price: float
    size_usd: float
    """Notional at entry, USD."""

    pnl_usd: float
    """Realized P&L in USD, after fees."""

    fees_usd: float = 0.0
    reason_close: str = ""

    def __post_init__(self) -> None:
        if self.side not in ("long", "short"):
            raise ValueError(f"side must be 'long' or 'short', got {self.side!r}")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be tz-aware")


class Accountant:
    """Tracks equity, realized/unrealized P&L, daily P&L, drawdown.

    Designed to integrate with the kill switch: callers check derived
    properties (daily_pnl_pct, drawdown_pct, consecutive_losses) and
    trigger the switch when thresholds are breached.
    """

    def __init__(self, starting_capital_usd: float, now: datetime | None = None) -> None:
        if starting_capital_usd <= 0:
            raise ValueError(
                f"starting_capital_usd must be positive, got {starting_capital_usd}"
            )

        init_now = _ensure_utc(now) if now is not None else self._utc_now()

        self._starting_capital: float = float(starting_capital_usd)
        self._realized_pnl: float = 0.0
        self._unrealized_pnl: float = 0.0
        self._peak_equity: float = float(starting_capital_usd)

        self._trades: list[Trade] = []
        self._recent_trades: deque[Trade] = deque(maxlen=500)

        self._daily_start_equity: float = float(starting_capital_usd)
        self._daily_reset_date: date = init_now.date()

    # --- Clock --------------------------------------------------------------

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    def _maybe_reset_daily(self, now: datetime | None = None) -> None:
        current = _ensure_utc(now) if now is not None else self._utc_now()
        today = current.date()
        if today != self._daily_reset_date:
            self._daily_start_equity = self.equity
            self._daily_reset_date = today

    # --- Equity and P&L -----------------------------------------------------

    @property
    def starting_capital(self) -> float:
        return self._starting_capital

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def unrealized_pnl(self) -> float:
        return self._unrealized_pnl

    @property
    def equity(self) -> float:
        """Current equity = starting capital + realized P&L + unrealized P&L."""
        return self._starting_capital + self._realized_pnl + self._unrealized_pnl

    @property
    def peak_equity(self) -> float:
        """All-time peak of equity observed so far."""
        return self._peak_equity

    def update_unrealized(self, unrealized_pnl: float) -> None:
        """Update the unrealized P&L (e.g. mark-to-market on open position)."""
        self._unrealized_pnl = float(unrealized_pnl)
        if self.equity > self._peak_equity:
            self._peak_equity = self.equity

    def record_trade(self, trade: Trade) -> None:
        """Record a closed trade. Updates realized P&L and peak equity."""
        _ensure_utc(trade.timestamp)
        self._realized_pnl += trade.pnl_usd
        self._trades.append(trade)
        self._recent_trades.append(trade)
        if self.equity > self._peak_equity:
            self._peak_equity = self.equity

    # --- Derived risk metrics ----------------------------------------------

    def daily_pnl_pct(self, now: datetime | None = None) -> float:
        """Fractional P&L since start of current UTC day.

        Negative when losing. Rolls over at UTC 00:00.
        """
        self._maybe_reset_daily(now)
        if self._daily_start_equity <= 0:
            return 0.0
        return (self.equity - self._daily_start_equity) / self._daily_start_equity

    @property
    def drawdown_pct(self) -> float:
        """Drawdown from peak equity as non-negative fraction."""
        if self._peak_equity <= 0:
            return 0.0
        dd = (self._peak_equity - self.equity) / self._peak_equity
        return max(0.0, dd)

    @property
    def consecutive_losses(self) -> int:
        """Number of consecutive losing trades ending at the most recent trade."""
        count = 0
        for t in reversed(self._trades):
            if t.pnl_usd < 0:
                count += 1
            else:
                break
        return count

    def trades_in_last(
        self,
        duration: timedelta,
        now: datetime | None = None,
    ) -> int:
        """Count of trades whose timestamps fall within `now - duration .. now`."""
        current = _ensure_utc(now) if now is not None else self._utc_now()
        cutoff = current - duration
        return sum(1 for t in self._recent_trades if t.timestamp >= cutoff)

    def trades_in_last_hour(self, now: datetime | None = None) -> int:
        return self.trades_in_last(timedelta(hours=1), now=now)

    # --- Introspection ------------------------------------------------------

    @property
    def trade_count(self) -> int:
        return len(self._trades)

    @property
    def trades(self) -> tuple[Trade, ...]:
        """Immutable view of all recorded trades."""
        return tuple(self._trades)
