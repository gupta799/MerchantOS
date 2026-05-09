from __future__ import annotations

from app.ids import ProductId, VariantId
from app.models import Product, ProductVariant


def demo_catalog() -> list[Product]:
    return [
        Product(
            id=ProductId("shoe_123"),
            name="StormRunner GTX",
            price=139,
            description="Waterproof trail running shoe with grippy lugs and wide-fit support.",
            waterproof=True,
            delivery_promise="Arrives by Friday",
            variants=[
                ProductVariant(
                    id=VariantId("shoe_123_105_wide"),
                    label="10.5 Wide",
                    size="10.5",
                    fit="wide",
                    in_stock=True,
                ),
                ProductVariant(
                    id=VariantId("shoe_123_105_regular"),
                    label="10.5 Regular",
                    size="10.5",
                    fit="regular",
                    in_stock=True,
                ),
            ],
        ),
        Product(
            id=ProductId("shoe_456"),
            name="RidgeLite Flow",
            price=119,
            description="Lightweight trail shoe for dry conditions and fast daily runs.",
            waterproof=False,
            delivery_promise="Arrives next week",
            variants=[
                ProductVariant(
                    id=VariantId("shoe_456_105_wide"),
                    label="10.5 Wide",
                    size="10.5",
                    fit="wide",
                    in_stock=True,
                )
            ],
        ),
    ]

