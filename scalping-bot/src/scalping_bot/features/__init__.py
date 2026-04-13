"""Feature engineering — trade-based, microstructure, temporal, pairwise.

All features are polars-native. Each module exposes pure functions that
take a dataframe (or series) and return a new frame with additional
columns or a derived frame. No global state.
"""

from scalping_bot.features.builder import (
    build_feature_matrix,
    load_orderbook_snapshots_range,
    load_trades_range,
)
from scalping_bot.features.flow import (
    aggregate_trades_to_bars,
    cumulative_delta,
    flow_imbalance,
    trade_rate,
    vwap,
)
from scalping_bot.features.labels import forward_return, label_direction
from scalping_bot.features.orderbook import (
    align_to_bars,
    join_to_feature_matrix,
    snapshot_features,
)
from scalping_bot.features.pairwise import pairwise_and_features, top_k_pairs_by_correlation
from scalping_bot.features.temporal import hour_of_day_features, minute_of_hour_features
from scalping_bot.features.volatility import realized_vol, trade_price_vol

__all__ = [
    "aggregate_trades_to_bars",
    "align_to_bars",
    "build_feature_matrix",
    "cumulative_delta",
    "flow_imbalance",
    "forward_return",
    "hour_of_day_features",
    "join_to_feature_matrix",
    "label_direction",
    "load_orderbook_snapshots_range",
    "load_trades_range",
    "minute_of_hour_features",
    "pairwise_and_features",
    "realized_vol",
    "snapshot_features",
    "top_k_pairs_by_correlation",
    "trade_price_vol",
    "trade_rate",
    "vwap",
]
