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
from app.ids import ProductId, SessionId, VariantId
from app.models import HarnessTrace, RelationshipPrompt, VerificationStatus
from app.services.cart_service import CartService
from app.services.session_service import SessionService
from app.services.trace_service import TraceService


class MerchantHarnessProtocol(Protocol):
    async def plan_visual_guidance(self, session_id: SessionId) -> VisualGuidancePlan:
        ...


class ScriptedMerchantHarness(MerchantHarnessProtocol):
    def __init__(self, session_service: SessionService, trace_service: TraceService | None = None) -> None:
        self._session_service = session_service
        self._trace_service = trace_service

    async def plan_visual_guidance(self, session_id: SessionId) -> VisualGuidancePlan:
        session = self._session_service.get_session_response(session_id)
        product = session.recommended_products[0]
        plan = VisualGuidancePlan(
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
        if self._trace_service is not None:
            self._trace_service.record_harness_trace(
                session_id,
                HarnessTrace(
                    phase="scripted_plan",
                    provider="scripted",
                    model="scripted",
                    message="Scripted harness produced deterministic visual guidance plan.",
                    product_id=plan.product_id,
                    variant_id=plan.variant_id,
                    goal=plan.goal,
                    assistant_message=plan.assistant_message,
                    relationship_prompt=plan.relationship_prompt,
                ),
                VerificationStatus.SUCCEEDED,
                "Scripted harness plan selected",
            )
        return plan


class DeepAgentsMerchantHarness(MerchantHarnessProtocol):
    def __init__(
        self,
        session_service: SessionService,
        graph: CompiledStateGraph,
        settings: AppSettings,
        trace_service: TraceService | None = None,
    ) -> None:
        self._session_service = session_service
        self._graph = graph
        self._settings = settings
        self._trace_service = trace_service

    async def plan_visual_guidance(self, session_id: SessionId) -> VisualGuidancePlan:
        session = self._session_service.get_session_response(session_id)
        request = DeepAgentPlanRequest(session_id=session_id, session=session)
        prompt_text = request.prompt_text()
        self._record_harness_trace(
            session_id,
            phase="deepagents_prompt",
            message="DeepAgents/Gemma planning prompt created.",
            status=VerificationStatus.PENDING,
            verification_message="Gemma harness prompt prepared",
            prompt_text=prompt_text,
        )
        output = await self._graph.ainvoke({"messages": [HumanMessage(content=prompt_text)]})
        raw_output_text = self._summarize_deep_agent_output(cast(Mapping[str, object], output))
        self._record_harness_trace(
            session_id,
            phase="deepagents_raw_output",
            message="DeepAgents/Gemma returned a raw planning response.",
            status=VerificationStatus.SUCCEEDED,
            verification_message="Gemma harness returned raw output",
            raw_output_text=raw_output_text,
        )
        try:
            result = parse_deep_agent_plan(cast(Mapping[str, object], output))
        except DeepAgentParseError as exc:
            plan = self._fallback_plan(session_id)
            self._record_plan_trace(
                session_id,
                "deepagents_fallback",
                f"DeepAgents/Gemma response could not be parsed, so the harness used a typed fallback: {exc}",
                plan,
                VerificationStatus.FAILED,
                "Gemma output parse failed; fallback plan used",
            )
            return plan
        plan = self._validated_plan(session_id, result)
        self._record_plan_trace(
            session_id,
            "deepagents_plan",
            "DeepAgents/Gemma produced a typed merchant visual guidance plan.",
            plan,
            VerificationStatus.SUCCEEDED,
            "Gemma harness plan selected",
        )
        return plan

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

    def _record_plan_trace(
        self,
        session_id: SessionId,
        phase: str,
        message: str,
        plan: VisualGuidancePlan,
        status: VerificationStatus,
        verification_message: str,
    ) -> None:
        self._record_harness_trace(
            session_id,
            phase=phase,
            message=message,
            status=status,
            verification_message=verification_message,
            product_id=plan.product_id,
            variant_id=plan.variant_id,
            goal=plan.goal,
            assistant_message=plan.assistant_message,
            relationship_prompt=plan.relationship_prompt,
        )

    def _record_harness_trace(
        self,
        session_id: SessionId,
        phase: str,
        message: str,
        status: VerificationStatus,
        verification_message: str,
        prompt_text: str | None = None,
        raw_output_text: str | None = None,
        product_id: ProductId | None = None,
        variant_id: VariantId | None = None,
        goal: str | None = None,
        assistant_message: str | None = None,
        relationship_prompt: RelationshipPrompt | None = None,
    ) -> None:
        if self._trace_service is None:
            return
        self._trace_service.record_harness_trace(
            session_id,
            HarnessTrace(
                phase=phase,
                provider=self._settings.harness_model_provider,
                model=self._settings.harness_model,
                message=message,
                prompt_text=prompt_text,
                raw_output_text=raw_output_text,
                product_id=product_id,
                variant_id=variant_id,
                goal=goal,
                assistant_message=assistant_message,
                relationship_prompt=relationship_prompt,
            ),
            status,
            verification_message,
        )

    def _summarize_deep_agent_output(self, output: Mapping[str, object]) -> str:
        if "messages" not in output:
            return repr(output)[:4000]
        messages = output["messages"]
        if not isinstance(messages, list):
            return repr(output)[:4000]
        chunks: list[str] = []
        for message in messages[-4:]:
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip() != "":
                chunks.append(content.strip())
        if len(chunks) == 0:
            return repr(output)[:4000]
        return "\n\n---\n\n".join(chunks)[-4000:]


def build_merchant_harness(
    settings: AppSettings,
    session_service: SessionService,
    cart_service: CartService,
    trace_service: TraceService | None = None,
) -> MerchantHarnessProtocol:
    if settings.harness_mode == "scripted":
        return ScriptedMerchantHarness(session_service, trace_service)
    validate_harness_model_provider(settings)
    toolbox = MerchantToolbox(session_service, cart_service)
    graph = build_merchant_deep_agent(settings, toolbox)
    return DeepAgentsMerchantHarness(session_service, graph, settings, trace_service)
