import type { ReactElement } from "react";
import type { Cart } from "../api/types";

export function CartDrawer({ cart }: { cart: Cart }): ReactElement {
  return (
    <aside className="cart-drawer">
      <h2>Cart</h2>
      {cart.items.length === 0 ? <p>Your cart is ready for guided shopping.</p> : null}
      {cart.items.map((item) => (
        <div className="cart-item" key={`${item.product_id}-${item.variant_id}`} data-agent-cart-product-id={item.product_id}>
          <span>{item.name}</span>
          <span>{item.variant_label}</span>
          <strong>${item.price}</strong>
        </div>
      ))}
      <div className="cart-total">
        <span>Subtotal</span>
        <strong>${cart.subtotal}</strong>
      </div>
    </aside>
  );
}
