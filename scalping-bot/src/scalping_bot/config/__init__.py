"""Configuration subsystem. Env-based settings via pydantic-settings."""

from scalping_bot.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
