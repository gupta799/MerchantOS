from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.browser.kernel_runner import KernelSimulationRunner
from app.config import get_settings
from app.errors import AgentReadyError
from app.ids import SessionId
from app.ids import SimulationId
from app.models import (
    AgentIntentRequest,
    AgentIntentResponse,
    CustomerMessageRequest,
    GuideStartResponse,
    GuideStatus,
    HealthResponse,
    MerchantEventAck,
    MerchantEventCreate,
    McpReadinessResponse,
    RuntimeResponse,
    SessionResponse,
    SimulationCreateRequest,
    SimulationListResponse,
    SimulationRun,
    SimulationTelemetryResponse,
    TelemetrySummaryRequest,
    TelemetrySummaryResponse,
    TelemetrySummaryAllResponse,
    TelemetryExportBundle,
    TraceResponse,
)
from app.agents.merchant_harness import build_merchant_harness
from app.policies import merchant_policy
from app.realtime.channel import session_channel
from app.services.cart_service import CartService
from app.services.computer_service import ComputerService
from app.services.event_service import EventService
from app.services.guide_service import GuideService
from app.services.intent_service import IntentService
from app.services.session_service import SessionService
from app.services.simulation_service import SimulationService
from app.services.telemetry_service import TelemetryService
from app.services.trace_service import TraceService
from app.store import store

router = APIRouter()


def _intent_service() -> IntentService:
    return IntentService(store, get_settings())


def _session_service() -> SessionService:
    return SessionService(store)


def _event_service() -> EventService:
    return EventService(store)


def _cart_service() -> CartService:
    return CartService(store)


def _trace_service() -> TraceService:
    return TraceService(store, get_settings())


def _simulation_service() -> SimulationService:
    return SimulationService(store, get_settings())


def _telemetry_service() -> TelemetryService:
    return TelemetryService(store)


def _guide_service() -> GuideService:
    settings = get_settings()
    session_service = _session_service()
    cart_service = _cart_service()
    return GuideService(
        channel=session_channel,
        harness=build_merchant_harness(settings, session_service, cart_service),
        computer_service=ComputerService(settings),
        policy=merchant_policy,
        session_service=session_service,
        cart_service=cart_service,
        event_service=_event_service(),
        trace_service=_trace_service(),
    )


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


@router.get("/api/runtime", response_model=RuntimeResponse)
async def runtime() -> RuntimeResponse:
    settings = get_settings()
    return RuntimeResponse(
        harness_mode=settings.harness_mode,
        harness_model_provider=settings.harness_model_provider,
        harness_model=settings.harness_model,
        computer_client_mode=settings.computer_client_mode,
        computer_model=(
            settings.tzafon_computer_model
            if settings.computer_client_mode == "tzafon"
            else settings.openai_computer_model
        ),
        browser_environment=settings.browser_environment,
        demo_mode=settings.harness_mode == "scripted" or settings.computer_client_mode == "scripted",
    )


@router.post("/api/agent-intent", response_model=AgentIntentResponse)
async def create_agent_intent(request: AgentIntentRequest) -> AgentIntentResponse:
    return _intent_service().create_intent_session(request)


@router.post("/api/simulations", response_model=SimulationRun)
async def create_simulation(request: SimulationCreateRequest) -> SimulationRun:
    simulation = _simulation_service().create_simulation(request)
    if get_settings().browser_environment == "kernel":
        asyncio.create_task(_run_kernel_simulation_safely(simulation.simulation_id))
    return simulation


@router.get("/api/simulations", response_model=SimulationListResponse)
async def list_simulations() -> SimulationListResponse:
    return _simulation_service().list_simulations()


@router.get("/api/simulations/{simulation_id}", response_model=SimulationRun)
async def get_simulation(simulation_id: SimulationId) -> SimulationRun:
    return _simulation_service().get_simulation(simulation_id)


@router.get("/api/simulations/{simulation_id}/trace", response_model=TraceResponse)
async def get_simulation_trace(simulation_id: SimulationId) -> TraceResponse:
    return _simulation_service().trace_response(simulation_id)


@router.get("/api/simulations/{simulation_id}/telemetry", response_model=SimulationTelemetryResponse)
async def get_simulation_telemetry(simulation_id: SimulationId) -> SimulationTelemetryResponse:
    return _simulation_service().telemetry_response(simulation_id)


@router.get("/api/simulations/{simulation_id}/mcp-readiness", response_model=McpReadinessResponse)
async def get_simulation_mcp_readiness(simulation_id: SimulationId) -> McpReadinessResponse:
    return _simulation_service().mcp_readiness(simulation_id)


@router.get("/api/simulations/{simulation_id}/export", response_model=TelemetryExportBundle)
async def export_simulation(simulation_id: SimulationId) -> TelemetryExportBundle:
    return _simulation_service().export_bundle(simulation_id)


@router.post("/api/summarize", response_model=TelemetrySummaryResponse)
async def summarize_telemetry(request: TelemetrySummaryRequest) -> TelemetrySummaryResponse:
    return _telemetry_service().summarize_simulation(request.simulation_id)


@router.post("/api/summarize-all", response_model=TelemetrySummaryAllResponse)
async def summarize_all_telemetry() -> TelemetrySummaryAllResponse:
    return _telemetry_service().summarize_all_simulations()


@router.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: SessionId) -> SessionResponse:
    return _session_service().get_session_response(session_id)


@router.post("/api/sessions/{session_id}/events", response_model=MerchantEventAck)
async def create_event(session_id: SessionId, event: MerchantEventCreate) -> MerchantEventAck:
    return _event_service().store_event(session_id, event)


@router.post("/api/sessions/{session_id}/messages", response_model=GuideStartResponse)
async def create_customer_message(session_id: SessionId, request: CustomerMessageRequest) -> GuideStartResponse:
    if not session_channel.has_connection(session_id):
        return GuideStartResponse(
            status=GuideStatus.WAITING_FOR_BROWSER,
            message="Browser SDK is not connected yet.",
        )
    try:
        guide_service = _guide_service()
    except AgentReadyError as exc:
        return GuideStartResponse(status=GuideStatus.ERROR, message=str(exc))
    asyncio.create_task(_run_guide_safely(guide_service, session_id))
    return GuideStartResponse(status=GuideStatus.RUNNING, message=f"Starting guide: {request.message}")


@router.get("/api/sessions/{session_id}/trace", response_model=TraceResponse)
async def get_trace(session_id: SessionId) -> TraceResponse:
    return _trace_service().response(session_id)


@router.websocket("/api/sessions/{session_id}/guide/ws")
async def guide_websocket(websocket: WebSocket, session_id: SessionId) -> None:
    await session_channel.connect(session_id, websocket)
    try:
        while True:
            payload = await websocket.receive_text()
            await session_channel.receive_text(session_id, payload)
    except WebSocketDisconnect:
        session_channel.disconnect(session_id)


async def _run_guide_safely(guide_service: GuideService, session_id: SessionId) -> None:
    try:
        await guide_service.run_guided_session(session_id)
    except AgentReadyError as exc:
        await session_channel.send_error(session_id, str(exc))
    except Exception as exc:
        await session_channel.send_error(session_id, f"Unexpected guide failure: {exc}")


async def _run_kernel_simulation_safely(simulation_id: SimulationId) -> None:
    settings = get_settings()
    try:
        await KernelSimulationRunner(settings, store).run(simulation_id)
    except AgentReadyError as exc:
        SimulationService(store, settings).mark_failed(simulation_id, str(exc))
    except Exception as exc:
        SimulationService(store, settings).mark_failed(
            simulation_id,
            f"Unexpected Kernel simulation failure: {exc}",
        )
