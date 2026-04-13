"""Thin wrapper around pybit's public linear WebSocket.

Public streams (trades, orderbook, tickers) do not require API credentials.
Bybit `linear` channel covers USDT perpetual futures including BTCUSDT.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pybit.unified_trading import WebSocket

MessageCallback = Callable[[dict[str, Any]], None]


class BybitPublicWS:
    """Subscribe-and-route wrapper over `pybit.unified_trading.WebSocket`.

    pybit manages the underlying thread, reconnection and heartbeat. We only
    route messages to our own callbacks and present a simple lifecycle.
    """

    def __init__(
        self,
        symbol: str,
        depth: int = 50,
        testnet: bool = False,
    ) -> None:
        self._symbol = symbol
        self._depth = depth
        self._testnet = testnet
        self._ws: WebSocket | None = None
        self._on_trade: MessageCallback | None = None
        self._on_orderbook: MessageCallback | None = None
        self._on_ticker: MessageCallback | None = None

    # --- Lifecycle ----------------------------------------------------------

    def start(
        self,
        on_trade: MessageCallback | None = None,
        on_orderbook: MessageCallback | None = None,
        on_ticker: MessageCallback | None = None,
    ) -> None:
        """Open the connection and subscribe to all configured streams."""
        if self._ws is not None:
            raise RuntimeError("already started")

        self._on_trade = on_trade
        self._on_orderbook = on_orderbook
        self._on_ticker = on_ticker

        self._ws = WebSocket(testnet=self._testnet, channel_type="linear")

        if on_trade is not None:
            self._ws.trade_stream(symbol=self._symbol, callback=self._route_trade)
        if on_orderbook is not None:
            self._ws.orderbook_stream(
                depth=self._depth,
                symbol=self._symbol,
                callback=self._route_orderbook,
            )
        if on_ticker is not None:
            self._ws.ticker_stream(symbol=self._symbol, callback=self._route_ticker)

    def stop(self) -> None:
        """Close the WebSocket. Safe to call multiple times."""
        if self._ws is None:
            return
        # pybit 5.x exposes `exit()`; older versions `stop()`. Try both.
        ws = self._ws
        self._ws = None
        stop_fn = getattr(ws, "exit", None) or getattr(ws, "stop", None)
        if callable(stop_fn):
            stop_fn()

    # --- Routing ------------------------------------------------------------

    def _route_trade(self, msg: dict[str, Any]) -> None:
        if self._on_trade is not None:
            self._on_trade(msg)

    def _route_orderbook(self, msg: dict[str, Any]) -> None:
        if self._on_orderbook is not None:
            self._on_orderbook(msg)

    def _route_ticker(self, msg: dict[str, Any]) -> None:
        if self._on_ticker is not None:
            self._on_ticker(msg)
