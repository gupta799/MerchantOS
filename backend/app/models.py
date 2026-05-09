from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.ids import ActionId, EventId, MerchantId, ProductId, SessionId, SimulationId, TraceId, VariantId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStatus(StrEnum):
    CREATED = "created"
    ACTIVE = "active"
    GUIDING = "guiding"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationStatus(StrEnum):
    CREATED = "created"
    CONNECTING = "connecting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BrowserEnvironment(StrEnum):
    LOCAL_SDK = "local_sdk"
    KERNEL = "kernel"


class FailureLabel(StrEnum):
    NO_VISIBLE_ACTION = "no_visible_action"
    NO_OP_CLICK = "no_op_click"
    LOOP_DETECTED = "loop_detected"
    AMBIGUOUS_SELECTOR = "ambiguous_selector"
    MISSING_STRUCTURED_DATA = "missing_structured_data"
    MISSING_AGENT_ACTION = "missing_agent_action"
    UNSAFE_ACTION_BLOCKED = "unsafe_action_blocked"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class MerchantEventType(StrEnum):
    GUIDED_SESSION_OPENED = "guided_session_opened"
    SIMULATION_OPENED = "simulation_opened"
    SIMULATION_STARTED = "simulation_started"
    ASSISTANT_OPENED = "assistant_opened"
    GUIDE_ALLOWED = "guide_allowed"
    PRODUCT_VIEWED = "product_viewed"
    VARIANT_SELECTED = "variant_selected"
    ADD_TO_CART_CLICKED = "add_to_cart_clicked"
    CART_UPDATED = "cart_updated"
    LOYALTY_PROMPT_SEEN = "loyalty_prompt_seen"
    LOYALTY_ACCEPTED = "loyalty_accepted"


class EventSource(StrEnum):
    MERCHANT_SDK = "merchant_sdk"
    MERCHANT_HARNESS = "merchant_harness"
    EXTERNAL_AGENT = "external_agent"


class RelationshipPrompt(StrEnum):
    ORDER_UPDATES = "order_updates"
    LOYALTY_SIGNUP = "loyalty_signup"
    SAVE_PREFERENCES = "save_preferences"


class ComputerActionType(StrEnum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    SCROLL = "scroll"
    TYPE = "type"
    WAIT = "wait"
    KEYPRESS = "keypress"
    DRAG = "drag"
    MOVE = "move"
    SCREENSHOT = "screenshot"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GuideStatus(StrEnum):
    IDLE = "idle"
    WAITING_FOR_BROWSER = "waiting_for_browser"
    RUNNING = "running"
    NEEDS_CONFIRMATION = "needs_confirmation"
    DONE = "done"
    ERROR = "error"


class CustomerPreferences(BaseModel):
    category: str = "trail running shoes"
    budget_max: int = 150
    delivery_by: str = "Friday"
    size: str = "10.5"
    fit: str = "wide"


class AgentIntentRequest(BaseModel):
    merchant_id: MerchantId = Field(default=MerchantId("demo_shop"))
    source_agent: str = "chatgpt"
    user_goal: str
    preferences: CustomerPreferences = Field(default_factory=CustomerPreferences)


class AgentIntentResponse(BaseModel):
    session_id: SessionId
    handoff_url: str
    summary: str


class SimulationScenario(BaseModel):
    scenario_id: str
    title: str
    goal: str


class SimulationCreateRequest(BaseModel):
    merchant_id: MerchantId = Field(default=MerchantId("demo_shop"))
    scenario_id: str = "autonomous_commerce_readiness"


class ProductVariant(BaseModel):
    id: VariantId
    label: str
    size: str
    fit: str
    in_stock: bool


class Product(BaseModel):
    id: ProductId
    name: str
    price: int
    description: str
    waterproof: bool
    delivery_promise: str
    variants: list[ProductVariant]


class RecommendedProduct(BaseModel):
    id: ProductId
    name: str
    price: int
    reason: str
    variant_id: VariantId


class CartItem(BaseModel):
    product_id: ProductId
    variant_id: VariantId
    name: str
    variant_label: str
    price: int
    quantity: int = 1


class Cart(BaseModel):
    session_id: SessionId
    items: list[CartItem] = Field(default_factory=list)
    subtotal: int = 0


class ConsentState(BaseModel):
    order_updates: bool = False
    loyalty_signup: bool = False
    save_preferences: bool = False


class MerchantSession(BaseModel):
    session_id: SessionId
    merchant_id: MerchantId
    source_agent: str
    user_goal: str
    preferences: CustomerPreferences
    status: SessionStatus
    recommended_products: list[RecommendedProduct]
    relationship_prompts: list[RelationshipPrompt]
    consent: ConsentState = Field(default_factory=ConsentState)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionResponse(BaseModel):
    session_id: SessionId
    merchant_id: MerchantId
    source_agent: str
    intent_goal: str
    preferences: CustomerPreferences
    status: SessionStatus
    recommended_products: list[RecommendedProduct]
    products: list[Product]
    cart: Cart
    relationship_prompts: list[RelationshipPrompt]
    consent: ConsentState
    assistant_message: str


class MerchantEventCreate(BaseModel):
    type: MerchantEventType
    source: EventSource = EventSource.MERCHANT_SDK
    product_id: ProductId | None = None
    variant_id: VariantId | None = None
    message: str | None = None


class MerchantEvent(BaseModel):
    event_id: EventId
    session_id: SessionId
    type: MerchantEventType
    source: EventSource
    product_id: ProductId | None = None
    variant_id: VariantId | None = None
    message: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class MerchantEventAck(BaseModel):
    event_id: EventId
    stored: Literal[True] = True


class DomActionSummary(BaseModel):
    action: str
    label: str
    selector: str
    product_id: ProductId | None = None
    variant_id: VariantId | None = None
    requires_confirmation: bool = False


class BrowserDomSummary(BaseModel):
    visible_agent_actions: list[DomActionSummary] = Field(default_factory=list)
    selected_variant_id: VariantId | None = None
    cart_count: int = 0
    cart_product_ids: list[ProductId] = Field(default_factory=list)


class Viewport(BaseModel):
    width: int
    height: int
    device_scale_factor: float = 1.0


class BrowserObservation(BaseModel):
    url: str
    screenshot: str
    viewport: Viewport
    dom_summary: BrowserDomSummary


class ComputerAction(BaseModel):
    type: ComputerActionType
    action_id: ActionId
    x: int | None = None
    y: int | None = None
    text: str | None = None
    scroll_x: int | None = None
    scroll_y: int | None = None
    key: str | None = None
    reason: str = "OpenAI computer action"


class ActionExpectation(BaseModel):
    expected_state_change: str
    product_id: ProductId | None = None
    variant_id: VariantId | None = None


class BrowserActionResult(BaseModel):
    action_id: ActionId
    success: bool
    url: str
    observation: BrowserObservation
    events: list[MerchantEventCreate] = Field(default_factory=list)
    message: str | None = None


class ActionVerification(BaseModel):
    status: VerificationStatus
    message: str


class TraceEntry(BaseModel):
    trace_id: TraceId
    session_id: SessionId
    action: ComputerAction | None = None
    observation: BrowserObservation | None = None
    verification: ActionVerification
    created_at: datetime = Field(default_factory=utc_now)


class TraceResponse(BaseModel):
    session_id: SessionId
    entries: list[TraceEntry]


class TelemetryMetric(BaseModel):
    key: str
    label: str
    value: float
    unit: str
    description: str


class AgentReadinessReport(BaseModel):
    simulation_id: SimulationId
    readiness_score: int
    summary: str
    metrics: list[TelemetryMetric]
    failures: list[FailureLabel]
    recommendations: list[str]


class SimulationRun(BaseModel):
    simulation_id: SimulationId
    session_id: SessionId
    status: SimulationStatus
    browser_environment: BrowserEnvironment = BrowserEnvironment.LOCAL_SDK
    browser_session_id: str | None = None
    browser_live_view_url: str | None = None
    scenario: SimulationScenario
    current_goal: str
    report: AgentReadinessReport
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SimulationListResponse(BaseModel):
    simulations: list[SimulationRun]


class SimulationTelemetryResponse(BaseModel):
    simulation_id: SimulationId
    metrics: list[TelemetryMetric]
    failures: list[FailureLabel]


class McpRecommendationKind(StrEnum):
    TOOL = "tool"
    RESOURCE = "resource"
    SCHEMA = "schema"


class McpReadinessRecommendation(BaseModel):
    name: str
    kind: McpRecommendationKind
    priority: int
    description: str
    schema_preview_json: str


class McpReadinessResponse(BaseModel):
    simulation_id: SimulationId
    recommendations: list[McpReadinessRecommendation]


class TelemetryExportBundle(BaseModel):
    simulation: SimulationRun
    session: MerchantSession
    trace: TraceResponse
    telemetry: SimulationTelemetryResponse
    report: AgentReadinessReport


class TelemetrySummaryRequest(BaseModel):
    simulation_id: SimulationId


class TelemetrySummaryResponse(BaseModel):
    simulation_id: SimulationId
    model: str
    markdown: str


class TelemetrySummaryAllResponse(BaseModel):
    simulation_ids: list[SimulationId]
    model: str
    markdown: str


class CustomerMessageRequest(BaseModel):
    message: str


class GuideStartResponse(BaseModel):
    status: GuideStatus
    message: str


class HealthResponse(BaseModel):
    ok: bool


class RuntimeResponse(BaseModel):
    harness_mode: Literal["scripted", "deepagents"]
    harness_model_provider: Literal["llamacpp", "ollama", "openai"]
    harness_model: str
    computer_client_mode: Literal["scripted", "openai", "tzafon"]
    computer_model: str
    browser_environment: Literal["local_sdk", "kernel"]
    demo_mode: bool
