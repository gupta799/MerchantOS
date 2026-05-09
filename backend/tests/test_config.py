from __future__ import annotations

import pytest

from app.config import AppSettings
from app.errors import ConfigError


def test_scripted_mode_does_not_need_openai_key() -> None:
    settings = AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted")
    settings.validate_runtime()


def test_llamacpp_harness_model_does_not_need_openai_key() -> None:
    settings = AppSettings(
        OPENAI_API_KEY=None,
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="llamacpp",
        AGENTREADY_HARNESS_MODEL="gemma4-e4b-it",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    settings.validate_runtime()
    assert settings.harness_model_provider == "llamacpp"
    assert settings.harness_model == "gemma4-e4b-it"


def test_ollama_harness_model_does_not_need_openai_key() -> None:
    settings = AppSettings(
        OPENAI_API_KEY=None,
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="ollama",
        AGENTREADY_HARNESS_MODEL="gemma4:e4b",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    settings.validate_runtime()
    assert settings.harness_model_provider == "ollama"
    assert settings.harness_model == "gemma4:e4b"


def test_openai_mode_requires_key() -> None:
    settings = AppSettings(
        OPENAI_API_KEY=None,
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="openai",
    )
    with pytest.raises(ConfigError):
        settings.validate_runtime()


def test_tzafon_computer_mode_requires_key() -> None:
    settings = AppSettings(
        TZAFON_API_KEY=None,
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="tzafon",
    )
    with pytest.raises(ConfigError):
        settings.validate_runtime()


def test_tzafon_computer_mode_accepts_key_without_openai() -> None:
    settings = AppSettings(
        OPENAI_API_KEY=None,
        TZAFON_API_KEY="tz-test",
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="tzafon",
    )
    settings.validate_runtime()


def test_kernel_browser_environment_requires_kernel_key() -> None:
    settings = AppSettings(
        KERNEL_API_KEY=None,
        TZAFON_API_KEY="tz-test",
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_PUBLIC_STOREFRONT_URL="https://merchant.example",
    )
    with pytest.raises(ConfigError):
        settings.validate_runtime()


def test_kernel_browser_environment_requires_tzafon_key() -> None:
    settings = AppSettings(
        KERNEL_API_KEY="ker-test",
        TZAFON_API_KEY=None,
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_COMPUTER_CLIENT="tzafon",
    )
    with pytest.raises(ConfigError):
        settings.validate_runtime()


def test_kernel_browser_environment_accepts_local_tunnel_target_without_public_url() -> None:
    settings = AppSettings(
        KERNEL_API_KEY="ker-test",
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_PUBLIC_STOREFRONT_URL="",
        AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL="http://localhost:5173",
        AGENTREADY_COMPUTER_CLIENT="scripted",
        AGENTREADY_HARNESS_MODE="scripted",
    )
    settings.validate_runtime()


def test_kernel_browser_environment_accepts_required_keys_without_openai() -> None:
    settings = AppSettings(
        OPENAI_API_KEY=None,
        KERNEL_API_KEY="ker-test",
        TZAFON_API_KEY="tz-test",
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_PUBLIC_STOREFRONT_URL="https://merchant.example",
        AGENTREADY_COMPUTER_CLIENT="tzafon",
        AGENTREADY_HARNESS_MODE="scripted",
    )
    settings.validate_runtime()


def test_openai_harness_model_requires_key() -> None:
    settings = AppSettings(
        OPENAI_API_KEY=None,
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="openai",
        AGENTREADY_HARNESS_MODEL="gpt-5.5",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    with pytest.raises(ConfigError):
        settings.validate_runtime()


def test_deprecated_deepagents_model_selects_openai_provider() -> None:
    settings = AppSettings(
        _env_file=None,
        OPENAI_API_KEY="sk-test",
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_DEEPAGENTS_MODEL="gpt-5.5",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    settings.validate_runtime()
    assert settings.harness_model_provider == "openai"
    assert settings.harness_model == "gpt-5.5"
