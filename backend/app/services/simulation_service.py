from __future__ import annotations

from app.config import AppSettings
from app.ids import SessionId, SimulationId, new_simulation_id
from app.models import (
    AgentReadinessReport,
    AgentIntentRequest,
    BrowserEnvironment,
    CustomerPreferences,
    McpReadinessRecommendation,
    McpReadinessResponse,
    McpRecommendationKind,
    SessionStatus,
    SimulationCreateRequest,
    SimulationListResponse,
    SimulationRun,
    SimulationScenario,
    SimulationStatus,
    SimulationTelemetryResponse,
    TelemetryExportBundle,
    TraceEntry,
    TraceResponse,
)
from app.services.intent_service import IntentService
from app.services.telemetry_service import TelemetryService
from app.store import InMemoryStore


DEFAULT_SCENARIO = SimulationScenario(
    scenario_id="autonomous_commerce_readiness",
    title="Autonomous commerce readiness probe",
    goal=(
        "Behave like a computer-use buying agent. Find a waterproof trail running shoe under "
        "$150, identify the 10.5 Wide variant, add it to cart, verify the shipping promise, "
        "look for return-policy signals, and stop before checkout or payment."
    ),
)


class SimulationService:
    def __init__(self, store: InMemoryStore, settings: AppSettings) -> None:
        self._store = store
        self._settings = settings
        self._telemetry = TelemetryService(store)

    def create_simulation(self, request: SimulationCreateRequest) -> SimulationRun:
        scenario = self._scenario_for(request.scenario_id)
        intent_response = IntentService(self._store, self._settings).create_intent_session(
            AgentIntentRequest(
                merchant_id=request.merchant_id,
                source_agent="agentready_cua_simulator",
                user_goal=scenario.goal,
                preferences=CustomerPreferences(),
            )
        )
        simulation_id = new_simulation_id()
        run = SimulationRun(
            simulation_id=simulation_id,
            session_id=intent_response.session_id,
            status=SimulationStatus.CONNECTING,
            browser_environment=BrowserEnvironment(self._settings.browser_environment),
            scenario=scenario,
            current_goal=scenario.goal,
            report=self._build_report(simulation_id, intent_response.session_id),
        )
        self._store.create_simulation(run)
        return self.get_simulation(simulation_id)

    def get_simulation(self, simulation_id: SimulationId) -> SimulationRun:
        existing = self._store.get_simulation(simulation_id)
        session = self._store.get_session(existing.session_id)
        traces = self._store.traces_for_session(existing.session_id)
        status = self._status_from_existing(existing.status, session.status, traces)
        report = self._build_report(simulation_id, existing.session_id)
        updated = existing.model_copy(update={"status": status, "report": report})
        return self._store.update_simulation(updated)

    def list_simulations(self) -> SimulationListResponse:
        simulations = [self.get_simulation(simulation.simulation_id) for simulation in self._store.list_simulations()]
        simulations.sort(key=lambda simulation: simulation.created_at, reverse=True)
        return SimulationListResponse(simulations=simulations)

    def mark_running(self, simulation_id: SimulationId) -> SimulationRun:
        existing = self._store.get_simulation(simulation_id)
        updated = existing.model_copy(update={"status": SimulationStatus.RUNNING})
        return self._store.update_simulation(updated)

    def attach_browser_session(
        self,
        simulation_id: SimulationId,
        browser_session_id: str,
        browser_live_view_url: str | None,
    ) -> SimulationRun:
        existing = self._store.get_simulation(simulation_id)
        updated = existing.model_copy(
            update={
                "browser_session_id": browser_session_id,
                "browser_live_view_url": browser_live_view_url,
                "status": SimulationStatus.RUNNING,
            }
        )
        return self._store.update_simulation(updated)

    def mark_completed(self, simulation_id: SimulationId) -> SimulationRun:
        existing = self._store.get_simulation(simulation_id)
        report = self._build_report(simulation_id, existing.session_id)
        updated = existing.model_copy(update={"status": SimulationStatus.COMPLETED, "report": report})
        return self._store.update_simulation(updated)

    def mark_failed(self, simulation_id: SimulationId, message: str) -> SimulationRun:
        existing = self._store.get_simulation(simulation_id)
        report = self._build_report(simulation_id, existing.session_id)
        failed_report = report.model_copy(update={"summary": message})
        updated = existing.model_copy(update={"status": SimulationStatus.FAILED, "report": failed_report})
        return self._store.update_simulation(updated)

    def trace_response(self, simulation_id: SimulationId) -> TraceResponse:
        simulation = self.get_simulation(simulation_id)
        return TraceResponse(
            session_id=simulation.session_id,
            entries=self._store.traces_for_session(simulation.session_id),
        )

    def telemetry_response(self, simulation_id: SimulationId) -> SimulationTelemetryResponse:
        simulation = self.get_simulation(simulation_id)
        return SimulationTelemetryResponse(
            simulation_id=simulation_id,
            metrics=simulation.report.metrics,
            failures=simulation.report.failures,
        )

    def mcp_readiness(self, simulation_id: SimulationId) -> McpReadinessResponse:
        self.get_simulation(simulation_id)
        return McpReadinessResponse(
            simulation_id=simulation_id,
            recommendations=[
                McpReadinessRecommendation(
                    name="catalog.search",
                    kind=McpRecommendationKind.TOOL,
                    priority=1,
                    description="Expose product discovery as a model-callable MCP tool so agents do not rely only on visual browsing.",
                    schema_preview_json='{"type":"object","properties":{"query":{"type":"string"},"budget_max":{"type":"number"},"attributes":{"type":"array","items":{"type":"string"}}},"required":["query"]}',
                ),
                McpReadinessRecommendation(
                    name="product://{product_id}",
                    kind=McpRecommendationKind.RESOURCE,
                    priority=2,
                    description="Expose product facts, variants, delivery promises, and policy links as stable MCP resources.",
                    schema_preview_json='{"uriTemplate":"product://{product_id}","mimeType":"application/json"}',
                ),
                McpReadinessRecommendation(
                    name="cart.prepare",
                    kind=McpRecommendationKind.TOOL,
                    priority=3,
                    description="Let agents prepare a cart with selected variants while keeping checkout and payment human-controlled.",
                    schema_preview_json='{"type":"object","properties":{"product_id":{"type":"string"},"variant_id":{"type":"string"},"quantity":{"type":"integer","minimum":1}},"required":["product_id","variant_id"]}',
                ),
            ],
        )

    def export_bundle(self, simulation_id: SimulationId) -> TelemetryExportBundle:
        simulation = self.get_simulation(simulation_id)
        session = self._store.get_session(simulation.session_id)
        trace = TraceResponse(
            session_id=simulation.session_id,
            entries=self._store.traces_for_session(simulation.session_id),
        )
        telemetry = SimulationTelemetryResponse(
            simulation_id=simulation_id,
            metrics=simulation.report.metrics,
            failures=simulation.report.failures,
        )
        return TelemetryExportBundle(
            simulation=simulation,
            session=session,
            trace=trace,
            telemetry=telemetry,
            report=simulation.report,
        )

    def _scenario_for(self, scenario_id: str) -> SimulationScenario:
        if scenario_id == DEFAULT_SCENARIO.scenario_id:
            return DEFAULT_SCENARIO
        return DEFAULT_SCENARIO.model_copy(update={"scenario_id": scenario_id})

    def _status_from_session(self, session_status: SessionStatus, traces: list[TraceEntry]) -> SimulationStatus:
        if session_status == SessionStatus.COMPLETED:
            return SimulationStatus.COMPLETED
        if session_status == SessionStatus.FAILED:
            return SimulationStatus.FAILED
        if session_status == SessionStatus.GUIDING:
            return SimulationStatus.RUNNING
        if len(traces) > 0:
            return SimulationStatus.RUNNING
        return SimulationStatus.CONNECTING

    def _status_from_existing(
        self,
        existing_status: SimulationStatus,
        session_status: SessionStatus,
        traces: list[TraceEntry],
    ) -> SimulationStatus:
        if existing_status in {SimulationStatus.COMPLETED, SimulationStatus.FAILED}:
            return existing_status
        if existing_status == SimulationStatus.RUNNING and session_status not in {
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
        }:
            return SimulationStatus.RUNNING
        return self._status_from_session(session_status, traces)

    def _build_report(self, simulation_id: SimulationId, session_id: SessionId) -> AgentReadinessReport:
        return self._telemetry.build_report(simulation_id, session_id)
