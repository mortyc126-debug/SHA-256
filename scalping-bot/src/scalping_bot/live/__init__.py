"""Live paper-trading subsystem.

Wires real-time Bybit WebSocket → rolling bar builder → live feature
pipeline → trained Distinguisher → ThresholdStrategy → PaperBroker.
"""

from scalping_bot.live.bar_builder import LiveBarBuilder, OneSecondBar
from scalping_bot.live.feature_pipeline import LiveFeatureBuilder
from scalping_bot.live.model_io import load_model, save_model
from scalping_bot.live.paper_broker import PaperBroker
from scalping_bot.live.runner import PaperTradingSession

__all__ = [
    "LiveBarBuilder",
    "LiveFeatureBuilder",
    "OneSecondBar",
    "PaperBroker",
    "PaperTradingSession",
    "load_model",
    "save_model",
]
