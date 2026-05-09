from __future__ import annotations

from app.agents.merchant_harness import MerchantHarnessProtocol
from app.agents.plans import VisualGuidancePlan
from app.computer.protocol import ComputerContinueRequest, ComputerStartRequest, ComputerTurn
from app.ids import SessionId
from app.models import (
    ActionExpectation,
    EventSource,
    GuideStatus,
    MerchantEventCreate,
    MerchantEventType,
    SessionStatus,
    VerificationStatus,
)
from app.policies import MerchantPolicy
from app.realtime.channel import SessionChannel
from app.services.cart_service import CartService
from app.services.computer_service import ComputerService
from app.services.event_service import EventService
from app.services.session_service import SessionService
from app.services.trace_service import TraceService


class GuideService:
    def __init__(
        self,
        channel: SessionChannel,
        harness: MerchantHarnessProtocol,
        computer_service: ComputerService,
        policy: MerchantPolicy,
        session_service: SessionService,
        cart_service: CartService,
        event_service: EventService,
        trace_service: TraceService,
    ) -> None:
        self._channel = channel
        self._harness = harness
        self._computer_service = computer_service
        self._policy = policy
        self._session_service = session_service
        self._cart_service = cart_service
        self._event_service = event_service
        self._trace_service = trace_service

    async def run_guided_session(self, session_id: SessionId) -> GuideStatus:
        self._session_service.set_status(session_id, SessionStatus.GUIDING)
        await self._channel.send_assistant_update(
            session_id,
            "Gemma-powered DeepAgents harness is inspecting merchant context and choosing the visual task.",
        )
        plan = await self._harness.plan_visual_guidance(session_id)
        await self._channel.send_assistant_update(
            session_id,
            f"{plan.assistant_message} Gemma selected this browser goal: {plan.goal}",
        )
        observation = await self._channel.request_observation(session_id)
        self._trace_service.record_observation(session_id, observation)
        await self._channel.send_assistant_update(
            session_id,
            "Sending the live storefront observation to the computer-use action model.",
        )
        turn = await self._computer_service.start(
            ComputerStartRequest(goal=plan.goal, observation=observation)
        )
        await self._channel.send_assistant_update(session_id, turn.message)
        final_status = await self._complete_turns(session_id, turn, plan)
        if final_status == GuideStatus.DONE:
            self._session_service.set_status(session_id, SessionStatus.COMPLETED)
        return final_status

    async def _complete_turns(
        self,
        session_id: SessionId,
        turn: ComputerTurn,
        plan: VisualGuidancePlan,
    ) -> GuideStatus:
        current_turn = turn
        for _ in range(6):
            if current_turn.completed or len(current_turn.actions) == 0:
                await self._channel.send_done(
                    session_id,
                    "Automated CUA simulation completed the core cart-readiness task.",
                )
                return GuideStatus.DONE
            for action in current_turn.actions:
                observation = await self._channel.request_observation(session_id)
                try:
                    self._policy.validate_action(action, observation)
                except Exception as exc:
                    trace = self._trace_service.record_action(
                        session_id,
                        action,
                        observation,
                        VerificationStatus.BLOCKED,
                        str(exc),
                    )
                    await self._channel.send_trace_update(session_id, trace)
                    await self._channel.send_error(session_id, str(exc))
                    return GuideStatus.ERROR
                expected = ActionExpectation(
                    expected_state_change="cart_or_variant_state_changes",
                    product_id=plan.product_id,
                    variant_id=plan.variant_id,
                )
                result = await self._channel.execute_action(session_id, action, expected)
                self._store_result_events(session_id, result.events)
                if result.observation.dom_summary.cart_count > 0:
                    self._cart_service.add_item(session_id, plan.product_id, plan.variant_id)
                trace = self._trace_service.record_action(
                    session_id,
                    action,
                    result.observation,
                    VerificationStatus.SUCCEEDED if result.success else VerificationStatus.FAILED,
                    result.message or "Browser SDK executed action",
                )
                await self._channel.send_trace_update(session_id, trace)
                if current_turn.call_id is None:
                    await self._channel.send_done(session_id, "Automated CUA simulation complete.")
                    return GuideStatus.DONE
                current_turn = await self._computer_service.continue_turn(
                    ComputerContinueRequest(
                        previous_response_id=current_turn.response_id,
                        call_id=current_turn.call_id,
                        observation=result.observation,
                    )
                )
                await self._channel.send_assistant_update(session_id, current_turn.message)
        await self._channel.send_error(session_id, "Guide reached the maximum step count.")
        return GuideStatus.ERROR

    def _store_result_events(self, session_id: SessionId, events: list[MerchantEventCreate]) -> None:
        for event in events:
            normalized = event.model_copy(update={"source": EventSource.MERCHANT_SDK})
            self._event_service.store_event(session_id, normalized)
        if len(events) == 0:
            self._event_service.store_event(
                session_id,
                MerchantEventCreate(
                    type=MerchantEventType.ASSISTANT_OPENED,
                    source=EventSource.MERCHANT_HARNESS,
                    message="Computer-use step completed",
                ),
            )
