"""Intuition engine — accumulates voter consensus over time.

On each new bar:
  1. Run all directional voters.
  2. Compute weighted directional consensus σ ∈ [-1, +1].
  3. Add to a rolling history of recent σ values.
  4. The bot is "convicted" when σ has been consistently strong
     (same sign, magnitude > threshold) over the last `confirm_bars`.

This mimics how a discretionary trader builds confidence: not on a
single tick, but on watching the same picture form for several
seconds.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from scalping_bot.intuition.voters import (
    VoterResult,
    flow_imbalance_voter,
    momentum_voter,
    trade_rate_surge_voter,
    vol_regime_voter,
    vwap_voter,
)
from scalping_bot.live.bar_builder import OneSecondBar

VoterFn = Callable[[Sequence[OneSecondBar]], VoterResult]


@dataclass
class IntuitionConfig:
    """Knobs for the intuition engine."""

    confirm_bars: int = 5
    """Conviction must hold for this many consecutive bars before entry."""

    sigma_enter: float = 0.40
    """Minimum |σ| needed to consider entry."""

    sigma_exit: float = 0.20
    """If conviction drops below this while in position, exit."""

    cooldown_bars: int = 30
    """After a trade closes, wait this many bars before considering re-entry."""

    voter_weights: dict[str, float] = field(
        default_factory=lambda: {
            "flow_imbalance": 1.0,
            "momentum": 1.0,
            "vwap": 0.7,
            "trade_rate_surge": 0.5,
        }
    )
    """How much each directional voter contributes. Vol regime is special."""


@dataclass
class IntuitionState:
    """Snapshot of conviction at a point in time."""

    sigma: float  # signed conviction in [-1, +1]
    direction: int  # sign of σ
    confirm_count: int  # how many consecutive bars in same direction
    voter_results: list[VoterResult]
    vol_strength: float  # 0..1 multiplier from vol_regime_voter
    is_convicted: bool  # True iff confirm_count >= confirm_bars and |σ| >= enter


class IntuitionEngine:
    """Stateful conviction tracker over a stream of OneSecondBars."""

    def __init__(
        self,
        config: IntuitionConfig | None = None,
        directional_voters: Sequence[VoterFn] | None = None,
    ) -> None:
        self.config = config or IntuitionConfig()
        default: list[VoterFn] = [
            flow_imbalance_voter,
            momentum_voter,
            vwap_voter,
            trade_rate_surge_voter,
        ]
        self._voters: list[VoterFn] = list(directional_voters) if directional_voters else default
        self._sigma_history: deque[float] = deque(maxlen=200)
        self._cooldown_left: int = 0

    # --- Lifecycle ----------------------------------------------------------

    def cooldown_after_trade(self) -> None:
        """Trigger cooldown — call after closing a position."""
        self._cooldown_left = self.config.cooldown_bars

    def reset(self) -> None:
        self._sigma_history.clear()
        self._cooldown_left = 0

    # --- Per-bar evaluation -------------------------------------------------

    def evaluate(self, bars: Sequence[OneSecondBar]) -> IntuitionState:
        """Compute the current conviction state from the most recent bars."""
        # Capture cooldown state BEFORE decrement so cooldown_bars=N means
        # exactly N evaluations during which conviction is suppressed.
        in_cooldown = self._cooldown_left > 0
        if in_cooldown:
            self._cooldown_left -= 1

        results: list[VoterResult] = [voter(bars) for voter in self._voters]
        vol_result = vol_regime_voter(bars)
        vol_strength = vol_result.strength

        # Weighted directional consensus
        weighted_sum = 0.0
        weight_total = 0.0
        for r in results:
            w = self.config.voter_weights.get(r.name, 1.0)
            weighted_sum += w * r.direction * r.strength
            weight_total += w
        sigma = weighted_sum / weight_total if weight_total > 0 else 0.0
        # Boost by vol regime (high vol expansion = stronger signal)
        sigma = max(-1.0, min(1.0, sigma * (1.0 + 0.5 * vol_strength)))

        self._sigma_history.append(sigma)
        direction = 1 if sigma > 0 else (-1 if sigma < 0 else 0)

        # How many recent bars share the same sign with |σ| > enter?
        confirm_count = 0
        for past_sigma in reversed(self._sigma_history):
            if direction != 0 and (past_sigma > 0) == (sigma > 0) and abs(past_sigma) >= self.config.sigma_enter:
                confirm_count += 1
            else:
                break

        is_convicted = (
            not in_cooldown
            and abs(sigma) >= self.config.sigma_enter
            and confirm_count >= self.config.confirm_bars
        )

        return IntuitionState(
            sigma=sigma,
            direction=direction,
            confirm_count=confirm_count,
            voter_results=results,
            vol_strength=vol_strength,
            is_convicted=is_convicted,
        )

    @property
    def sigma_history(self) -> tuple[float, ...]:
        return tuple(self._sigma_history)

    @property
    def cooldown_remaining(self) -> int:
        return self._cooldown_left
