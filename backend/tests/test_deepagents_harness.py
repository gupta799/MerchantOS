from __future__ import annotations

from collections.abc import Callable, Sequence

from langchain_core.language_models.chat_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from app.agents.factory import build_merchant_deep_agent
from app.agents.merchant_harness import DeepAgentsMerchantHarness
from app.agents.tools import MerchantToolbox
from app.config import AppSettings
from app.ids import ProductId, VariantId
from app.models import AgentIntentRequest, RelationshipPrompt
from app.services.cart_service import CartService
from app.services.intent_service import IntentService
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


async def test_deepagents_harness_returns_typed_plan() -> None:
    local_store = InMemoryStore()
    settings = AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted")
    created = IntentService(local_store, settings).create_intent_session(
        AgentIntentRequest(user_goal="Find waterproof trail running shoes under $150")
    )
    session_service = SessionService(local_store)
    cart_service = CartService(local_store)
    toolbox = MerchantToolbox(session_service, cart_service)
    graph = build_merchant_deep_agent(
        settings,
        toolbox,
        model_override=ToolBindableFakeChatModel(
            responses=[
                """
                {
                  "session_id": "%s",
                  "product_id": "shoe_123",
                  "variant_id": "shoe_123_105_wide",
                  "goal": "Select 10.5 Wide for StormRunner GTX, add it to cart, and stop before checkout or payment.",
                  "assistant_message": "I found StormRunner GTX in 10.5 Wide. I can add it to your cart on RidgeRun.",
                  "relationship_prompt": "loyalty_signup"
                }
                """
                % created.session_id
            ]
        ),
    )
    harness = DeepAgentsMerchantHarness(session_service, graph, settings)
    plan = await harness.plan_visual_guidance(created.session_id)
    assert plan.product_id == ProductId("shoe_123")
    assert plan.variant_id == VariantId("shoe_123_105_wide")
    assert plan.relationship_prompt == RelationshipPrompt.LOYALTY_SIGNUP


async def test_deepagents_harness_falls_back_when_local_model_misses_json_shape() -> None:
    local_store = InMemoryStore()
    settings = AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted")
    created = IntentService(local_store, settings).create_intent_session(
        AgentIntentRequest(user_goal="Find waterproof trail running shoes under $150")
    )
    session_service = SessionService(local_store)
    cart_service = CartService(local_store)
    toolbox = MerchantToolbox(session_service, cart_service)
    graph = build_merchant_deep_agent(
        settings,
        toolbox,
        model_override=ToolBindableFakeChatModel(
            responses=["I recommend StormRunner GTX in 10.5 Wide, then stop before checkout."]
        ),
    )
    harness = DeepAgentsMerchantHarness(session_service, graph, settings)
    plan = await harness.plan_visual_guidance(created.session_id)
    assert plan.product_id == ProductId("shoe_123")
    assert plan.variant_id == VariantId("shoe_123_105_wide")
    assert plan.relationship_prompt == RelationshipPrompt.LOYALTY_SIGNUP
