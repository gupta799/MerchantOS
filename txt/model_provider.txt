from __future__ import annotations

from urllib.parse import urljoin

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.config import AppSettings
from app.errors import ConfigError


def build_harness_model(settings: AppSettings) -> BaseChatModel:
    if settings.harness_model_provider == "llamacpp":
        return ChatOpenAI(
            model=settings.harness_model,
            api_key="local",
            base_url=settings.llamacpp_base_url,
            temperature=0,
        )
    if settings.harness_model_provider == "ollama":
        return ChatOllama(
            model=settings.harness_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    if settings.openai_api_key is None:
        raise ConfigError("OPENAI_API_KEY is required to build the OpenAI harness model")
    return ChatOpenAI(
        model=_openai_model_name(settings.harness_model),
        api_key=settings.openai_api_key.get_secret_value(),
        temperature=0,
    )


def validate_harness_model_provider(settings: AppSettings) -> None:
    if settings.harness_model_provider == "llamacpp":
        _validate_endpoint(
            settings.llamacpp_base_url,
            "llama.cpp harness model provider is configured but "
            f"{settings.llamacpp_base_url} is not reachable",
        )
        return
    if settings.harness_model_provider != "ollama":
        return
    _validate_endpoint(
        settings.ollama_base_url,
        "Ollama harness model provider is configured but "
        f"{settings.ollama_base_url} is not reachable",
        path="api/tags",
    )


def _validate_endpoint(base_url: str, message: str, path: str = "models") -> None:
    endpoint = urljoin(base_url.rstrip("/") + "/", path)
    try:
        response = httpx.get(endpoint, timeout=1.5)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ConfigError(message) from exc


def _openai_model_name(model_name: str) -> str:
    if model_name.startswith("openai:"):
        return model_name.removeprefix("openai:")
    return model_name
