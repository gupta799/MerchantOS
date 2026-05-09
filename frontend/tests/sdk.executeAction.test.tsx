import { describe, expect, it } from "vitest";
import { executeAction } from "../src/sdk/executeAction";

describe("executeAction", () => {
  it("clicks an approved merchant element", async () => {
    const root = document.createElement("div");
    root.setAttribute("data-agent-safe-root", "true");
    const button = document.createElement("button");
    button.setAttribute("data-agent-action", "select_variant");
    button.setAttribute("data-agent-product-id", "shoe_123");
    button.setAttribute("data-agent-variant-id", "shoe_123_105_wide");
    button.textContent = "10.5 Wide";
    button.addEventListener("click", () => button.setAttribute("data-selected", "true"));
    root.appendChild(button);
    document.body.appendChild(root);
    button.getBoundingClientRect = () => ({
      x: 0,
      y: 0,
      width: 100,
      height: 40,
      top: 0,
      left: 0,
      right: 100,
      bottom: 40,
      toJSON: () => ""
    });
    document.elementFromPoint = () => button;
    const result = await executeAction(root, {
      type: "click",
      action_id: "act_1",
      x: 10,
      y: 10,
      reason: "Select 10.5 Wide"
    });
    expect(result.success).toBe(true);
    expect(button.getAttribute("data-selected")).toBe("true");
  });
});

