"""Live feature pipeline: rolling window of bars → polars frame matching
the schema produced by `features.builder.build_feature_matrix`.

Strategy: keep last N bars in memory (a deque). On each new bar, append,
re-run the same feature transforms used in training. This is wasteful
(O(window) per bar) but for our cadence (1 bar/sec, window ≤ 600) it
takes < 5ms in polars.

If we need more speed later, switch to truly incremental rolling
statistics (Welford for std, etc.) — but only after profiling proves it
matters.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

import polars as pl

from scalping_bot.features.flow import (
    cumulative_delta,
    flow_imbalance,
    trade_rate,
    vwap,
)
from scalping_bot.features.temporal import hour_of_day_features, minute_of_hour_features
from scalping_bot.features.volatility import realized_vol, trade_price_vol
from scalping_bot.live.bar_builder import OneSecondBar


@dataclass
class LiveFeatureBuilder:
    """Rolling feature builder over the last `window_bars` bars.

    Default windows match `features.builder.build_feature_matrix` so a
    model trained offline expects the same feature vector live.
    """

    window_bars: int = 600  # 10 minutes at 1s
    rv_windows: tuple[int, ...] = (60, 300)
    vwap_windows: tuple[int, ...] = (30, 300)
    cum_delta_windows: tuple[int, ...] = (30, 300)

    _bars: deque[OneSecondBar] | None = None

    def __post_init__(self) -> None:
        self._bars = deque(maxlen=self.window_bars)

    def add_bar(self, bar: OneSecondBar) -> None:
        assert self._bars is not None
        self._bars.append(bar)

    @property
    def n_bars(self) -> int:
        assert self._bars is not None
        return len(self._bars)

    @property
    def warmed_up(self) -> bool:
        """True iff we have enough bars for all rolling windows."""
        max_window = max(
            (max(self.rv_windows), max(self.vwap_windows), max(self.cum_delta_windows))
        )
        return self.n_bars >= max_window + 1

    def build_features(self) -> pl.DataFrame:
        """Materialize the rolling window into a polars feature frame.

        Returns an empty frame if we haven't warmed up yet. Otherwise the
        last row of this frame is the live feature vector for the current
        bar.
        """
        assert self._bars is not None
        if not self.warmed_up:
            return pl.DataFrame()

        bars_list: Iterable[OneSecondBar] = self._bars
        bars = pl.DataFrame(
            {
                "ts_bar": [b.ts_bar for b in bars_list],
                "open": [b.open for b in bars_list],
                "high": [b.high for b in bars_list],
                "low": [b.low for b in bars_list],
                "close": [b.close for b in bars_list],
                "vwap": [b.vwap for b in bars_list],
                "volume": [b.volume for b in bars_list],
                "buy_volume": [b.buy_volume for b in bars_list],
                "sell_volume": [b.sell_volume for b in bars_list],
                "trade_count": [b.trade_count for b in bars_list],
            }
        )

        bars = flow_imbalance(bars)
        bars = trade_rate(bars)
        for w in self.rv_windows:
            bars = realized_vol(bars, window_bars=w)
        for w in self.vwap_windows:
            bars = vwap(bars, window_bars=w)
        for w in self.cum_delta_windows:
            bars = cumulative_delta(bars, window_bars=w)
        bars = trade_price_vol(bars, window_bars=max(self.rv_windows))
        bars = hour_of_day_features(bars)
        bars = minute_of_hour_features(bars)

        return bars

    def latest_feature_row(self) -> pl.DataFrame:
        """Return just the last row of the feature frame (one row, all cols)."""
        feat = self.build_features()
        if feat.is_empty():
            return feat
        return feat.tail(1)
