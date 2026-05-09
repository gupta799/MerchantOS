from __future__ import annotations

from app.config import AppSettings
from app.demo_data import demo_catalog
from app.ids import new_session_id
from app.models import (
    AgentIntentRequest,
    AgentIntentResponse,
    Cart,
    MerchantSession,
    RecommendedProduct,
    RelationshipPrompt,
    SessionStatus,
)
from app.store import InMemoryStore


class IntentService:
    def __init__(self, store: InMemoryStore, settings: AppSettings) -> None:
        self._store = store
        self._settings = settings

    def create_intent_session(self, request: AgentIntentRequest) -> AgentIntentResponse:
        recommended = self._recommend_products(request)
        session_id = new_session_id()
        session = MerchantSession(
            session_id=session_id,
            merchant_id=request.merchant_id,
            source_agent=request.source_agent,
            user_goal=request.user_goal,
            preferences=request.preferences,
            status=SessionStatus.CREATED,
            recommended_products=recommended,
            relationship_prompts=[
                RelationshipPrompt.ORDER_UPDATES,
                RelationshipPrompt.LOYALTY_SIGNUP,
                RelationshipPrompt.SAVE_PREFERENCES,
            ],
        )
        cart = Cart(session_id=session_id)
        self._store.create_session(session, cart)
        return AgentIntentResponse(
            session_id=session_id,
            handoff_url=f"{self._settings.frontend_base_url}/agent-session/{session_id}",
            summary=f"Found {len(recommended)} merchant-owned recommendations.",
        )

    def _recommend_products(self, request: AgentIntentRequest) -> list[RecommendedProduct]:
        products = demo_catalog()
        matches: list[RecommendedProduct] = []
        for product in products:
            if product.price > request.preferences.budget_max:
                continue
            if "waterproof" in request.user_goal.lower() and not product.waterproof:
                continue
            matching_variants = [
                variant
                for variant in product.variants
                if variant.size == request.preferences.size
                and variant.fit == request.preferences.fit
                and variant.in_stock
            ]
            if len(matching_variants) == 0:
                continue
            matches.append(
                RecommendedProduct(
                    id=product.id,
                    name=product.name,
                    price=product.price,
                    reason=f"Matches {request.preferences.size} {request.preferences.fit}, under budget, {product.delivery_promise.lower()}.",
                    variant_id=matching_variants[0].id,
                )
            )
        if len(matches) > 0:
            return matches
        first_product = products[0]
        return [
            RecommendedProduct(
                id=first_product.id,
                name=first_product.name,
                price=first_product.price,
                reason="Best available match in the merchant catalog.",
                variant_id=first_product.variants[0].id,
            )
        ]

