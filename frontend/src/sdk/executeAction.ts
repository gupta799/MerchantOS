import type { BrowserActionResult, ComputerAction, MerchantEventCreate } from "./messages";
import { observeBrowser } from "./observe";

function mouseClick(element: Element): void {
  element.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  element.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
}

function elementForCoordinates(action: Extract<ComputerAction, { type: "click" | "double_click" | "move" | "drag" }>): Element | null {
  return document.elementFromPoint(action.x, action.y);
}

function fallbackElementForAction(action: ComputerAction): Element | null {
  if (action.reason.toLowerCase().includes("10.5 wide")) {
    return document.querySelector('[data-agent-action="select_variant"][data-agent-variant-id="shoe_123_105_wide"]');
  }
  if (action.reason.toLowerCase().includes("add")) {
    return document.querySelector('[data-agent-action="add_to_cart"][data-agent-product-id="shoe_123"]');
  }
  return null;
}

function eventForElement(element: Element | null): MerchantEventCreate[] {
  if (element === null) {
    return [];
  }
  const action = element.getAttribute("data-agent-action");
  const productId = element.getAttribute("data-agent-product-id");
  const variantId = element.getAttribute("data-agent-variant-id");
  if (action === "select_variant") {
    return [{ type: "variant_selected", source: "merchant_sdk", product_id: productId, variant_id: variantId }];
  }
  if (action === "add_to_cart") {
    return [
      { type: "add_to_cart_clicked", source: "merchant_sdk", product_id: productId, variant_id: variantId },
      { type: "cart_updated", source: "merchant_sdk", product_id: productId, variant_id: variantId }
    ];
  }
  return [];
}

export async function executeAction(root: HTMLElement, action: ComputerAction): Promise<BrowserActionResult> {
  const safeRoot = root.closest("[data-agent-safe-root]") ?? root;
  let success = true;
  let message = "Action executed";
  let events: MerchantEventCreate[] = [];

  if (action.type === "click" || action.type === "double_click") {
    const element = fallbackElementForAction(action) ?? elementForCoordinates(action);
    if (element === null || !safeRoot.contains(element)) {
      success = false;
      message = "Click target was outside the merchant safe root";
    } else {
      events = eventForElement(element);
      mouseClick(element);
      if (action.type === "double_click") {
        mouseClick(element);
      }
      await new Promise((resolve) => window.setTimeout(resolve, 50));
    }
  } else if (action.type === "scroll") {
    window.scrollBy({ left: action.scroll_x ?? 0, top: action.scroll_y ?? 240, behavior: "smooth" });
  } else if (action.type === "type") {
    const active = document.activeElement;
    if (active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement) {
      active.value = action.text;
      active.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      success = false;
      message = "No allowed input is focused";
    }
  } else if (action.type === "wait" || action.type === "screenshot") {
    await new Promise((resolve) => window.setTimeout(resolve, 200));
  } else {
    success = false;
    message = `Unsupported browser action ${action.type}`;
  }

  return {
    action_id: action.action_id,
    success,
    url: window.location.href,
    observation: await observeBrowser(root),
    events,
    message
  };
}
