from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.merchant_harness import ScriptedMerchantHarness
from app.computer.scripted_computer import ScriptedComputerClient
from app.config import AppSettings
from app.ids import ProductId, SessionId, VariantId
from app.models import (
    ActionExpectation,
    BrowserActionResult,
    BrowserDomSummary,
    BrowserObservation,
    ComputerAction,
    EventSource,
    GuideStatus,
    MerchantEventCreate,
    MerchantEventType,
    TraceEntry,
    Viewport,
)
from app.policies import MerchantPolicy
from app.services.cart_service import CartService
from app.services.computer_service import ComputerService
from app.services.event_service import EventService
from app.services.guide_service import GuideService
from app.services.intent_service import IntentService
from app.services.session_service import SessionService
from app.services.trace_service import TraceService
from app.store import InMemoryStore


def base_observation(selected: bool, cart_count: int) -> BrowserObservation:
    return BrowserObservation(
        url="http://localhost:5173/agent-session/sess_123",
        screenshot="data:image/png;base64,",
        viewport=Viewport(width=800, height=600),
        dom_summary=BrowserDomSummary(
            selected_variant_id=VariantId("shoe_123_105_wide") if selected else None,
            cart_count=cart_count,
        ),
    )


@dataclass
class FakeChannel:
    observations: list[BrowserObservation]
    messages: list[str] = field(default_factory=list)

    async def request_observation(self, session_id: SessionId) -> BrowserObservation:
        return self.observations.pop(0)

    async def execute_action(
        self,
        session_id: SessionId,
        action: ComputerAction,
        expected: ActionExpectation,
    ) -> BrowserActionResult:
        selected = "Select" in action.reason
        cart_count = 0 if selected else 1
        return BrowserActionResult(
            action_id=action.action_id,
            success=True,
            url="http://localhost:5173/agent-session/sess_123",
            observation=base_observation(selected=True, cart_count=cart_count),
            events=[
                MerchantEventCreate(
                    type=MerchantEventType.CART_UPDATED if cart_count > 0 else MerchantEventType.VARIANT_SELECTED,
                    source=EventSource.MERCHANT_SDK,
                    product_id=expected.product_id,
                    variant_id=expected.variant_id,
                )
            ],
            message="Fake action executed",
        )

    async def send_assistant_update(self, session_id: SessionId, message: str) -> None:
        self.messages.append(message)

    async def send_trace_update(self, session_id: SessionId, trace_entry: TraceEntry) -> None:
        self.messages.append(trace_entry.verification.message)

    async def send_done(self, session_id: SessionId, message: str) -> None:
        self.messages.append(message)

    async def send_error(self, session_id: SessionId, message: str) -> None:
        self.messages.append(message)


async def test_guide_service_runs_observation_to_trace_loop() -> None:
    local_store = InMemoryStore()
    settings = AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted")
    intent = IntentService(local_store, settings)
    created = intent.create_intent_session(user_goal_request())
    session_service = SessionService(local_store)
    cart_service = CartService(local_store)
    event_service = EventService(local_store)
    trace_service = TraceService(local_store)
    channel = FakeChannel(
        observations=[
            base_observation(selected=False, cart_count=0),
            base_observation(selected=False, cart_count=0),
            base_observation(selected=True, cart_count=0),
        ]
    )
    guide = GuideService(
        channel=channel,
        harness=ScriptedMerchantHarness(session_service),
        computer_service=ComputerService(settings, ScriptedComputerClient()),
        policy=MerchantPolicy(),
        session_service=session_service,
        cart_service=cart_service,
        event_service=event_service,
        trace_service=trace_service,
    )
    status = await guide.run_guided_session(created.session_id)
    assert status == GuideStatus.DONE
    assert cart_service.verify_contains(created.session_id, ProductId("shoe_123")) is True
    assert len(trace_service.response(created.session_id).entries) >= 2


def user_goal_request() -> "AgentIntentRequest":
    from app.models import AgentIntentRequest

    return AgentIntentRequest(user_goal="Find waterproof trail running shoes under $150")
