"""Tests for TrailingStopState."""

from __future__ import annotations

import pytest

from scalping_bot.backtest.engine import Side
from scalping_bot.intuition.trailing import TrailingStopConfig, TrailingStopState


@pytest.fixture
def cfg() -> TrailingStopConfig:
    return TrailingStopConfig(
        initial_sl_bps=30.0,
        breakeven_trigger_bps=5.0,
        trail_distance_bps=5.0,
        initial_lock_bps=1.0,
    )


class TestLong:
    def test_initial_stop_below_entry(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, entry_price=100.0, cfg=cfg)
        assert s.current_stop == pytest.approx(100.0 * (1 - 30 / 10_000))
        assert not s.breakeven_triggered

    def test_initial_sl_hit(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, 100.0, cfg)
        # Drop 35 bps → past initial SL of -30 bps
        hit = s.update(100.0 * (1 - 35 / 10_000), cfg)
        assert hit

    def test_no_stop_within_initial_range(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, 100.0, cfg)
        # Drop only 10 bps
        hit = s.update(100.0 * (1 - 10 / 10_000), cfg)
        assert not hit

    def test_breakeven_trigger_locks_profit(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, 100.0, cfg)
        # Move +6 bps → breakeven trigger fires → SL becomes entry + 1 bp
        s.update(100.0 * (1 + 6 / 10_000), cfg)
        assert s.breakeven_triggered
        assert s.current_stop == pytest.approx(100.0 * (1 + 1 / 10_000))

    def test_trailing_after_breakeven(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, 100.0, cfg)
        # Trigger breakeven
        s.update(100.0 * (1 + 6 / 10_000), cfg)
        # Then move up to +20 bps → stop trails to +15 (best=120bps - 5bps)
        s.update(100.0 * (1 + 20 / 10_000), cfg)
        expected_stop = 100.0 * (1 + 20 / 10_000) * (1 - 5 / 10_000)
        assert s.current_stop == pytest.approx(expected_stop)

    def test_stop_never_moves_backward(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, 100.0, cfg)
        s.update(100.0 * (1 + 20 / 10_000), cfg)  # high water 120bps
        high_stop = s.current_stop
        s.update(100.0 * (1 + 10 / 10_000), cfg)  # pulled back to 110bps
        assert s.current_stop == high_stop  # unchanged

    def test_locked_profit_realized(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.LONG, 100.0, cfg)
        s.update(100.0 * (1 + 20 / 10_000), cfg)
        # If price drops back to stop level → realized profit ≈ +15 bps
        stop_price = s.current_stop
        hit = s.update(stop_price - 0.001, cfg)  # just under stop
        assert hit
        assert s.realized_profit_bps_if_stopped() > 0


class TestShort:
    def test_initial_stop_above_entry(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.SHORT, entry_price=100.0, cfg=cfg)
        assert s.current_stop == pytest.approx(100.0 * (1 + 30 / 10_000))

    def test_initial_sl_hit_on_rally(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.SHORT, 100.0, cfg)
        hit = s.update(100.0 * (1 + 35 / 10_000), cfg)
        assert hit

    def test_breakeven_on_drop(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.SHORT, 100.0, cfg)
        # Drop 6 bps (favorable for short) → breakeven
        s.update(100.0 * (1 - 6 / 10_000), cfg)
        assert s.breakeven_triggered
        assert s.current_stop == pytest.approx(100.0 * (1 - 1 / 10_000))

    def test_trailing_after_breakeven_short(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.SHORT, 100.0, cfg)
        s.update(100.0 * (1 - 6 / 10_000), cfg)  # trigger breakeven
        s.update(100.0 * (1 - 20 / 10_000), cfg)  # ride down
        expected_stop = 100.0 * (1 - 20 / 10_000) * (1 + 5 / 10_000)
        assert s.current_stop == pytest.approx(expected_stop)

    def test_stop_never_moves_up_for_short(self, cfg: TrailingStopConfig) -> None:
        s = TrailingStopState.open(Side.SHORT, 100.0, cfg)
        s.update(100.0 * (1 - 20 / 10_000), cfg)
        low_stop = s.current_stop
        s.update(100.0 * (1 - 10 / 10_000), cfg)  # bounced back
        assert s.current_stop == low_stop
