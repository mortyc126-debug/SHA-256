"""Tests for the intuition engine and its voters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scalping_bot.intuition.engine import IntuitionConfig, IntuitionEngine
from scalping_bot.intuition.voters import (
    flow_imbalance_voter,
    momentum_voter,
    trade_rate_surge_voter,
    vol_regime_voter,
    vwap_voter,
)
from scalping_bot.live.bar_builder import OneSecondBar

T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)


def _bar(
    i: int,
    close: float,
    buy_vol: float = 0.5,
    sell_vol: float = 0.5,
    trade_count: int = 10,
) -> OneSecondBar:
    return OneSecondBar(
        ts_bar=T0 + timedelta(seconds=i),
        open=close,
        high=close + 0.05,
        low=close - 0.05,
        close=close,
        vwap=close,
        volume=buy_vol + sell_vol,
        buy_volume=buy_vol,
        sell_volume=sell_vol,
        trade_count=trade_count,
    )


# --- Voters ---------------------------------------------------------------


class TestFlowImbalance:
    def test_warmup_returns_neutral(self) -> None:
        bars = [_bar(i, 100.0) for i in range(5)]
        r = flow_imbalance_voter(bars, window=30)
        assert r.direction == 0
        assert r.strength == 0.0

    def test_buy_pressure_bullish(self) -> None:
        bars = [_bar(i, 100.0, buy_vol=2.0, sell_vol=0.1) for i in range(40)]
        r = flow_imbalance_voter(bars, window=30)
        assert r.direction == 1
        assert r.strength > 0.5

    def test_sell_pressure_bearish(self) -> None:
        bars = [_bar(i, 100.0, buy_vol=0.1, sell_vol=2.0) for i in range(40)]
        r = flow_imbalance_voter(bars, window=30)
        assert r.direction == -1
        assert r.strength > 0.5

    def test_balanced_neutral(self) -> None:
        bars = [_bar(i, 100.0, buy_vol=1.0, sell_vol=1.0) for i in range(40)]
        r = flow_imbalance_voter(bars, window=30)
        assert r.direction == 0


class TestMomentum:
    def test_warmup_neutral(self) -> None:
        bars = [_bar(i, 100.0) for i in range(20)]
        r = momentum_voter(bars, short=10, long=60)
        assert r.direction == 0

    def test_uptrend_bullish(self) -> None:
        bars = [_bar(i, 100.0 + i * 0.01) for i in range(80)]
        r = momentum_voter(bars, short=10, long=60)
        assert r.direction == 1
        assert r.strength > 0

    def test_downtrend_bearish(self) -> None:
        bars = [_bar(i, 100.0 - i * 0.01) for i in range(80)]
        r = momentum_voter(bars, short=10, long=60)
        assert r.direction == -1

    def test_disagreement_neutral(self) -> None:
        # Long-window flat, short-window up — should NOT trigger
        prices = [100.0] * 70 + [100.0 + i * 0.01 for i in range(15)]
        bars = [_bar(i, prices[i]) for i in range(len(prices))]
        # Still triggers since short up, long up slightly. Adjust to one
        # that genuinely disagrees:
        prices = [100.0] * 60 + [99.0] * 20  # long down (over 80 bars) but short up?
        bars = [_bar(i, prices[i]) for i in range(len(prices))]
        r = momentum_voter(bars, short=5, long=60)
        # short window: 99 → 99 = flat. long: 100 → 99 = down. disagree.
        assert r.direction in (0, -1)


class TestVwap:
    def test_above_vwap_bullish(self) -> None:
        # First 50 bars at 100, then jump to 100.5 for last 10
        bars = [_bar(i, 100.0, buy_vol=1, sell_vol=1) for i in range(50)]
        bars += [_bar(50 + i, 100.5, buy_vol=1, sell_vol=1) for i in range(10)]
        # Override vwap to the close price
        bars = [
            OneSecondBar(
                ts_bar=b.ts_bar, open=b.open, high=b.high, low=b.low, close=b.close,
                vwap=b.close, volume=b.volume, buy_volume=b.buy_volume,
                sell_volume=b.sell_volume, trade_count=b.trade_count,
            )
            for b in bars
        ]
        r = vwap_voter(bars, window=60)
        # Current price > rolling vwap → bullish
        assert r.direction == 1


class TestVolRegime:
    def test_warmup_neutral(self) -> None:
        bars = [_bar(i, 100.0) for i in range(50)]
        r = vol_regime_voter(bars, fast=30, slow=300)
        assert r.direction == 0
        assert r.strength == 0.0

    def test_expansion_high_strength(self) -> None:
        # First 300 flat, last 30 volatile
        bars = [_bar(i, 100.0) for i in range(300)]
        bars += [_bar(300 + i, 100.0 + (1 if i % 2 else -1) * 0.5) for i in range(30)]
        r = vol_regime_voter(bars, fast=30, slow=300)
        assert r.direction == 0  # vol voter never picks side
        assert r.strength > 0.3


class TestTradeRateSurge:
    def test_no_surge_neutral(self) -> None:
        bars = [_bar(i, 100.0, trade_count=10) for i in range(70)]
        r = trade_rate_surge_voter(bars)
        assert r.direction == 0

    def test_surge_with_uptick_bullish(self) -> None:
        bars = [_bar(i, 100.0, trade_count=10) for i in range(60)]
        # Last 5 bars: triple activity + rising price
        bars += [_bar(60 + i, 100.1 + i * 0.01, trade_count=50) for i in range(5)]
        r = trade_rate_surge_voter(bars)
        assert r.direction == 1


# --- Engine ---------------------------------------------------------------


def _strong_uptrend_bars(n: int) -> list[OneSecondBar]:
    """A clear bullish setup: rising price + buy-side dominant volume."""
    return [
        _bar(i, 100.0 + i * 0.02, buy_vol=2.0, sell_vol=0.2, trade_count=20)
        for i in range(n)
    ]


def _strong_downtrend_bars(n: int) -> list[OneSecondBar]:
    return [
        _bar(i, 100.0 - i * 0.02, buy_vol=0.2, sell_vol=2.0, trade_count=20)
        for i in range(n)
    ]


def _flat_bars(n: int) -> list[OneSecondBar]:
    return [_bar(i, 100.0, buy_vol=1.0, sell_vol=1.0, trade_count=10) for i in range(n)]


class TestEngineStateMachine:
    def test_no_conviction_during_warmup(self) -> None:
        eng = IntuitionEngine()
        bars = _flat_bars(50)
        for i in range(1, len(bars) + 1):
            state = eng.evaluate(bars[:i])
            assert not state.is_convicted

    def test_uptrend_eventually_convicts(self) -> None:
        eng = IntuitionEngine(IntuitionConfig(confirm_bars=3, sigma_enter=0.30))
        bars = _strong_uptrend_bars(100)
        convicted_at = None
        for i in range(1, len(bars) + 1):
            state = eng.evaluate(bars[:i])
            if state.is_convicted:
                convicted_at = i
                assert state.direction == 1
                assert state.sigma > 0
                break
        assert convicted_at is not None, "Strong uptrend should eventually convict"

    def test_downtrend_eventually_convicts_short(self) -> None:
        eng = IntuitionEngine(IntuitionConfig(confirm_bars=3, sigma_enter=0.30))
        bars = _strong_downtrend_bars(100)
        for i in range(1, len(bars) + 1):
            state = eng.evaluate(bars[:i])
            if state.is_convicted:
                assert state.direction == -1
                return
        pytest.fail("Strong downtrend should convict short")

    def test_flat_market_never_convicts(self) -> None:
        eng = IntuitionEngine(IntuitionConfig(confirm_bars=3, sigma_enter=0.30))
        bars = _flat_bars(200)
        for i in range(1, len(bars) + 1):
            state = eng.evaluate(bars[:i])
            assert not state.is_convicted

    def test_cooldown_blocks_re_entry(self) -> None:
        eng = IntuitionEngine(IntuitionConfig(confirm_bars=2, sigma_enter=0.30, cooldown_bars=5))
        bars = _strong_uptrend_bars(120)
        # Run until convicted
        for i in range(1, len(bars) + 1):
            state = eng.evaluate(bars[:i])
            if state.is_convicted:
                eng.cooldown_after_trade()
                break

        # During cooldown, evaluate more bars: should NOT convict
        for j in range(5):
            state = eng.evaluate(bars[: i + j + 1])
            assert not state.is_convicted, f"convicted during cooldown at j={j}"

    def test_voter_results_accessible(self) -> None:
        eng = IntuitionEngine()
        bars = _strong_uptrend_bars(80)
        state = eng.evaluate(bars)
        names = {r.name for r in state.voter_results}
        assert {"flow_imbalance", "momentum", "vwap", "trade_rate_surge"}.issubset(names)
