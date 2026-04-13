"""Historical data downloader for Bybit public archives.

Sources:
- Trades:    https://public.bybit.com/trading/<SYMBOL>/<SYMBOL><YYYY-MM-DD>.csv.gz
- Orderbook: https://quote-saver.bycsi.com/orderbook/linear/<SYMBOL>/<YYYY-MM-DD>_<SYMBOL>_ob200.data.zip
- Trades archive begins March 2020; orderbook archive begins May 2025.
- No authentication or API keys required.
"""

from scalping_bot.historical.converter import (
    convert_orderbook_to_parquet,
    convert_trades_to_parquet,
)
from scalping_bot.historical.downloader import (
    download_orderbook_day,
    download_trades_day,
    orderbook_url,
    trades_url,
)

__all__ = [
    "convert_orderbook_to_parquet",
    "convert_trades_to_parquet",
    "download_orderbook_day",
    "download_trades_day",
    "orderbook_url",
    "trades_url",
]
