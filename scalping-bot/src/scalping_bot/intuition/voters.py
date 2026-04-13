"""Microstructure voters for the intuition engine.

Each voter looks at a rolling window of recent bars and returns a
VoterResult: a direction in {-1, 0, +1} and a strength in [0, 1].

All voters are pure functions on a list of recent OneSecondBars; no
shared state, no training data, no model weights. They are deliberately
simple — the goal is "what does an experienced trader notice in the
current tape?", not "what does a model say".
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from scalping_bot.live.bar_builder import OneSecondBar


@dataclass(frozen=True)
class VoterResult:
    """One voter's read on the current market state."""

    name: str
    direction: int  # -1 short, 0 neutral, +1 long
    strength: float  # [0, 1]
    detail: str = ""


def _safe_mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _safe_std(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = _safe_mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return math.sqrt(var)


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# --- Individual voters ------------------------------------------------------


def flow_imbalance_voter(bars: Sequence[OneSecondBar], window: int = 30) -> VoterResult:
    """Vote based on cumulative buy vs sell volume in last `window` bars.

    Strong taker-buy dominance → bullish; strong sell → bearish.
    Strength is the magnitude of normalized imbalance.
    """
    name = "flow_imbalance"
    if len(bars) < window:
        return VoterResult(name, 0, 0.0, "warmup")
    recent = bars[-window:]
    buy = sum(b.buy_volume for b in recent)
    sell = sum(b.sell_volume for b in recent)
    total = buy + sell
    if total == 0:
        return VoterResult(name, 0, 0.0, "no_volume")
    imb = (buy - sell) / total
    direction = 1 if imb > 0.05 else (-1 if imb < -0.05 else 0)
    strength = _clip(abs(imb) * 2.0)  # 0.5 imbalance → strength 1.0
    return VoterResult(name, direction, strength, f"imb={imb:+.3f}")


def momentum_voter(bars: Sequence[OneSecondBar], short: int = 10, long: int = 60) -> VoterResult:
    """Two-window momentum — bullish only when both short AND long agree.

    Short window catches the immediate move, long window confirms it
    isn't just a single-bar spike.
    """
    name = "momentum"
    if len(bars) < long + 1:
        return VoterResult(name, 0, 0.0, "warmup")

    p_now = bars[-1].close
    p_short = bars[-short].close
    p_long = bars[-long].close
    if p_short == 0 or p_long == 0:
        return VoterResult(name, 0, 0.0, "zero_price")

    ret_short = (p_now - p_short) / p_short
    ret_long = (p_now - p_long) / p_long

    # Both must point the same way
    if ret_short > 0 and ret_long > 0:
        direction = 1
    elif ret_short < 0 and ret_long < 0:
        direction = -1
    else:
        return VoterResult(name, 0, 0.0, f"disagree s={ret_short:+.4%} l={ret_long:+.4%}")

    # Strength ~ smaller of the two normalized to ~10 bps reference
    strength = _clip(min(abs(ret_short), abs(ret_long)) / 0.001)
    return VoterResult(
        name, direction, strength, f"s={ret_short:+.4%} l={ret_long:+.4%}"
    )


def vol_regime_voter(
    bars: Sequence[OneSecondBar],
    fast: int = 30,
    slow: int = 300,
) -> VoterResult:
    """Vote on whether volatility is expanding (good for breakout entries).

    Direction is neutral (this voter alone doesn't pick a side); strength
    indicates regime. Returned as `(0, strength)` so the accumulator can
    use it as a confidence multiplier when other voters agree.
    """
    name = "vol_regime"
    if len(bars) < slow + 1:
        return VoterResult(name, 0, 0.0, "warmup")

    fast_returns = [
        (bars[-i].close - bars[-i - 1].close) / bars[-i - 1].close
        for i in range(1, fast + 1)
        if bars[-i - 1].close > 0
    ]
    slow_returns = [
        (bars[-i].close - bars[-i - 1].close) / bars[-i - 1].close
        for i in range(1, slow + 1)
        if bars[-i - 1].close > 0
    ]
    fast_vol = _safe_std(fast_returns)
    slow_vol = _safe_std(slow_returns)
    if slow_vol == 0:
        return VoterResult(name, 0, 0.0, "flat")

    ratio = fast_vol / slow_vol
    # Expanding (ratio > 1.5): high strength; contracting (ratio < 0.7): low
    if ratio > 1.5:
        strength = _clip((ratio - 1.5) / 1.5)  # ratio=3 → strength 1.0
    elif ratio < 0.7:
        strength = 0.0
    else:
        strength = 0.3
    return VoterResult(name, 0, strength, f"ratio={ratio:.2f}")


def vwap_voter(bars: Sequence[OneSecondBar], window: int = 60) -> VoterResult:
    """Where is current price relative to recent VWAP?

    Above VWAP → mild bullish bias (institutional accumulation).
    Below VWAP → mild bearish bias.
    Uses distance in bps as strength.
    """
    name = "vwap"
    if len(bars) < window:
        return VoterResult(name, 0, 0.0, "warmup")

    recent = bars[-window:]
    sum_pv = sum(b.vwap * b.volume for b in recent if b.volume > 0)
    sum_v = sum(b.volume for b in recent)
    if sum_v == 0:
        return VoterResult(name, 0, 0.0, "no_volume")

    rolling_vwap = sum_pv / sum_v
    p_now = bars[-1].close
    if rolling_vwap == 0:
        return VoterResult(name, 0, 0.0, "zero_vwap")

    delta_bps = (p_now - rolling_vwap) / rolling_vwap * 10_000.0
    direction = 1 if delta_bps > 1.0 else (-1 if delta_bps < -1.0 else 0)
    strength = _clip(abs(delta_bps) / 5.0)  # 5 bps off VWAP → strength 1.0
    return VoterResult(name, direction, strength, f"Δ={delta_bps:+.2f}bps")


def trade_rate_surge_voter(
    bars: Sequence[OneSecondBar],
    window_recent: int = 5,
    window_baseline: int = 60,
) -> VoterResult:
    """Surge in trading activity.

    Direction is the sign of recent price change (activity + direction).
    Strength is how unusual the activity is vs baseline.
    """
    name = "trade_rate_surge"
    if len(bars) < window_baseline:
        return VoterResult(name, 0, 0.0, "warmup")

    recent_rate = _safe_mean([b.trade_count for b in bars[-window_recent:]])
    baseline_rate = _safe_mean([b.trade_count for b in bars[-window_baseline:]])
    if baseline_rate == 0:
        return VoterResult(name, 0, 0.0, "no_trades")

    ratio = recent_rate / baseline_rate
    if ratio < 1.5:
        return VoterResult(name, 0, 0.0, f"ratio={ratio:.2f} (no surge)")

    p_now = bars[-1].close
    p_then = bars[-window_recent].close
    if p_then == 0:
        return VoterResult(name, 0, 0.0, "zero_price")
    direction = 1 if p_now > p_then else (-1 if p_now < p_then else 0)
    strength = _clip((ratio - 1.5) / 2.5)  # ratio=4 → strength 1.0
    return VoterResult(name, direction, strength, f"ratio={ratio:.2f}")
