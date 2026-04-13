"""Runtime-configurable settings. Loaded from environment / .env file.

Risk limits are NOT here — they live in scalping_bot.risk.limits as
hardcoded constants. This module is for things that legitimately vary
between environments: API keys, endpoint URLs, symbol names, log levels.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings.

    Load order: .env file → real environment → explicit overrides.
    All keys are prefixed with `SCALPING_BOT_` to avoid collisions.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SCALPING_BOT_",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Environment ---
    env: Literal["testnet", "mainnet"] = Field(
        default="testnet",
        description="Testnet until we have earned the right to mainnet.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- Bybit credentials (Phase 1+; optional in Phase 0) ---
    bybit_api_key: SecretStr | None = None
    bybit_api_secret: SecretStr | None = None

    # --- Trading parameters ---
    symbol: str = "BTCUSDT"
    starting_capital_usd: float = Field(default=100.0, gt=0)

    # --- Paths ---
    data_dir: Path = Path("./data")
    log_dir: Path = Path("./logs")

    def ensure_dirs(self) -> None:
        """Create data and log directories if they don't exist yet."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Re-import the module to force reload."""
    return Settings()
