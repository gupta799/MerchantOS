from __future__ import annotations

from pydantic import BaseModel

from app.demo_data import demo_catalog
from app.ids import ProductId, SessionId, VariantId
from app.models import Product, ProductVariant, SessionResponse
from app.services.cart_service import CartService
from app.services.session_service import SessionService


class CatalogPayload(BaseModel):
    products: list[Product]


class VisualGoalPayload(BaseModel):
    session_id: SessionId
    product_id: ProductId
    variant_id: VariantId
    goal: str


class MerchantToolbox:
    def __init__(self, session_service: SessionService, cart_service: CartService) -> None:
        self._session_service = session_service
        self._cart_service = cart_service

    def get_session_context(self, session_id: str) -> str:
        """Return merchant-owned session context for a guided shopping session."""
        session = self._session_service.get_session_response(SessionId(session_id))
        return session.model_dump_json()

    def search_catalog(self, session_id: str) -> str:
        """Return the merchant-owned catalog available to the current session."""
        self._session_service.get_session_response(SessionId(session_id))
        return CatalogPayload(products=demo_catalog()).model_dump_json()

    def get_cart_state(self, session_id: str) -> str:
        """Return the merchant-owned cart state for a guided shopping session."""
        session = self._session_service.get_session_response(SessionId(session_id))
        return session.cart.model_dump_json()

    def build_visual_guidance_goal(self, session_id: str, product_id: str, variant_id: str) -> str:
        """Build a narrow browser task for OpenAI computer use from a product and variant."""
        session = self._session_service.get_session_response(SessionId(session_id))
        product = _find_product(session, ProductId(product_id))
        variant = _find_variant(product, VariantId(variant_id))
        return VisualGoalPayload(
            session_id=SessionId(session_id),
            product_id=product.id,
            variant_id=variant.id,
            goal=(
                f"Select {variant.label} for {product.name}, add it to cart, "
                "and stop before checkout or payment."
            ),
        ).model_dump_json()

    def update_cart(self, session_id: str, product_id: str, variant_id: str) -> str:
        """Update merchant-owned cart state after a verified browser action."""
        cart = self._cart_service.add_item(
            SessionId(session_id),
            ProductId(product_id),
            VariantId(variant_id),
        )
        return cart.model_dump_json()


def _find_product(session: SessionResponse, product_id: ProductId) -> Product:
    for product in session.products:
        if product.id == product_id:
            return product
    return session.products[0]


def _find_variant(product: Product, variant_id: VariantId) -> ProductVariant:
    for variant in product.variants:
        if variant.id == variant_id:
            return variant
    return product.variants[0]
