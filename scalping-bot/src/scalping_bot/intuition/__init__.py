"""Intuition engine — adaptive, training-free trade decisions.

Core idea (rooted in SuperBit methodology §55-58 σ-self-tuning):
The bot looks at the *current* market state across multiple
microstructure indicators. Each indicator votes for a direction with
a strength in [0, 1]. Votes accumulate into a conviction σ ∈ [-1, +1].
The bot enters a trade only when σ has been consistently strong for
several consecutive bars — building "confidence" the way a human
trader does watching the screen.

No historical training. Statistics are rolling, computed on the most
recent bars only. The model has no opinion about yesterday because
yesterday's microstructure regime is gone.
"""

from scalping_bot.intuition.engine import IntuitionConfig, IntuitionEngine
from scalping_bot.intuition.voters import (
    VoterResult,
    flow_imbalance_voter,
    momentum_voter,
    vol_regime_voter,
    vwap_voter,
)

__all__ = [
    "IntuitionConfig",
    "IntuitionEngine",
    "VoterResult",
    "flow_imbalance_voter",
    "momentum_voter",
    "vol_regime_voter",
    "vwap_voter",
]
