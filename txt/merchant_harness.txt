from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from app.agents.factory import build_merchant_deep_agent
from app.agents.model_provider import validate_harness_model_provider
from app.agents.plans import DeepAgentPlanRequest, DeepAgentPlanResult, VisualGuidancePlan
from app.agents.result_parser import DeepAgentParseError, parse_deep_agent_plan
from app.agents.tools import MerchantToolbox
from app.config import AppSettings
from app.ids import SessionId
from app.models import RelationshipPrompt
from app.services.cart_service import CartService
from app.services.session_service import SessionService


class MerchantHarnessProtocol(Protocol):
    async def plan_visual_guidance(self, session_id: SessionId) -> VisualGuidancePlan:
        ...


class ScriptedMerchantHarness(MerchantHarnessProtocol):
    def __init__(self, session_service: SessionService) -> None:
        self._session_service = session_service

    async def plan_visual_guidance(self, session_id: SessionId) -> VisualGuidancePlan:
        session = self._session_service.get_session_response(session_id)
        product = session.recommended_products[0]
        return VisualGuidancePlan(
            session_id=session_id,
            product_id=product.id,
            variant_id=product.variant_id,
            goal=(
                f"Select the recommended variant for {product.name}, add it to cart, "
                "and stop before checkout or payment."
            ),
            assistant_message=(
                f"I can help add {product.name} to your cart while keeping you on the merchant site."
            ),
            relationship_prompt=RelationshipPrompt.LOYALTY_SIGNUP,
        )


class DeepAgentsMerchantHarness(MerchantHarnessProtocol):
    def __init__(
        self,
        session_service: SessionService,
        graph: CompiledStateGraph,
    ) -> None:
        self._session_service = session_service
        self._graph = graph

    async def plan_visual_guidance(self, session_id: SessionId) -> VisualGuidancePlan:
        session = self._session_service.get_session_response(session_id)
        request = DeepAgentPlanRequest(session_id=session_id, session=session)
        output = await self._graph.ainvoke({"messages": [HumanMessage(content=request.prompt_text())]})
        try:
            result = parse_deep_agent_plan(cast(Mapping[str, object], output))
        except DeepAgentParseError:
            return self._fallback_plan(session_id)
        return self._validated_plan(session_id, result)

    def _validated_plan(self, session_id: SessionId, result: DeepAgentPlanResult) -> VisualGuidancePlan:
        session = self._session_service.get_session_response(session_id)
        matching_products = [product for product in session.products if product.id == result.product_id]
        matching_variants = [
            variant
            for product in matching_products
            for variant in product.variants
            if variant.id == result.variant_id
        ]
        if len(matching_products) == 0 or len(matching_variants) == 0:
            product = session.recommended_products[0]
            return VisualGuidancePlan(
                session_id=session_id,
                product_id=product.id,
                variant_id=product.variant_id,
                goal=(
                    f"Select the recommended variant for {product.name}, add it to cart, "
                    "and stop before checkout or payment."
                ),
                assistant_message=f"I found {product.name}. I can add it to your cart on this merchant site.",
                relationship_prompt=RelationshipPrompt.LOYALTY_SIGNUP,
            )
        return result.to_visual_guidance_plan()

    def _fallback_plan(self, session_id: SessionId) -> VisualGuidancePlan:
        session = self._session_service.get_session_response(session_id)
        product = session.recommended_products[0]
        return VisualGuidancePlan(
            session_id=session_id,
            product_id=product.id,
            variant_id=product.variant_id,
            goal=(
                f"Select the recommended variant for {product.name}, add it to cart, "
                "and stop before checkout or payment."
            ),
            assistant_message=f"I found {product.name}. I can add it to your cart on this merchant site.",
            relationship_prompt=RelationshipPrompt.LOYALTY_SIGNUP,
        )


def build_merchant_harness(
    settings: AppSettings,
    session_service: SessionService,
    cart_service: CartService,
) -> MerchantHarnessProtocol:
    if settings.harness_mode == "scripted":
        return ScriptedMerchantHarness(session_service)
    validate_harness_model_provider(settings)
    toolbox = MerchantToolbox(session_service, cart_service)
    graph = build_merchant_deep_agent(settings, toolbox)
    return DeepAgentsMerchantHarness(session_service, graph)
