from __future__ import annotations

from app.demo_data import demo_catalog
from app.errors import NotFoundError
from app.ids import ProductId, SessionId, VariantId
from app.models import Cart, CartItem, Product, ProductVariant
from app.store import InMemoryStore


class CartService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add_item(self, session_id: SessionId, product_id: ProductId, variant_id: VariantId) -> Cart:
        product = self._find_product(product_id)
        variant = self._find_variant(product_id, variant_id)
        cart = self._store.get_cart(session_id)
        existing = [
            item
            for item in cart.items
            if item.product_id == product_id and item.variant_id == variant_id
        ]
        if len(existing) == 0:
            updated_items = [
                *cart.items,
                CartItem(
                    product_id=product_id,
                    variant_id=variant_id,
                    name=product.name,
                    variant_label=variant.label,
                    price=product.price,
                ),
            ]
        else:
            updated_items = [
                item.model_copy(update={"quantity": item.quantity + 1})
                if item.product_id == product_id and item.variant_id == variant_id
                else item
                for item in cart.items
            ]
        updated = Cart(
            session_id=session_id,
            items=updated_items,
            subtotal=sum(item.price * item.quantity for item in updated_items),
        )
        return self._store.save_cart(updated)

    def verify_contains(self, session_id: SessionId, product_id: ProductId) -> bool:
        cart = self._store.get_cart(session_id)
        return any(item.product_id == product_id for item in cart.items)

    def _find_product(self, product_id: ProductId) -> Product:
        for product in demo_catalog():
            if product.id == product_id:
                return product
        raise NotFoundError(f"Product {product_id} was not found")

    def _find_variant(self, product_id: ProductId, variant_id: VariantId) -> ProductVariant:
        product = self._find_product(product_id)
        for variant in product.variants:
            if variant.id == variant_id:
                return variant
        raise NotFoundError(f"Variant {variant_id} was not found")
