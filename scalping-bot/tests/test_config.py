"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from scalping_bot.config.settings import Settings, get_settings


class TestSettingsDefaults:
    def test_default_env_is_testnet(self) -> None:
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.env == "testnet"

    def test_default_symbol(self) -> None:
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.symbol == "BTCUSDT"

    def test_starting_capital_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Settings(starting_capital_usd=-1, _env_file=None)  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            Settings(starting_capital_usd=0, _env_file=None)  # type: ignore[call-arg]

    def test_log_level_limited(self) -> None:
        with pytest.raises(ValidationError):
            Settings(log_level="SILLY", _env_file=None)  # type: ignore[call-arg]

    def test_env_limited_to_testnet_mainnet(self) -> None:
        with pytest.raises(ValidationError):
            Settings(env="demo", _env_file=None)  # type: ignore[call-arg]


class TestSettingsFromEnv:
    def test_overrides_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SCALPING_BOT_SYMBOL", "ETHUSDT")
        monkeypatch.setenv("SCALPING_BOT_STARTING_CAPITAL_USD", "500")
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.symbol == "ETHUSDT"
        assert s.starting_capital_usd == 500.0

    def test_secret_fields_are_optional(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SCALPING_BOT_BYBIT_API_KEY", raising=False)
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.bybit_api_key is None
        assert s.bybit_api_secret is None


class TestEnsureDirs:
    def test_creates_missing_directories(self, tmp_path: Path) -> None:
        s = Settings(
            data_dir=tmp_path / "data",
            log_dir=tmp_path / "logs",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert not (tmp_path / "data").exists()
        s.ensure_dirs()
        assert (tmp_path / "data").is_dir()
        assert (tmp_path / "logs").is_dir()


class TestCachedAccessor:
    def test_get_settings_returns_singleton(self) -> None:
        # Clear cache so this test is independent
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
