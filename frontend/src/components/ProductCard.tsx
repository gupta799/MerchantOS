import type { ReactElement } from "react";
import type { Product } from "../api/types";

type ProductCardProps = {
  product: Product;
  selectedVariantId: string | null;
  onSelectVariant: (variantId: string) => void;
  onAddToCart: (productId: string, variantId: string) => void;
};

export function ProductCard({
  product,
  selectedVariantId,
  onSelectVariant,
  onAddToCart
}: ProductCardProps): ReactElement {
  const selectedVariant = product.variants.find((variant) => variant.id === selectedVariantId) ?? product.variants[0];
  return (
    <article className="product-card" data-agent-product data-agent-product-id={product.id}>
      <div className={`product-image ${product.id}`} aria-hidden="true" />
      <div className="product-detail">
        <p className="eyebrow">{product.waterproof ? "Waterproof" : "Trail ready"}</p>
        <h2>{product.name}</h2>
        <p>{product.description}</p>
        <div className="product-meta">
          <span>${product.price}</span>
          <span>{product.delivery_promise}</span>
        </div>
      </div>
      <div className="variant-row">
        {product.variants.map((variant) => (
          <button
            key={variant.id}
            type="button"
            className={selectedVariantId === variant.id ? "variant selected" : "variant"}
            data-agent-action="select_variant"
            data-agent-product-id={product.id}
            data-agent-variant-id={variant.id}
            data-selected={selectedVariantId === variant.id ? "true" : "false"}
            onClick={() => onSelectVariant(variant.id)}
          >
            {variant.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="primary-action"
        data-agent-action="add_to_cart"
        data-agent-product-id={product.id}
        data-agent-variant-id={selectedVariant.id}
        data-agent-requires-confirmation="true"
        onClick={() => onAddToCart(product.id, selectedVariant.id)}
      >
        Add to cart
      </button>
    </article>
  );
}
