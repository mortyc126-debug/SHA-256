"""Tests for P&L accounting and derived risk metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scalping_bot.risk.accounting import Accountant, Trade


def make_trade(
    pnl: float,
    side: str = "long",
    ts: datetime | None = None,
) -> Trade:
    """Helper to build a Trade with sensible defaults."""
    return Trade(
        timestamp=ts or datetime.now(UTC),
        side=side,
        entry_price=68_000.0,
        exit_price=68_000.0 + (pnl / 0.001),  # arbitrary, not used for math
        size_usd=30.0,
        pnl_usd=pnl,
    )


class TestInitialState:
    def test_starting_capital_required_positive(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Accountant(0)
        with pytest.raises(ValueError, match="positive"):
            Accountant(-100)

    def test_initial_equity_equals_starting(self) -> None:
        acc = Accountant(100.0)
        assert acc.equity == 100.0
        assert acc.starting_capital == 100.0
        assert acc.realized_pnl == 0.0
        assert acc.unrealized_pnl == 0.0
        assert acc.peak_equity == 100.0

    def test_initial_drawdown_is_zero(self) -> None:
        acc = Accountant(100.0)
        assert acc.drawdown_pct == 0.0

    def test_initial_trade_count_is_zero(self) -> None:
        acc = Accountant(100.0)
        assert acc.trade_count == 0
        assert acc.consecutive_losses == 0


class TestRecordTrade:
    def test_winning_trade_increases_equity(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=5.0))
        assert acc.equity == 105.0
        assert acc.realized_pnl == 5.0

    def test_losing_trade_decreases_equity(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=-3.0))
        assert acc.equity == 97.0
        assert acc.realized_pnl == -3.0

    def test_multiple_trades_accumulate(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=2.0))
        acc.record_trade(make_trade(pnl=-1.0))
        acc.record_trade(make_trade(pnl=3.0))
        assert acc.equity == 104.0
        assert acc.trade_count == 3

    def test_trade_with_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="tz-aware"):
            Trade(
                timestamp=datetime(2026, 4, 13, 12, 0, 0),  # naive
                side="long",
                entry_price=70_000,
                exit_price=70_100,
                size_usd=30,
                pnl_usd=1,
            )

    def test_trade_with_invalid_side_rejected(self) -> None:
        with pytest.raises(ValueError, match="side"):
            Trade(
                timestamp=datetime.now(UTC),
                side="sideways",  # invalid
                entry_price=70_000,
                exit_price=70_100,
                size_usd=30,
                pnl_usd=1,
            )


class TestUnrealized:
    def test_update_unrealized_reflects_in_equity(self) -> None:
        acc = Accountant(100.0)
        acc.update_unrealized(5.0)
        assert acc.equity == 105.0
        assert acc.unrealized_pnl == 5.0

    def test_updating_unrealized_multiple_times_replaces_not_accumulates(self) -> None:
        acc = Accountant(100.0)
        acc.update_unrealized(5.0)
        acc.update_unrealized(3.0)
        assert acc.unrealized_pnl == 3.0
        assert acc.equity == 103.0

    def test_unrealized_loss(self) -> None:
        acc = Accountant(100.0)
        acc.update_unrealized(-7.5)
        assert acc.equity == 92.5


class TestPeakEquityAndDrawdown:
    def test_peak_rises_with_wins(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=10.0))
        assert acc.peak_equity == 110.0

    def test_peak_does_not_fall_on_loss(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=10.0))
        assert acc.peak_equity == 110.0
        acc.record_trade(make_trade(pnl=-5.0))
        assert acc.peak_equity == 110.0  # unchanged
        assert acc.equity == 105.0

    def test_drawdown_calculated_correctly(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=20.0))  # peak 120
        acc.record_trade(make_trade(pnl=-30.0))  # equity 90
        # Drawdown = (120 - 90) / 120 = 0.25
        assert acc.drawdown_pct == pytest.approx(0.25)

    def test_unrealized_contributes_to_peak(self) -> None:
        acc = Accountant(100.0)
        acc.update_unrealized(15.0)
        assert acc.peak_equity == 115.0


class TestDailyReset:
    def test_same_day_no_reset(self) -> None:
        t0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)
        acc = Accountant(100.0, now=t0)
        acc.record_trade(make_trade(pnl=5.0, ts=t0))
        t_later = t0 + timedelta(hours=5)
        # Still same UTC date → daily_pnl from start-of-day equity
        assert acc.daily_pnl_pct(now=t_later) == pytest.approx(0.05)

    def test_new_day_triggers_reset(self) -> None:
        t0 = datetime(2026, 4, 13, 23, 0, 0, tzinfo=UTC)
        acc = Accountant(100.0, now=t0)
        acc.record_trade(make_trade(pnl=5.0, ts=t0))
        t_next = datetime(2026, 4, 14, 1, 0, 0, tzinfo=UTC)
        # Next UTC day: daily_pnl resets to 0 (baseline = 105)
        assert acc.daily_pnl_pct(now=t_next) == pytest.approx(0.0)

    def test_daily_loss_visible(self) -> None:
        t0 = datetime(2026, 4, 13, 0, 0, 0, tzinfo=UTC)
        acc = Accountant(100.0, now=t0)
        acc.record_trade(make_trade(pnl=-3.0, ts=t0))
        assert acc.daily_pnl_pct(now=t0) == pytest.approx(-0.03)


class TestConsecutiveLosses:
    def test_no_trades_no_losses(self) -> None:
        assert Accountant(100.0).consecutive_losses == 0

    def test_single_win_no_losses(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=1.0))
        assert acc.consecutive_losses == 0

    def test_count_trailing_losses(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=-1))
        acc.record_trade(make_trade(pnl=-1))
        acc.record_trade(make_trade(pnl=-1))
        assert acc.consecutive_losses == 3

    def test_win_resets_counter(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=-1))
        acc.record_trade(make_trade(pnl=-1))
        acc.record_trade(make_trade(pnl=+2))  # win
        assert acc.consecutive_losses == 0
        acc.record_trade(make_trade(pnl=-1))
        assert acc.consecutive_losses == 1

    def test_zero_pnl_not_a_loss(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=-1))
        acc.record_trade(make_trade(pnl=0))  # break-even
        assert acc.consecutive_losses == 0  # chain broken


class TestTradesInLastHour:
    def test_no_trades(self) -> None:
        acc = Accountant(100.0)
        now = datetime.now(UTC)
        assert acc.trades_in_last_hour(now=now) == 0

    def test_all_recent_trades_counted(self) -> None:
        t0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)
        acc = Accountant(100.0, now=t0)
        for _ in range(5):
            acc.record_trade(make_trade(pnl=0.1, ts=t0))
        now = t0 + timedelta(minutes=30)
        assert acc.trades_in_last_hour(now=now) == 5

    def test_old_trades_excluded(self) -> None:
        t0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)
        acc = Accountant(100.0, now=t0)
        # Old trades
        for _ in range(3):
            acc.record_trade(make_trade(pnl=0.1, ts=t0))
        # Query 2 hours later
        now = t0 + timedelta(hours=2)
        assert acc.trades_in_last_hour(now=now) == 0

    def test_mixed_ages(self) -> None:
        t0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)
        acc = Accountant(100.0, now=t0)
        for _ in range(2):
            acc.record_trade(make_trade(pnl=0.1, ts=t0))
        for _ in range(3):
            acc.record_trade(make_trade(pnl=0.1, ts=t0 + timedelta(minutes=50)))
        now = t0 + timedelta(minutes=55)
        assert acc.trades_in_last_hour(now=now) == 5

        later = t0 + timedelta(minutes=90)  # first batch just rolled out
        assert acc.trades_in_last_hour(now=later) == 3


class TestTradesImmutability:
    def test_trades_view_is_tuple(self) -> None:
        acc = Accountant(100.0)
        acc.record_trade(make_trade(pnl=1.0))
        snapshot = acc.trades
        assert isinstance(snapshot, tuple)
        acc.record_trade(make_trade(pnl=2.0))
        # Snapshot stays at 1
        assert len(snapshot) == 1
        assert len(acc.trades) == 2
