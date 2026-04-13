"""IntuitionTrader — production wrapper around all intuition components.

Composes:
  * IntuitionEngine  — directional-voter consensus into σ-conviction.
  * SuperStateEngine — optional K-archetype voter (O(K) per bar).
  * TrailingStopState — locks profit on favorable moves.
  * BacktestEngine / PaperBroker — actual P&L bookkeeping.

The trader exposes a single `step(engine, bar, recent_bars)` method
that does everything for one bar: mark-to-market, manage open
position (trailing stop / time exit), or evaluate conviction and open
new position. Same interface works for backtest or paper trading.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from scalping_bot.backtest.engine import BacktestEngine, Side
from scalping_bot.intuition.engine import IntuitionConfig, IntuitionEngine, VoterFn
from scalping_bot.intuition.super_state import SuperStateEngine
from scalping_bot.intuition.trailing import TrailingStopConfig, TrailingStopState
from scalping_bot.intuition.voters import (
    VoterResult,
    flow_imbalance_voter,
    momentum_voter,
    trade_rate_surge_voter,
    vwap_voter,
)

if TYPE_CHECKING:
    from scalping_bot.live.bar_builder import OneSecondBar


class Action(Enum):
    HOLD = "hold"
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE = "close"


@dataclass
class IntuitionTraderConfig:
    """All knobs for the integrated trader."""

    # Intuition / conviction
    sigma_enter: float = 0.50
    sigma_exit: float = 0.25
    confirm_bars: int = 10
    cooldown_bars: int = 60

    # Sizing / leverage
    base_size_fraction: float = 0.10
    """Fraction of equity per trade. Multiplied internally by sigma."""

    # Stop management
    trailing_initial_sl_bps: float = 30.0
    trailing_breakeven_bps: float = 5.0
    trailing_distance_bps: float = 5.0
    trailing_initial_lock_bps: float = 1.0
    max_hold_bars: int = 600

    # Super-state (optional)
    use_super_state: bool = True
    super_state_n_archetypes: int = 12
    super_state_window_bars: int = 60
    super_state_horizon_bars: int = 60
    super_state_min_warmup_bars: int = 3600
    super_state_refit_interval_bars: int = 1800
    super_state_voter_weight: float = 1.5


def _build_voter_weights(cfg: IntuitionTraderConfig) -> dict[str, float]:
    weights: dict[str, float] = {
        "flow_imbalance": 1.0,
        "momentum": 1.0,
        "vwap": 0.7,
        "trade_rate_surge": 0.5,
    }
    if cfg.use_super_state:
        weights["super_state"] = cfg.super_state_voter_weight
    return weights


@dataclass
class IntuitionTrader:
    """Stateful trader: owns conviction, super-state, and trailing logic."""

    config: IntuitionTraderConfig = field(default_factory=IntuitionTraderConfig)

    # Internals (initialized in __post_init__)
    intuition: IntuitionEngine = field(init=False)
    super_state: SuperStateEngine | None = field(init=False, default=None)
    _trailing_cfg: TrailingStopConfig = field(init=False)
    _stop_state: TrailingStopState | None = field(init=False, default=None)
    _bars_in_position: int = field(init=False, default=0)
    _last_open_sigma: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        cfg = self.config
        self._trailing_cfg = TrailingStopConfig(
            initial_sl_bps=cfg.trailing_initial_sl_bps,
            breakeven_trigger_bps=cfg.trailing_breakeven_bps,
            trail_distance_bps=cfg.trailing_distance_bps,
            initial_lock_bps=cfg.trailing_initial_lock_bps,
        )
        intuition_cfg = IntuitionConfig(
            confirm_bars=cfg.confirm_bars,
            sigma_enter=cfg.sigma_enter,
            sigma_exit=cfg.sigma_exit,
            cooldown_bars=cfg.cooldown_bars,
            voter_weights=_build_voter_weights(cfg),
        )

        voter_list: list[VoterFn] = [
            flow_imbalance_voter,
            momentum_voter,
            vwap_voter,
            trade_rate_surge_voter,
        ]

        if cfg.use_super_state:
            self.super_state = SuperStateEngine(
                n_archetypes=cfg.super_state_n_archetypes,
                window_bars=cfg.super_state_window_bars,
                horizon_bars=cfg.super_state_horizon_bars,
                min_warmup_bars=cfg.super_state_min_warmup_bars,
                refit_interval_bars=cfg.super_state_refit_interval_bars,
            )
            voter_list.append(self._make_super_state_voter())

        self.intuition = IntuitionEngine(intuition_cfg, directional_voters=voter_list)

    def _make_super_state_voter(self) -> VoterFn:
        def voter(bars: Sequence[OneSecondBar]) -> VoterResult:
            assert self.super_state is not None
            pred = self.super_state.predict()
            if pred is None:
                return VoterResult("super_state", 0, 0.0, "warmup")
            return VoterResult(
                "super_state",
                pred.direction,
                pred.confidence,
                f"exp={pred.expected_return_bps:+.2f}bps conc={pred.concentration:.2f}",
            )

        return voter

    # --- Lifecycle hooks ----------------------------------------------------

    def reset(self) -> None:
        """Forget all state; for re-running the same trader on a fresh dataset."""
        self.intuition.reset()
        if self.super_state is not None:
            self.super_state = SuperStateEngine(
                n_archetypes=self.config.super_state_n_archetypes,
                window_bars=self.config.super_state_window_bars,
                horizon_bars=self.config.super_state_horizon_bars,
                min_warmup_bars=self.config.super_state_min_warmup_bars,
                refit_interval_bars=self.config.super_state_refit_interval_bars,
            )
        self._stop_state = None
        self._bars_in_position = 0

    # --- Per-bar step -------------------------------------------------------

    def step(
        self,
        engine: BacktestEngine,
        bar: OneSecondBar,
        recent_bars: Sequence[OneSecondBar],
    ) -> Action:
        """One bar of decision making. Updates engine state in place."""
        engine.mark_to_market(bar.close)

        # Feed super-state always (even with open position) so its library stays warm
        if self.super_state is not None:
            self.super_state.observe(recent_bars)

        # Always evaluate intuition (cheap; needed for sigma history)
        state = self.intuition.evaluate(recent_bars)

        # --- Manage open position ---
        if engine.position is not None:
            if self._stop_state is None:
                # Defensive: position open without trailing state — close it
                engine.close_position(bar.ts_bar, bar.close, "stale_no_trailing")
                self.intuition.cooldown_after_trade()
                self._bars_in_position = 0
                return Action.CLOSE

            self._bars_in_position += 1
            if self._stop_state.update(bar.close, self._trailing_cfg):
                realized_bps = self._stop_state.realized_profit_bps_if_stopped()
                reason = (
                    "trail_lock_profit"
                    if self._stop_state.breakeven_triggered and realized_bps > 0
                    else (
                        "trail_breakeven"
                        if self._stop_state.breakeven_triggered
                        else "initial_sl"
                    )
                )
                engine.close_position(bar.ts_bar, bar.close, reason)
                self.intuition.cooldown_after_trade()
                self._stop_state = None
                self._bars_in_position = 0
                return Action.CLOSE

            if self._bars_in_position >= self.config.max_hold_bars:
                engine.close_position(bar.ts_bar, bar.close, "time_exit")
                self.intuition.cooldown_after_trade()
                self._stop_state = None
                self._bars_in_position = 0
                return Action.CLOSE

            return Action.HOLD

        # --- No open position: maybe open ---
        if not state.is_convicted:
            return Action.HOLD

        side = Side.LONG if state.direction > 0 else Side.SHORT
        size = self.config.base_size_fraction * abs(state.sigma)
        size = max(self.config.base_size_fraction * 0.5, min(1.0, size))

        opened = engine.open_position(side, bar.ts_bar, bar.close, size)
        if not opened:
            return Action.HOLD

        self._stop_state = TrailingStopState.open(side, bar.close, self._trailing_cfg)
        self._bars_in_position = 0
        self._last_open_sigma = state.sigma
        return Action.OPEN_LONG if side == Side.LONG else Action.OPEN_SHORT

    def force_close(self, engine: BacktestEngine, bar: OneSecondBar, reason: str = "session_end") -> bool:
        """Flatten any open position. Returns True if a position was closed."""
        if engine.position is None:
            return False
        engine.close_position(bar.ts_bar, bar.close, reason)
        self._stop_state = None
        self._bars_in_position = 0
        return True

    @property
    def has_position(self) -> bool:
        return self._stop_state is not None

    @property
    def last_open_sigma(self) -> float:
        return self._last_open_sigma
