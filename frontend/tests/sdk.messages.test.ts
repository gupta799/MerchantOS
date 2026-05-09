import { describe, expect, it } from "vitest";
import { parseBackendMessage } from "../src/sdk/messages";

describe("parseBackendMessage", () => {
  it("parses assistant updates", () => {
    const parsed = parseBackendMessage(
      JSON.stringify({ type: "assistant_update", session_id: "sess_123", message: "Ready" })
    );
    expect(parsed.type).toBe("assistant_update");
  });
});

