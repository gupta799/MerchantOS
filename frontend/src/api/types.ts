export type SessionStatus = "created" | "active" | "guiding" | "completed" | "failed";
export type SimulationStatus = "created" | "connecting" | "running" | "completed" | "failed";
export type FailureLabel =
  | "no_visible_action"
  | "no_op_click"
  | "loop_detected"
  | "ambiguous_selector"
  | "missing_structured_data"
  | "missing_agent_action"
  | "unsafe_action_blocked"
  | "task_completed"
  | "task_failed";
export type RelationshipPrompt = "order_updates" | "loyalty_signup" | "save_preferences";
export type HarnessMode = "scripted" | "deepagents";
export type HarnessModelProvider = "llamacpp" | "ollama" | "openai";
export type ComputerClientMode = "scripted" | "openai" | "tzafon";
export type GuideStatus =
  | "idle"
  | "waiting_for_browser"
  | "running"
  | "needs_confirmation"
  | "done"
  | "error";

export type CustomerPreferences = {
  category: string;
  budget_max: number;
  delivery_by: string;
  size: string;
  fit: string;
};

export type AgentIntentRequest = {
  merchant_id: string;
  source_agent: string;
  user_goal: string;
  preferences: CustomerPreferences;
};

export type AgentIntentResponse = {
  session_id: string;
  handoff_url: string;
  summary: string;
};

export type SimulationCreateRequest = {
  merchant_id: string;
  scenario_id: string;
};

export type SimulationScenario = {
  scenario_id: string;
  title: string;
  goal: string;
};

export type TelemetryMetric = {
  key: string;
  label: string;
  value: number;
  unit: string;
  description: string;
};

export type AgentReadinessReport = {
  simulation_id: string;
  readiness_score: number;
  summary: string;
  metrics: TelemetryMetric[];
  failures: FailureLabel[];
  recommendations: string[];
};

export type SimulationRun = {
  simulation_id: string;
  session_id: string;
  status: SimulationStatus;
  scenario: SimulationScenario;
  current_goal: string;
  report: AgentReadinessReport;
  created_at: string;
  updated_at: string;
};

export type SimulationTelemetryResponse = {
  simulation_id: string;
  metrics: TelemetryMetric[];
  failures: FailureLabel[];
};

export type McpRecommendationKind = "tool" | "resource" | "schema";

export type McpReadinessRecommendation = {
  name: string;
  kind: McpRecommendationKind;
  priority: number;
  description: string;
  schema_preview_json: string;
};

export type McpReadinessResponse = {
  simulation_id: string;
  recommendations: McpReadinessRecommendation[];
};

export type GuideStartResponse = {
  status: GuideStatus;
  message: string;
};

export type ProductVariant = {
  id: string;
  label: string;
  size: string;
  fit: string;
  in_stock: boolean;
};

export type Product = {
  id: string;
  name: string;
  price: number;
  description: string;
  waterproof: boolean;
  delivery_promise: string;
  variants: ProductVariant[];
};

export type RecommendedProduct = {
  id: string;
  name: string;
  price: number;
  reason: string;
  variant_id: string;
};

export type CartItem = {
  product_id: string;
  variant_id: string;
  name: string;
  variant_label: string;
  price: number;
  quantity: number;
};

export type Cart = {
  session_id: string;
  items: CartItem[];
  subtotal: number;
};

export type ConsentState = {
  order_updates: boolean;
  loyalty_signup: boolean;
  save_preferences: boolean;
};

export type SessionResponse = {
  session_id: string;
  merchant_id: string;
  source_agent: string;
  intent_goal: string;
  preferences: CustomerPreferences;
  status: SessionStatus;
  recommended_products: RecommendedProduct[];
  products: Product[];
  cart: Cart;
  relationship_prompts: RelationshipPrompt[];
  consent: ConsentState;
  assistant_message: string;
};

export type TraceEntry = {
  trace_id: string;
  verification: {
    status: string;
    message: string;
  };
  action?: {
    type: string;
    reason: string;
  } | null;
};

export type TraceResponse = {
  session_id: string;
  entries: TraceEntry[];
};

export type RuntimeResponse = {
  harness_mode: HarnessMode;
  harness_model_provider: HarnessModelProvider;
  harness_model: string;
  computer_client_mode: ComputerClientMode;
  computer_model: string;
  demo_mode: boolean;
};
