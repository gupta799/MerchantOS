import { describe, expect, it } from "vitest";
import { collectDomSummary } from "../src/sdk/observe";

describe("collectDomSummary", () => {
  it("finds data-agent actions", () => {
    const root = document.createElement("div");
    root.innerHTML = `
      <button data-agent-action="select_variant" data-agent-product-id="shoe_123" data-agent-variant-id="shoe_123_105_wide" data-selected="true">10.5 Wide</button>
      <button data-agent-action="add_to_cart" data-agent-product-id="shoe_123">Add to cart</button>
      <div data-agent-cart-product-id="shoe_123"></div>
    `;
    const summary = collectDomSummary(root);
    expect(summary.visible_agent_actions).toHaveLength(2);
    expect(summary.selected_variant_id).toBe("shoe_123_105_wide");
    expect(summary.cart_count).toBe(1);
  });
});

