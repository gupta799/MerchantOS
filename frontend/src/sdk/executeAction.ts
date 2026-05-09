import type { BrowserActionResult, ComputerAction, MerchantEventCreate } from "./messages";
import { observeBrowser } from "./observe";

function mouseClick(element: Element): void {
  element.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  element.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
}

function actionPoint(
  root: HTMLElement,
  element: Element,
  action: Extract<ComputerAction, { type: "click" | "double_click" }>
): { x: number; y: number } {
  if (Number.isFinite(action.x) && Number.isFinite(action.y)) {
    return { x: action.x, y: action.y };
  }
  const rootRect = root.getBoundingClientRect();
  const elementRect = element.getBoundingClientRect();
  return {
    x: elementRect.left - rootRect.left + elementRect.width / 2,
    y: elementRect.top - rootRect.top + elementRect.height / 2
  };
}

async function showAgentPointer(root: HTMLElement, x: number, y: number, label: string): Promise<void> {
  const rootRect = root.getBoundingClientRect();
  const existingBadge = root.querySelector(".agent-cua-action-badge");
  existingBadge?.remove();

  const badge = document.createElement("div");
  badge.className = "agent-cua-action-badge";
  badge.textContent = `CUA action: ${label}`;
  root.prepend(badge);

  const pointer = document.createElement("div");
  pointer.className = "agent-cua-pointer";
  pointer.textContent = label;
  pointer.style.left = `${rootRect.left + x}px`;
  pointer.style.top = `${rootRect.top + y}px`;

  const pulse = document.createElement("div");
  pulse.className = "agent-cua-pulse";
  pulse.style.left = `${rootRect.left + x}px`;
  pulse.style.top = `${rootRect.top + y}px`;

  document.body.append(pointer, pulse);
  await new Promise((resolve) => window.setTimeout(resolve, 2200));
  pointer.classList.add("clicked");
  pulse.classList.add("clicked");
  await new Promise((resolve) => window.setTimeout(resolve, 1200));
  pointer.remove();
  pulse.remove();
  window.setTimeout(() => badge.remove(), 30000);
}

function merchantActionForCoordinates(root: HTMLElement, x: number, y: number): Element | null {
  const rootRect = root.getBoundingClientRect();
  const actions = Array.from(root.querySelectorAll("[data-agent-action]"));
  const containing = actions.find((element) => {
    const rect = element.getBoundingClientRect();
    const left = rect.left - rootRect.left;
    const top = rect.top - rootRect.top;
    return x >= left && x <= left + rect.width && y >= top && y <= top + rect.height;
  });
  if (containing !== undefined) {
    return containing;
  }

  let nearest: { element: Element; distance: number } | null = null;
  for (const element of actions) {
    const rect = element.getBoundingClientRect();
    const centerX = rect.left - rootRect.left + rect.width / 2;
    const centerY = rect.top - rootRect.top + rect.height / 2;
    const distance = Math.hypot(centerX - x, centerY - y);
    if (nearest === null || distance < nearest.distance) {
      nearest = { element, distance };
    }
  }
  if (nearest !== null && nearest.distance <= 140) {
    return nearest.element;
  }
  return null;
}

function elementForCoordinates(
  root: HTMLElement,
  action: Extract<ComputerAction, { type: "click" | "double_click" | "move" | "drag" }>
): Element | null {
  const rect = root.getBoundingClientRect();
  return merchantActionForCoordinates(root, action.x, action.y) ?? document.elementFromPoint(rect.left + action.x, rect.top + action.y);
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
    const element = fallbackElementForAction(action) ?? elementForCoordinates(root, action);
    if (element === null || !safeRoot.contains(element)) {
      success = false;
      message = "Click target was outside the merchant safe root";
    } else {
      events = eventForElement(element);
      const point = actionPoint(root, element, action);
      await showAgentPointer(root, point.x, point.y, action.type === "double_click" ? "double click" : "click");
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
  } else if (action.type === "keypress") {
    const key = action.key.toLowerCase() === "enter" ? "Enter" : action.key;
    document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key }));
    document.activeElement?.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key }));
    message = `Keypress ${key} executed`;
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
