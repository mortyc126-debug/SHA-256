"""Tests for hardcoded risk limits and validation functions.

These tests exist mainly as a tripwire: if someone changes a constant,
the corresponding test fails and forces them to explain why in a commit
message. This is intentional friction.
"""

from __future__ import annotations

import pytest

from scalping_bot.risk import limits
from scalping_bot.risk.limits import (
    RiskLimits,
    check_leverage,
    check_liquidation_distance,
    check_position_size,
)


class TestConstants:
    """Verify hardcoded constants match documented values."""

    def test_max_leverage_is_3(self) -> None:
        assert RiskLimits.MAX_LEVERAGE == 3.0
        assert limits.MAX_LEVERAGE == 3.0

    def test_max_position_pct_is_30(self) -> None:
        assert RiskLimits.MAX_POSITION_PCT_OF_EQUITY == 0.30

    def test_max_daily_loss_pct_is_3(self) -> None:
        assert RiskLimits.MAX_DAILY_LOSS_PCT == 0.03

    def test_kill_switch_drawdown_is_10(self) -> None:
        assert RiskLimits.KILL_SWITCH_DRAWDOWN_PCT == 0.10

    def test_max_consecutive_losses_is_3(self) -> None:
        assert RiskLimits.MAX_CONSECUTIVE_LOSSES == 3

    def test_max_open_positions_is_1(self) -> None:
        assert RiskLimits.MAX_OPEN_POSITIONS == 1

    def test_min_liquidation_distance_is_10(self) -> None:
        assert RiskLimits.MIN_LIQUIDATION_DISTANCE_PCT == 0.10

    def test_max_trades_per_hour_is_20(self) -> None:
        assert RiskLimits.MAX_TRADES_PER_HOUR == 20

    def test_cooldown_is_positive(self) -> None:
        assert RiskLimits.CONSECUTIVE_LOSS_COOLDOWN_SECONDS > 0

    def test_heartbeat_timeout_is_positive(self) -> None:
        assert RiskLimits.HEARTBEAT_TIMEOUT_SECONDS > 0

    def test_all_percentages_are_in_range(self) -> None:
        """Sanity: all _PCT_ constants should be in (0, 1]."""
        pct_constants = [
            RiskLimits.MAX_POSITION_PCT_OF_EQUITY,
            RiskLimits.MIN_LIQUIDATION_DISTANCE_PCT,
            RiskLimits.MAX_DAILY_LOSS_PCT,
            RiskLimits.KILL_SWITCH_DRAWDOWN_PCT,
        ]
        for p in pct_constants:
            assert 0 < p <= 1, f"percentage {p} not in (0, 1]"


class TestCheckLeverage:
    def test_accepts_exactly_max(self) -> None:
        result = check_leverage(RiskLimits.MAX_LEVERAGE)
        assert result.allowed
        assert result.reason == "ok"

    def test_accepts_below_max(self) -> None:
        assert check_leverage(1.0).allowed
        assert check_leverage(2.5).allowed

    def test_rejects_above_max(self) -> None:
        result = check_leverage(5.0)
        assert not result.allowed
        assert "exceeds MAX_LEVERAGE" in result.reason

    def test_rejects_10x(self) -> None:
        assert not check_leverage(10.0).allowed

    def test_rejects_zero(self) -> None:
        result = check_leverage(0.0)
        assert not result.allowed
        assert "positive" in result.reason

    def test_rejects_negative(self) -> None:
        assert not check_leverage(-1.0).allowed


class TestCheckPositionSize:
    def test_accepts_under_limit(self) -> None:
        # 20% of equity — under 30% cap
        result = check_position_size(notional_usd=20.0, equity_usd=100.0)
        assert result.allowed

    def test_accepts_exactly_at_limit(self) -> None:
        # 30% exactly
        result = check_position_size(notional_usd=30.0, equity_usd=100.0)
        assert result.allowed

    def test_rejects_over_limit(self) -> None:
        # 40% — over 30% cap
        result = check_position_size(notional_usd=40.0, equity_usd=100.0)
        assert not result.allowed
        assert "exceeds MAX_POSITION_PCT_OF_EQUITY" in result.reason

    def test_rejects_huge_position(self) -> None:
        # User tries to go 3x with full equity (common $100 lever mistake)
        result = check_position_size(notional_usd=300.0, equity_usd=100.0)
        assert not result.allowed

    def test_rejects_negative_notional(self) -> None:
        assert not check_position_size(notional_usd=-10.0, equity_usd=100.0).allowed

    def test_rejects_zero_equity(self) -> None:
        assert not check_position_size(notional_usd=10.0, equity_usd=0.0).allowed


class TestCheckLiquidationDistance:
    def test_accepts_safe_distance(self) -> None:
        # 15% distance > 10% required
        result = check_liquidation_distance(mark_price=70_000, liquidation_price=59_500)
        assert result.allowed

    def test_rejects_too_close(self) -> None:
        # 5% distance < 10% required
        result = check_liquidation_distance(mark_price=70_000, liquidation_price=66_500)
        assert not result.allowed
        assert "below MIN_LIQUIDATION_DISTANCE_PCT" in result.reason

    def test_accepts_exactly_at_limit(self) -> None:
        # Exactly 10%
        result = check_liquidation_distance(mark_price=70_000, liquidation_price=63_000)
        assert result.allowed

    def test_works_for_short_side(self) -> None:
        # Short position: liquidation above mark
        result = check_liquidation_distance(mark_price=70_000, liquidation_price=80_500)
        assert result.allowed  # 15% above

    def test_rejects_invalid_prices(self) -> None:
        assert not check_liquidation_distance(0, 100).allowed
        assert not check_liquidation_distance(100, 0).allowed
        assert not check_liquidation_distance(-1, 100).allowed


class TestImmutability:
    """Ensure constants cannot be accidentally reassigned.

    Python does not enforce `Final` at runtime, but class-level assignment
    is still visible in a diff. These tests are documentation.
    """

    def test_risk_limits_has_expected_attributes(self) -> None:
        expected = {
            "MAX_LEVERAGE",
            "MAX_POSITION_PCT_OF_EQUITY",
            "MAX_OPEN_POSITIONS",
            "MIN_LIQUIDATION_DISTANCE_PCT",
            "MAX_DAILY_LOSS_PCT",
            "KILL_SWITCH_DRAWDOWN_PCT",
            "MAX_CONSECUTIVE_LOSSES",
            "CONSECUTIVE_LOSS_COOLDOWN_SECONDS",
            "MAX_TRADES_PER_HOUR",
            "HEARTBEAT_TIMEOUT_SECONDS",
        }
        actual = {name for name in dir(RiskLimits) if not name.startswith("_")}
        assert expected == actual, f"missing or extra: {expected ^ actual}"


@pytest.mark.parametrize(
    ("notional", "equity", "allowed"),
    [
        (10.0, 100.0, True),
        (30.0, 100.0, True),
        (30.01, 100.0, False),
        (29.99, 100.0, True),
        (90.0, 100.0, False),
        (0.0, 100.0, True),
    ],
)
def test_position_size_boundaries(notional: float, equity: float, allowed: bool) -> None:
    assert check_position_size(notional, equity).allowed is allowed
