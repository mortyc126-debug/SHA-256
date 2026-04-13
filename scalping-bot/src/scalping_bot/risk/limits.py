"""Hardcoded risk limits.

These constants are intentionally NOT loaded from config files. Changing
them requires modifying this source file, which forces a git diff, code
review, and a test run. This prevents the "just one more time, I'll raise
the leverage" class of accidents that routinely wipes out retail accounts.

All values are justified in docs/research_notes.md §3.

Rule of thumb: if you find yourself wanting to relax a limit at 3 AM
because the market is moving, you are exactly the person these limits
were written for.
"""

from __future__ import annotations

from typing import Final, NamedTuple

# --- Position and leverage --------------------------------------------------

MAX_LEVERAGE: Final[float] = 3.0
"""Maximum leverage multiplier. Pro traders rarely exceed 5x. With $100
capital and 5s-10min scalping, 3x is the upper bound that survives normal
BTC volatility (5-min realized vol of 0.3-1.0% is routine).
"""

MAX_POSITION_PCT_OF_EQUITY: Final[float] = 0.30
"""Maximum notional size of a single position as fraction of equity.
Leaves headroom for unexpected slippage and multi-position scenarios
(even though MAX_OPEN_POSITIONS=1 for now).
"""

MAX_OPEN_POSITIONS: Final[int] = 1
"""Single-symbol scalper. No pyramiding, no averaging down. When we open
a position we close it before opening another.
"""

MIN_LIQUIDATION_DISTANCE_PCT: Final[float] = 0.10
"""Required distance from liquidation price, as fraction of mark price.
Oct 2025 crash cascade showed that "safe" liquidation distances become
unsafe when exchange infrastructure degrades. 10% buffer is a floor, not
a target.
"""

# --- Loss limits ------------------------------------------------------------

MAX_DAILY_LOSS_PCT: Final[float] = 0.03
"""Max loss per UTC day, as fraction of starting-of-day equity.
Hitting this triggers a hard pause until the next UTC 00:00.
Calibrated so 10 bad days in a row = 26% drawdown, not ruin.
"""

KILL_SWITCH_DRAWDOWN_PCT: Final[float] = 0.10
"""Drawdown from all-time peak equity that triggers kill switch.
10% is aggressive for scalping — once hit, the strategy needs review
before restart. Manual reset required.
"""

MAX_CONSECUTIVE_LOSSES: Final[int] = 3
"""Consecutive losing trades that trigger a soft pause. Signals possible
regime break. Auto-resumes after cooldown (see CONSECUTIVE_LOSS_COOLDOWN).
"""

CONSECUTIVE_LOSS_COOLDOWN_SECONDS: Final[int] = 900
"""15 minutes cooldown after consecutive-loss pause."""

# --- Rate and frequency -----------------------------------------------------

MAX_TRADES_PER_HOUR: Final[int] = 20
"""Sanity cap on trade frequency. 20/hour = one every 3 minutes average.
For 5s-10min scalping this should be more than enough. Higher rates
suggest a bug or overactive strategy.
"""

HEARTBEAT_TIMEOUT_SECONDS: Final[int] = 30
"""Maximum age of latest market data tick before we pause. Stale data =
flying blind. Applies to both trade stream and orderbook stream.
"""

# --- Derived and utility ----------------------------------------------------


class LimitCheck(NamedTuple):
    """Result of a risk check. `allowed=False` means the action is blocked."""

    allowed: bool
    reason: str


class RiskLimits:
    """Namespace-only container for the hardcoded constants.

    Exists so callers can `from scalping_bot.risk import RiskLimits` and
    reference `RiskLimits.MAX_LEVERAGE` for readability. Do NOT subclass
    or mutate.
    """

    MAX_LEVERAGE: Final[float] = MAX_LEVERAGE
    MAX_POSITION_PCT_OF_EQUITY: Final[float] = MAX_POSITION_PCT_OF_EQUITY
    MAX_OPEN_POSITIONS: Final[int] = MAX_OPEN_POSITIONS
    MIN_LIQUIDATION_DISTANCE_PCT: Final[float] = MIN_LIQUIDATION_DISTANCE_PCT
    MAX_DAILY_LOSS_PCT: Final[float] = MAX_DAILY_LOSS_PCT
    KILL_SWITCH_DRAWDOWN_PCT: Final[float] = KILL_SWITCH_DRAWDOWN_PCT
    MAX_CONSECUTIVE_LOSSES: Final[int] = MAX_CONSECUTIVE_LOSSES
    CONSECUTIVE_LOSS_COOLDOWN_SECONDS: Final[int] = CONSECUTIVE_LOSS_COOLDOWN_SECONDS
    MAX_TRADES_PER_HOUR: Final[int] = MAX_TRADES_PER_HOUR
    HEARTBEAT_TIMEOUT_SECONDS: Final[int] = HEARTBEAT_TIMEOUT_SECONDS


# --- Validation functions ---------------------------------------------------


def check_leverage(leverage: float) -> LimitCheck:
    """Verify requested leverage is within safe bounds."""
    if leverage <= 0:
        return LimitCheck(False, f"leverage must be positive, got {leverage}")
    if leverage > MAX_LEVERAGE:
        return LimitCheck(
            False,
            f"leverage {leverage}x exceeds MAX_LEVERAGE={MAX_LEVERAGE}x",
        )
    return LimitCheck(True, "ok")


def check_position_size(notional_usd: float, equity_usd: float) -> LimitCheck:
    """Verify a proposed position notional fits within equity fraction limit."""
    if notional_usd < 0:
        return LimitCheck(False, f"notional must be non-negative, got {notional_usd}")
    if equity_usd <= 0:
        return LimitCheck(False, f"equity must be positive, got {equity_usd}")

    max_allowed = equity_usd * MAX_POSITION_PCT_OF_EQUITY
    if notional_usd > max_allowed:
        pct = notional_usd / equity_usd
        return LimitCheck(
            False,
            f"position notional ${notional_usd:.2f} is {pct:.1%} of equity, "
            f"exceeds MAX_POSITION_PCT_OF_EQUITY={MAX_POSITION_PCT_OF_EQUITY:.0%}",
        )
    return LimitCheck(True, "ok")


def check_liquidation_distance(
    mark_price: float,
    liquidation_price: float,
) -> LimitCheck:
    """Verify the liquidation price is far enough from the mark price."""
    if mark_price <= 0:
        return LimitCheck(False, f"mark price must be positive, got {mark_price}")
    if liquidation_price <= 0:
        return LimitCheck(False, f"liquidation price must be positive, got {liquidation_price}")

    distance_pct = abs(mark_price - liquidation_price) / mark_price
    if distance_pct < MIN_LIQUIDATION_DISTANCE_PCT:
        return LimitCheck(
            False,
            f"liquidation distance {distance_pct:.2%} below "
            f"MIN_LIQUIDATION_DISTANCE_PCT={MIN_LIQUIDATION_DISTANCE_PCT:.0%}",
        )
    return LimitCheck(True, "ok")
