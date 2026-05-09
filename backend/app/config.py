from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.errors import ConfigError

ComputerClientMode = Literal["scripted", "openai", "tzafon"]
HarnessMode = Literal["scripted", "deepagents"]
HarnessModelProvider = Literal["llamacpp", "ollama", "openai"]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_computer_model: str = Field(default="gpt-5.5", validation_alias="OPENAI_COMPUTER_MODEL")
    tzafon_api_key: SecretStr | None = Field(default=None, validation_alias="TZAFON_API_KEY")
    tzafon_api_base_url: str = Field(default="https://api.tzafon.ai", validation_alias="TZAFON_API_BASE_URL")
    tzafon_computer_model: str = Field(
        default="tzafon.northstar-cua-fast-1.6",
        validation_alias="TZAFON_COMPUTER_MODEL",
    )
    harness_model_provider_override: HarnessModelProvider | None = Field(
        default=None,
        validation_alias="AGENTREADY_HARNESS_MODEL_PROVIDER",
    )
    harness_model_override: str | None = Field(default=None, validation_alias="AGENTREADY_HARNESS_MODEL")
    deprecated_deepagents_model: str | None = Field(default=None, validation_alias="AGENTREADY_DEEPAGENTS_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="AGENTREADY_OLLAMA_BASE_URL")
    llamacpp_base_url: str = Field(
        default="http://localhost:8080/v1",
        validation_alias="AGENTREADY_LLAMACPP_BASE_URL",
    )
    harness_mode: HarnessMode = Field(default="deepagents", validation_alias="AGENTREADY_HARNESS_MODE")
    computer_client_mode: ComputerClientMode = Field(default="scripted", validation_alias="AGENTREADY_COMPUTER_CLIENT")
    frontend_base_url: str = Field(default="http://127.0.0.1:5174", validation_alias="FRONTEND_BASE_URL")
    backend_base_url: str = Field(default="http://localhost:8000", validation_alias="BACKEND_BASE_URL")
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @property
    def harness_model_provider(self) -> HarnessModelProvider:
        if self.harness_model_provider_override is not None:
            return self.harness_model_provider_override
        if self.deprecated_deepagents_model is not None:
            return "openai"
        return "llamacpp"

    @property
    def harness_model(self) -> str:
        if self.harness_model_override is not None and self.harness_model_override.strip() != "":
            return self.harness_model_override
        if self.deprecated_deepagents_model is not None and self.deprecated_deepagents_model.strip() != "":
            return self.deprecated_deepagents_model
        if self.harness_model_provider == "openai":
            return "gpt-5.5"
        if self.harness_model_provider == "llamacpp":
            return "gemma4-e4b-it"
        return "gemma4:e4b"

    def validate_runtime(self) -> None:
        if self.computer_client_mode == "openai" and self.openai_api_key is None:
            raise ConfigError("OPENAI_API_KEY is required when AGENTREADY_COMPUTER_CLIENT=openai")
        if self.computer_client_mode == "tzafon" and self.tzafon_api_key is None:
            raise ConfigError("TZAFON_API_KEY is required when AGENTREADY_COMPUTER_CLIENT=tzafon")
        if (
            self.harness_mode == "deepagents"
            and self.harness_model_provider == "openai"
            and self.openai_api_key is None
        ):
            raise ConfigError(
                "OPENAI_API_KEY is required when AGENTREADY_HARNESS_MODEL_PROVIDER=openai"
            )


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.validate_runtime()
    return settings
