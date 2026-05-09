from __future__ import annotations

from pydantic import BaseModel

from app.ids import ProductId, SessionId, VariantId
from app.models import RelationshipPrompt, SessionResponse


class VisualGuidancePlan(BaseModel):
    session_id: SessionId
    product_id: ProductId
    variant_id: VariantId
    goal: str
    assistant_message: str
    relationship_prompt: RelationshipPrompt


class DeepAgentPlanRequest(BaseModel):
    session_id: SessionId
    session: SessionResponse

    def prompt_text(self) -> str:
        return (
            "Create a merchant-owned visual guidance plan for this shopping session.\n"
            f"Session id: {self.session_id}\n"
            f"Customer goal: {self.session.intent_goal}\n"
            f"Recommended products: {self.session.recommended_products}\n"
            "Use tools to inspect merchant-owned session, catalog, and cart state.\n"
            "Choose the product and variant to guide toward.\n"
            "Return the final answer in the required structured response format only.\n"
            "Fields are: session_id, product_id, variant_id, goal, assistant_message, "
            "relationship_prompt.\n"
            "Use relationship_prompt value loyalty_signup unless order updates or saved "
            "preferences are clearly more appropriate.\n"
            "The goal must be a narrow browser task and must stop before checkout or payment."
        )


class DeepAgentPlanResult(BaseModel):
    session_id: SessionId
    product_id: ProductId
    variant_id: VariantId
    goal: str
    assistant_message: str
    relationship_prompt: RelationshipPrompt

    def to_visual_guidance_plan(self) -> VisualGuidancePlan:
        return VisualGuidancePlan(
            session_id=self.session_id,
            product_id=self.product_id,
            variant_id=self.variant_id,
            goal=self.goal,
            assistant_message=self.assistant_message,
            relationship_prompt=self.relationship_prompt,
        )
