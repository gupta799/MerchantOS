from __future__ import annotations

from collections.abc import Callable, Sequence

import httpx
import pytest
from langchain_core.runnables import Runnable
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.language_models.chat_models import LanguageModelInput
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.agents.factory import build_merchant_deep_agent
from app.agents.model_provider import build_harness_model, validate_harness_model_provider
from app.agents.tools import MerchantToolbox
from app.config import AppSettings
from app.errors import ConfigError
from app.services.cart_service import CartService
from app.services.session_service import SessionService
from app.store import InMemoryStore


class ToolBindableFakeChatModel(FakeListChatModel):
    def bind_tools(
        self,
        tools: Sequence[dict[str, object] | type | Callable[..., object] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: object,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self


def test_deepagents_factory_constructs_real_graph() -> None:
    local_store = InMemoryStore()
    session_service = SessionService(local_store)
    cart_service = CartService(local_store)
    toolbox = MerchantToolbox(session_service, cart_service)
    graph = build_merchant_deep_agent(
        AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted"),
        toolbox,
        model_override=ToolBindableFakeChatModel(responses=["{}"]),
    )
    assert hasattr(graph, "ainvoke")


def test_harness_model_provider_builds_ollama_model() -> None:
    settings = AppSettings(
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="ollama",
        AGENTREADY_HARNESS_MODEL="gemma4:e4b",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    model = build_harness_model(settings)
    assert isinstance(model, ChatOllama)


def test_harness_model_provider_builds_llamacpp_model() -> None:
    settings = AppSettings(
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="llamacpp",
        AGENTREADY_HARNESS_MODEL="gemma4-e4b-it",
        AGENTREADY_LLAMACPP_BASE_URL="http://localhost:8080/v1",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    model = build_harness_model(settings)
    assert isinstance(model, ChatOpenAI)


def test_harness_model_provider_builds_openai_model() -> None:
    settings = AppSettings(
        OPENAI_API_KEY="sk-test",
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="openai",
        AGENTREADY_HARNESS_MODEL="gpt-5.5",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    model = build_harness_model(settings)
    assert isinstance(model, ChatOpenAI)


def test_ollama_provider_reports_unreachable_server(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = AppSettings(
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="ollama",
        AGENTREADY_HARNESS_MODEL="gemma4:e4b",
        AGENTREADY_OLLAMA_BASE_URL="http://localhost:11434",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )

    def raise_connect_error(_url: str, timeout: float) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", raise_connect_error)

    with pytest.raises(ConfigError, match="Ollama harness model provider is configured"):
        validate_harness_model_provider(settings)


def test_llamacpp_provider_reports_unreachable_server(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = AppSettings(
        AGENTREADY_HARNESS_MODE="deepagents",
        AGENTREADY_HARNESS_MODEL_PROVIDER="llamacpp",
        AGENTREADY_HARNESS_MODEL="gemma4-e4b-it",
        AGENTREADY_LLAMACPP_BASE_URL="http://localhost:8080/v1",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )

    def raise_connect_error(_url: str, timeout: float) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", raise_connect_error)

    with pytest.raises(ConfigError, match="llama.cpp harness model provider is configured"):
        validate_harness_model_provider(settings)
