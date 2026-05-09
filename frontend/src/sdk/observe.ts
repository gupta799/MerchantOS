import type { BrowserDomSummary, BrowserObservation, DomActionSummary } from "./messages";
import { captureScreenshot } from "./screenshot";

function selectorFor(element: Element): string {
  const action = element.getAttribute("data-agent-action");
  const productId = element.getAttribute("data-agent-product-id");
  const variantId = element.getAttribute("data-agent-variant-id");
  if (action !== null && variantId !== null) {
    return `[data-agent-action="${action}"][data-agent-variant-id="${variantId}"]`;
  }
  if (action !== null && productId !== null) {
    return `[data-agent-action="${action}"][data-agent-product-id="${productId}"]`;
  }
  if (action !== null) {
    return `[data-agent-action="${action}"]`;
  }
  return "[data-agent-action]";
}

export function collectDomSummary(root: HTMLElement): BrowserDomSummary {
  const visibleAgentActions: DomActionSummary[] = Array.from(root.querySelectorAll("[data-agent-action]")).map((element) => ({
    action: element.getAttribute("data-agent-action") ?? "unknown",
    label: element.textContent?.trim() ?? "Unlabeled action",
    selector: selectorFor(element),
    product_id: element.getAttribute("data-agent-product-id"),
    variant_id: element.getAttribute("data-agent-variant-id"),
    requires_confirmation: element.getAttribute("data-agent-requires-confirmation") === "true"
  }));
  const selected = root.querySelector("[data-agent-variant-id][data-selected='true']");
  const cartItems = Array.from(root.querySelectorAll("[data-agent-cart-product-id]")).map((element) => element.getAttribute("data-agent-cart-product-id") ?? "");
  return {
    visible_agent_actions: visibleAgentActions,
    selected_variant_id: selected?.getAttribute("data-agent-variant-id") ?? null,
    cart_count: cartItems.filter(Boolean).length,
    cart_product_ids: cartItems.filter(Boolean)
  };
}

export async function observeBrowser(root: HTMLElement): Promise<BrowserObservation> {
  return {
    url: window.location.href,
    screenshot: await captureScreenshot(root),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      device_scale_factor: window.devicePixelRatio
    },
    dom_summary: collectDomSummary(root)
  };
}

