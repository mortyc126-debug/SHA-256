"""Tests for IntuitionTrader."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scalping_bot.backtest.engine import BacktestEngine, FeeModel
from scalping_bot.intuition.trader import (
    Action,
    IntuitionTrader,
    IntuitionTraderConfig,
)
from scalping_bot.live.bar_builder import OneSecondBar

T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)


def _bar(i: int, close: float, buy_vol: float = 0.5, sell_vol: float = 0.5) -> OneSecondBar:
    return OneSecondBar(
        ts_bar=T0 + timedelta(seconds=i),
        open=close, high=close + 0.05, low=close - 0.05, close=close,
        vwap=close, volume=buy_vol + sell_vol,
        buy_volume=buy_vol, sell_volume=sell_vol, trade_count=10,
    )


def _uptrend_bars(n: int) -> list[OneSecondBar]:
    return [_bar(i, 100.0 + i * 0.02, buy_vol=2.0, sell_vol=0.2) for i in range(n)]


def _flat_bars(n: int) -> list[OneSecondBar]:
    return [_bar(i, 100.0) for i in range(n)]


class TestConstruction:
    def test_defaults_construct(self) -> None:
        t = IntuitionTrader()
        assert t.intuition is not None
        assert t.super_state is not None  # default use_super_state=True

    def test_disable_super_state(self) -> None:
        cfg = IntuitionTraderConfig(use_super_state=False)
        t = IntuitionTrader(config=cfg)
        assert t.super_state is None


class TestStepIntegration:
    def test_no_action_during_warmup(self) -> None:
        cfg = IntuitionTraderConfig(use_super_state=False, sigma_enter=0.40, confirm_bars=3)
        t = IntuitionTrader(config=cfg)
        engine = BacktestEngine(starting_capital_usd=100, leverage=3.0, fee_model=FeeModel())
        bars = _flat_bars(50)
        for i in range(1, len(bars) + 1):
            action = t.step(engine, bars[i - 1], bars[:i])
            assert action == Action.HOLD
        assert engine.position is None

    def test_uptrend_eventually_opens_long(self) -> None:
        cfg = IntuitionTraderConfig(
            use_super_state=False,
            sigma_enter=0.30,
            confirm_bars=3,
            base_size_fraction=0.10,
        )
        t = IntuitionTrader(config=cfg)
        engine = BacktestEngine(starting_capital_usd=100, leverage=3.0, fee_model=FeeModel())
        bars = _uptrend_bars(150)
        opened = False
        for i in range(1, len(bars) + 1):
            action = t.step(engine, bars[i - 1], bars[:i])
            if action == Action.OPEN_LONG:
                opened = True
                break
        assert opened, "Strong uptrend should eventually trigger open_long"

    def test_position_closed_by_trailing_stop(self) -> None:
        cfg = IntuitionTraderConfig(
            use_super_state=False, sigma_enter=0.30, confirm_bars=3,
            trailing_initial_sl_bps=10, trailing_breakeven_bps=2,
            trailing_distance_bps=2, trailing_initial_lock_bps=1,
        )
        t = IntuitionTrader(config=cfg)
        engine = BacktestEngine(starting_capital_usd=100, leverage=3.0, fee_model=FeeModel())
        # First, ride uptrend to open
        bars = _uptrend_bars(150)
        for i in range(1, len(bars) + 1):
            t.step(engine, bars[i - 1], bars[:i])
            if engine.position is not None:
                break
        assert engine.position is not None

        # Then drop sharply → trailing stop should fire
        drop_bars = list(bars[:i])
        for j in range(20):
            new_bar = _bar(i + j, bars[i - 1].close * (1 - 0.001 * (j + 1)))
            drop_bars.append(new_bar)
            action = t.step(engine, new_bar, drop_bars)
            if action == Action.CLOSE:
                assert engine.position is None
                return
        pytest.fail("Trailing stop did not trigger on sharp drop")

    def test_force_close(self) -> None:
        cfg = IntuitionTraderConfig(use_super_state=False, sigma_enter=0.30, confirm_bars=3)
        t = IntuitionTrader(config=cfg)
        engine = BacktestEngine(starting_capital_usd=100, leverage=3.0, fee_model=FeeModel())
        bars = _uptrend_bars(150)
        for i in range(1, len(bars) + 1):
            t.step(engine, bars[i - 1], bars[:i])
            if engine.position is not None:
                last_bar = bars[i - 1]
                break
        else:
            pytest.skip("Did not open in this run")

        closed = t.force_close(engine, last_bar, "test_end")
        assert closed
        assert engine.position is None


class TestReset:
    def test_reset_clears_position_state(self) -> None:
        cfg = IntuitionTraderConfig(use_super_state=False)
        t = IntuitionTrader(config=cfg)
        # Manually muck with state
        t._bars_in_position = 50
        t._last_open_sigma = 0.7
        t.reset()
        assert t._bars_in_position == 0  # reset zeroed
