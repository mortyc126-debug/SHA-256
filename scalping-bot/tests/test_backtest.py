"""Tests for the backtest engine, strategy, metrics, and runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from scalping_bot.backtest.engine import (
    DEFAULT_SLIPPAGE_BPS,
    BacktestEngine,
    CompletedTrade,
    FeeModel,
    Position,
    Side,
)
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.backtest.runner import run_walk_forward_backtest
from scalping_bot.backtest.strategy import Action, StrategyConfig, ThresholdStrategy

T0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


# --- Engine ---------------------------------------------------------------


class TestEngine:
    def test_initial_state(self) -> None:
        e = BacktestEngine(starting_capital_usd=100.0)
        assert e.equity == 100.0
        assert e.position is None
        assert e.trades == ()
        assert e.drawdown_pct == 0.0

    def test_open_long_costs_fee(self) -> None:
        e = BacktestEngine(starting_capital_usd=100.0, leverage=3.0)
        ok = e.open_position(Side.LONG, T0, price=100_000.0, size_fraction_of_equity=0.30)
        assert ok
        assert e.position is not None
        # notional = 100 * 0.30 * 3.0 = 90, fee + slip taker
        expected_cost = 90.0 * (0.00055 + DEFAULT_SLIPPAGE_BPS / 10_000)
        assert e.equity == pytest.approx(100.0 - expected_cost)

    def test_cannot_open_with_existing_position(self) -> None:
        e = BacktestEngine()
        e.open_position(Side.LONG, T0, 100.0, 0.1)
        ok = e.open_position(Side.SHORT, T0, 100.0, 0.1)
        assert not ok

    def test_close_long_winning(self) -> None:
        e = BacktestEngine(starting_capital_usd=100.0, leverage=1.0)
        e.open_position(Side.LONG, T0, price=100.0, size_fraction_of_equity=1.0)
        # Open notional = 100 * 1.0 * 1 = 100
        # Move price up 10% → unrealized = 10
        completed = e.close_position(T0 + timedelta(seconds=30), 110.0, "manual")
        assert completed is not None
        assert completed.side == Side.LONG
        assert completed.pnl_usd > 0
        assert e.position is None
        assert len(e.trades) == 1

    def test_close_short_winning(self) -> None:
        e = BacktestEngine(starting_capital_usd=100.0, leverage=1.0)
        e.open_position(Side.SHORT, T0, price=100.0, size_fraction_of_equity=1.0)
        completed = e.close_position(T0 + timedelta(seconds=10), 90.0, "tp")
        assert completed is not None
        assert completed.pnl_usd > 0

    def test_close_without_position_returns_none(self) -> None:
        e = BacktestEngine()
        assert e.close_position(T0, 100.0, "noop") is None

    def test_drawdown_tracks_peak(self) -> None:
        e = BacktestEngine(starting_capital_usd=100.0, leverage=1.0)
        e.open_position(Side.LONG, T0, 100.0, 1.0)
        e.close_position(T0 + timedelta(seconds=10), 110.0, "tp")
        # equity now ~109 (after fees)
        peak = e.equity
        e.open_position(Side.LONG, T0 + timedelta(seconds=20), 110.0, 1.0)
        e.close_position(T0 + timedelta(seconds=30), 105.0, "sl")
        # Now equity dropped
        assert e.drawdown_pct > 0
        assert e.equity < peak

    def test_invalid_inputs_rejected(self) -> None:
        e = BacktestEngine()
        assert not e.open_position(Side.LONG, T0, price=0, size_fraction_of_equity=0.1)
        assert not e.open_position(Side.LONG, T0, price=100, size_fraction_of_equity=0)
        assert not e.open_position(Side.LONG, T0, price=100, size_fraction_of_equity=-0.1)

    def test_reset_clears_state(self) -> None:
        e = BacktestEngine(starting_capital_usd=100.0)
        e.open_position(Side.LONG, T0, 100.0, 0.5)
        e.close_position(T0, 110.0, "tp")
        e.reset()
        assert e.equity == 100.0
        assert e.trades == ()


class TestFeeModel:
    def test_taker_costs(self) -> None:
        fm = FeeModel(taker_fee_rate=0.001, maker_fee_rate=-0.0001, slippage_bps=2.0)
        # taker: notional * (0.001 + 0.0002) = 0.0012 * notional
        assert fm.entry_cost(1000.0, taker=True) == pytest.approx(1.2)

    def test_maker_can_be_negative(self) -> None:
        fm = FeeModel(taker_fee_rate=0.001, maker_fee_rate=-0.0001, slippage_bps=2.0)
        # maker: notional * (-0.0001 + 0) = -0.1 (rebate)
        assert fm.entry_cost(1000.0, taker=False) == pytest.approx(-0.1)


class TestPosition:
    def test_unrealized_long(self) -> None:
        p = Position(
            side=Side.LONG,
            entry_ts=T0,
            entry_price=100.0,
            notional_usd=100.0,
            fee_paid_usd=0.5,
        )
        assert p.unrealized_pnl(110.0) == pytest.approx(10.0)
        assert p.unrealized_pnl(90.0) == pytest.approx(-10.0)

    def test_unrealized_short(self) -> None:
        p = Position(
            side=Side.SHORT,
            entry_ts=T0,
            entry_price=100.0,
            notional_usd=100.0,
            fee_paid_usd=0.5,
        )
        assert p.unrealized_pnl(90.0) == pytest.approx(10.0)
        assert p.unrealized_pnl(110.0) == pytest.approx(-10.0)

    def test_zero_price_safe(self) -> None:
        p = Position(Side.LONG, T0, 100.0, 100.0, 0)
        assert p.unrealized_pnl(0) == 0.0


# --- Strategy -------------------------------------------------------------


def _make_engine() -> BacktestEngine:
    return BacktestEngine(starting_capital_usd=100.0, leverage=3.0)


class TestStrategy:
    def test_no_action_below_threshold(self) -> None:
        s = ThresholdStrategy(StrategyConfig(enter_threshold=0.7))
        e = _make_engine()
        action = s.step(e, T0, 100_000, proba_up=0.5, proba_down=0.4)
        assert action == Action.HOLD
        assert e.position is None

    def test_opens_long_on_strong_up_signal(self) -> None:
        s = ThresholdStrategy(StrategyConfig(enter_threshold=0.5))
        e = _make_engine()
        action = s.step(e, T0, 100_000, proba_up=0.7, proba_down=0.1)
        assert action == Action.OPEN_LONG
        assert e.position is not None
        assert e.position.side == Side.LONG

    def test_opens_short_on_strong_down_signal(self) -> None:
        s = ThresholdStrategy(StrategyConfig(enter_threshold=0.5))
        e = _make_engine()
        action = s.step(e, T0, 100_000, proba_up=0.1, proba_down=0.8)
        assert action == Action.OPEN_SHORT

    def test_take_profit_closes(self) -> None:
        s = ThresholdStrategy(
            StrategyConfig(
                enter_threshold=0.5, take_profit_bps=10.0, stop_loss_bps=100.0
            )
        )
        e = _make_engine()
        s.step(e, T0, 100.0, 0.7, 0.1)
        # 10 bps move up = 100 * 1.001 = 100.1
        action = s.step(e, T0 + timedelta(seconds=1), 100.11, 0.6, 0.1)
        assert action == Action.CLOSE
        assert e.position is None
        assert e.trades[-1].reason_close == "take_profit"

    def test_stop_loss_closes(self) -> None:
        s = ThresholdStrategy(
            StrategyConfig(
                enter_threshold=0.5, take_profit_bps=100.0, stop_loss_bps=10.0
            )
        )
        e = _make_engine()
        s.step(e, T0, 100.0, 0.7, 0.1)
        action = s.step(e, T0 + timedelta(seconds=1), 99.89, 0.6, 0.1)
        assert action == Action.CLOSE
        assert e.trades[-1].reason_close == "stop_loss"

    def test_time_exit(self) -> None:
        s = ThresholdStrategy(
            StrategyConfig(enter_threshold=0.5, max_hold_bars=2, take_profit_bps=1000, stop_loss_bps=1000)
        )
        e = _make_engine()
        s.step(e, T0, 100.0, 0.7, 0.1)  # open
        s.step(e, T0 + timedelta(seconds=1), 100.0, 0.6, 0.1)  # +1 bar
        action = s.step(e, T0 + timedelta(seconds=2), 100.0, 0.6, 0.1)  # +2 bars
        assert action == Action.CLOSE
        assert e.trades[-1].reason_close == "time_exit"

    def test_reversal_closes_long(self) -> None:
        s = ThresholdStrategy(
            StrategyConfig(
                enter_threshold=0.5,
                exit_threshold=0.6,
                take_profit_bps=1000,
                stop_loss_bps=1000,
                max_hold_bars=10000,
            )
        )
        e = _make_engine()
        s.step(e, T0, 100.0, 0.7, 0.1)
        action = s.step(e, T0 + timedelta(seconds=1), 100.0, 0.1, 0.7)
        assert action == Action.CLOSE
        assert e.trades[-1].reason_close == "reversal_down"


# --- Metrics --------------------------------------------------------------


def _trade(pnl: float, hold_s: float = 30.0, fees: float = 0.05) -> CompletedTrade:
    return CompletedTrade(
        side=Side.LONG,
        entry_ts=T0,
        exit_ts=T0 + timedelta(seconds=hold_s),
        entry_price=100.0,
        exit_price=100.0 + pnl,
        notional_usd=30.0,
        fees_usd=fees,
        pnl_usd=pnl,
        reason_close="test",
    )


class TestMetrics:
    def test_empty_summary(self) -> None:
        s = summarize_trades([], starting_capital_usd=100.0)
        assert s.n_trades == 0
        assert s.total_pnl_usd == 0.0
        assert s.win_rate == 0.0

    def test_basic_summary(self) -> None:
        trades = [_trade(2.0), _trade(-1.0), _trade(3.0), _trade(-0.5)]
        s = summarize_trades(trades, starting_capital_usd=100.0)
        assert s.n_trades == 4
        assert s.n_wins == 2
        assert s.n_losses == 2
        assert s.win_rate == 0.5
        assert s.total_pnl_usd == pytest.approx(3.5)
        # Profit factor = wins(5) / |losses|(1.5) ≈ 3.33
        assert s.profit_factor == pytest.approx(5.0 / 1.5)

    def test_drawdown_computed(self) -> None:
        # +5, -10 → dd = (105 - 95) / 105 ≈ 0.095
        trades = [_trade(5.0), _trade(-10.0)]
        s = summarize_trades(trades, starting_capital_usd=100.0)
        assert s.max_drawdown_pct == pytest.approx(10.0 / 105.0, abs=1e-4)

    def test_only_wins_infinite_profit_factor(self) -> None:
        s = summarize_trades([_trade(1.0), _trade(2.0)], starting_capital_usd=100.0)
        assert s.profit_factor == float("inf")

    def test_sharpe_annualized_when_holdings_known(self) -> None:
        trades = [_trade(1.0, hold_s=60.0), _trade(-0.5, hold_s=60.0), _trade(2.0, hold_s=60.0)]
        s = summarize_trades(trades, starting_capital_usd=100.0)
        assert s.sharpe_annualized is not None


# --- Runner integration ---------------------------------------------------


def _synth_feature_matrix(n: int = 1000, seed: int = 0) -> pl.DataFrame:
    """Synthetic frame with features, label, and a price series."""
    import numpy as np

    rng = np.random.default_rng(seed)
    f1 = rng.standard_normal(n)
    f2 = rng.standard_normal(n)
    score = f1 + 0.3 * f2 + 0.4 * rng.standard_normal(n)
    label = np.where(score > 0.5, 1, np.where(score < -0.5, -1, 0)).astype(np.int8)
    price = 100.0 + np.cumsum(rng.standard_normal(n) * 0.1)
    return pl.DataFrame(
        {
            "ts_bar": [T0 + timedelta(seconds=i) for i in range(n)],
            "f1": f1,
            "f2": f2,
            "close": price,
            "label_30": label,
        }
    )


class TestRunner:
    def test_runs_end_to_end(self) -> None:
        fm = _synth_feature_matrix(2000)
        fold_results, aggregate = run_walk_forward_backtest(
            feature_matrix=fm,
            feature_cols=["f1", "f2"],
            label_col="label_30",
            n_splits=2,
            n_pairwise=2,
            distinguisher_max_iter=200,
        )
        assert len(fold_results) == 2
        assert aggregate.n_trades >= 0  # may be 0 if model never crossed threshold

    def test_rejects_missing_columns(self) -> None:
        fm = pl.DataFrame({"x": [1, 2]})
        with pytest.raises(ValueError, match="ts_bar"):
            run_walk_forward_backtest(fm, ["x"], label_col="label", n_splits=2)

    def test_rejects_missing_price(self) -> None:
        fm = pl.DataFrame(
            {
                "ts_bar": [T0],
                "label_30": [1],
                "f1": [0.0],
            }
        )
        with pytest.raises(ValueError, match="close"):
            run_walk_forward_backtest(fm, ["f1"], label_col="label_30", n_splits=1)
