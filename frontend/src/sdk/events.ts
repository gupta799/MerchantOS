import type { MerchantEventCreate } from "./messages";
import { backendBaseUrl } from "../api/http";

export type ProductId = string;
export type VariantId = string;

export async function emitMerchantEvent(sessionId: string, event: MerchantEventCreate): Promise<void> {
  await fetch(`${backendBaseUrl()}/api/sessions/${sessionId}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event)
  });
}
