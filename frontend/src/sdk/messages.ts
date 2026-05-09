import type { ProductId, VariantId } from "./events";

export type Viewport = {
  width: number;
  height: number;
  device_scale_factor: number;
};

export type DomActionSummary = {
  action: string;
  label: string;
  selector: string;
  product_id: ProductId | null;
  variant_id: VariantId | null;
  requires_confirmation: boolean;
};

export type BrowserDomSummary = {
  visible_agent_actions: DomActionSummary[];
  selected_variant_id: VariantId | null;
  cart_count: number;
  cart_product_ids: ProductId[];
};

export type BrowserObservation = {
  url: string;
  screenshot: string;
  viewport: Viewport;
  dom_summary: BrowserDomSummary;
};

export type MerchantEventCreate = {
  type:
    | "guided_session_opened"
    | "simulation_opened"
    | "simulation_started"
    | "assistant_opened"
    | "guide_allowed"
    | "product_viewed"
    | "variant_selected"
    | "add_to_cart_clicked"
    | "cart_updated"
    | "loyalty_prompt_seen"
    | "loyalty_accepted";
  source: "merchant_sdk" | "merchant_harness" | "external_agent";
  product_id?: ProductId | null;
  variant_id?: VariantId | null;
  message?: string | null;
};

export type ComputerAction =
  | { type: "click"; action_id: string; x: number; y: number; reason: string }
  | { type: "double_click"; action_id: string; x: number; y: number; reason: string }
  | { type: "scroll"; action_id: string; x?: number | null; y?: number | null; scroll_x?: number | null; scroll_y?: number | null; reason: string }
  | { type: "type"; action_id: string; text: string; reason: string }
  | { type: "wait"; action_id: string; reason: string }
  | { type: "keypress"; action_id: string; key: string; reason: string }
  | { type: "move"; action_id: string; x: number; y: number; reason: string }
  | { type: "drag"; action_id: string; x: number; y: number; reason: string }
  | { type: "screenshot"; action_id: string; reason: string };

export type ActionExpectation = {
  expected_state_change: string;
  product_id: ProductId | null;
  variant_id: VariantId | null;
};

export type BrowserActionResult = {
  action_id: string;
  success: boolean;
  url: string;
  observation: BrowserObservation;
  events: MerchantEventCreate[];
  message: string | null;
};

export type GuideReadyMessage = {
  type: "guide_ready";
  session_id: string;
  observation: BrowserObservation;
};

export type ObservationMessage = {
  type: "observation";
  session_id: string;
  observation: BrowserObservation;
};

export type ActionResultMessage = {
  type: "action_result";
  session_id: string;
  result: BrowserActionResult;
};

export type BrowserToBackendMessage = GuideReadyMessage | ObservationMessage | ActionResultMessage;

export type RequestObservationMessage = {
  type: "request_observation";
  session_id: string;
};

export type ExecuteActionMessage = {
  type: "execute_action";
  session_id: string;
  action_id: string;
  action: ComputerAction;
  expected: ActionExpectation;
};

export type AssistantUpdateMessage = {
  type: "assistant_update";
  session_id: string;
  message: string;
};

export type TraceUpdateMessage = {
  type: "trace_update";
  session_id: string;
  trace: {
    trace_id: string;
    verification: { status: string; message: string };
    action?: ComputerAction | null;
  };
};

export type GuideDoneMessage = {
  type: "guide_done";
  session_id: string;
  message: string;
};

export type GuideErrorMessage = {
  type: "guide_error";
  session_id: string;
  message: string;
};

export type ConfirmationRequestMessage = {
  type: "confirmation_request";
  session_id: string;
  message: string;
};

export type BackendToBrowserMessage =
  | RequestObservationMessage
  | ExecuteActionMessage
  | AssistantUpdateMessage
  | TraceUpdateMessage
  | GuideDoneMessage
  | GuideErrorMessage
  | ConfirmationRequestMessage;

export function parseBackendMessage(payload: string): BackendToBrowserMessage {
  const parsed = JSON.parse(payload) as BackendToBrowserMessage;
  return parsed;
}
