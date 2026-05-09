from __future__ import annotations

from app.config import AppSettings
from app.ids import SessionId, SimulationId, new_simulation_id
from app.models import (
    AgentIntentRequest,
    AgentReadinessReport,
    CustomerPreferences,
    FailureLabel,
    McpReadinessRecommendation,
    McpReadinessResponse,
    McpRecommendationKind,
    SessionStatus,
    SimulationCreateRequest,
    SimulationRun,
    SimulationScenario,
    SimulationStatus,
    SimulationTelemetryResponse,
    TelemetryMetric,
    TraceEntry,
    TraceResponse,
    VerificationStatus,
)
from app.services.intent_service import IntentService
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
        status = self._status_from_session(session.status, traces)
        report = self._build_report(simulation_id, existing.session_id)
        updated = existing.model_copy(update={"status": status, "report": report})
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

    def _build_report(self, simulation_id: SimulationId, session_id: SessionId) -> AgentReadinessReport:
        traces = self._store.traces_for_session(session_id)
        metrics = self._metrics_for(session_id, traces)
        failures = self._failures_for(session_id, traces)
        score = self._score_for(metrics, failures)
        return AgentReadinessReport(
            simulation_id=simulation_id,
            readiness_score=score,
            summary=self._summary_for(score, failures),
            metrics=metrics,
            failures=failures,
            recommendations=self._recommendations_for(failures),
        )

    def _metrics_for(self, session_id: SessionId, traces: list[TraceEntry]) -> list[TelemetryMetric]:
        action_entries = [entry for entry in traces if entry.action is not None]
        observation_entries = [entry for entry in traces if entry.observation is not None]
        successful_actions = [
            entry
            for entry in action_entries
            if entry.verification.status == VerificationStatus.SUCCEEDED
        ]
        blocked_actions = [
            entry
            for entry in action_entries
            if entry.verification.status == VerificationStatus.BLOCKED
        ]
        action_total = len(action_entries)
        action_success_rate = 100.0 if action_total == 0 else round(len(successful_actions) / action_total * 100, 1)
        cart = self._store.get_cart(session_id)
        task_completion_rate = 100.0 if len(cart.items) > 0 else 0.0
        no_op_click_count = float(
            len(
                [
                    entry
                    for entry in action_entries
                    if entry.verification.status == VerificationStatus.FAILED
                    and entry.action is not None
                    and entry.action.type == "click"
                ]
            )
        )
        loop_count = float(self._loop_count(action_entries))
        latest_observation = observation_entries[-1].observation if len(observation_entries) > 0 else None
        visible_actions = latest_observation.dom_summary.visible_agent_actions if latest_observation is not None else []
        action_names = {action.action for action in visible_actions}
        coverage = round(len(action_names.intersection({"select_variant", "add_to_cart"})) / 2 * 100, 1)
        screenshot_confidence = 0.0
        if latest_observation is not None and latest_observation.screenshot.startswith("data:image/png;base64,"):
            screenshot_confidence = 95.0
        return [
            TelemetryMetric(
                key="task_completion_rate",
                label="Task completion",
                value=task_completion_rate,
                unit="%",
                description="Whether the autonomous CUA agent reached the target cart state.",
            ),
            TelemetryMetric(
                key="action_success_rate",
                label="Action success",
                value=action_success_rate,
                unit="%",
                description="Approved actions that executed successfully in the browser SDK.",
            ),
            TelemetryMetric(
                key="no_op_click_count",
                label="No-op clicks",
                value=no_op_click_count,
                unit="count",
                description="Click actions that did not produce a verified state transition.",
            ),
            TelemetryMetric(
                key="loop_count",
                label="Loop detections",
                value=loop_count,
                unit="count",
                description="Repeated action patterns that suggest the agent is stuck.",
            ),
            TelemetryMetric(
                key="blocked_unsafe_action_count",
                label="Blocked unsafe actions",
                value=float(len(blocked_actions)),
                unit="count",
                description="Actions stopped by merchant safety policy before reaching the browser.",
            ),
            TelemetryMetric(
                key="missing_structured_affordance_count",
                label="Missing affordances",
                value=0.0 if len(visible_actions) > 0 else 1.0,
                unit="count",
                description="Screens where the harness found no explicit agent-readable actions.",
            ),
            TelemetryMetric(
                key="actions_to_completion",
                label="Actions to completion",
                value=float(action_total),
                unit="actions",
                description="Number of browser actions needed for this simulation run.",
            ),
            TelemetryMetric(
                key="dom_action_coverage",
                label="DOM action coverage",
                value=coverage,
                unit="%",
                description="Coverage of expected merchant actions exposed through data-agent attributes.",
            ),
            TelemetryMetric(
                key="screenshot_state_confidence",
                label="Screenshot confidence",
                value=screenshot_confidence,
                unit="%",
                description="Whether screenshots were captured for replay and state verification.",
            ),
        ]

    def _loop_count(self, action_entries: list[TraceEntry]) -> int:
        repeated = 0
        previous_signature = ""
        streak = 0
        for entry in action_entries:
            if entry.action is None:
                continue
            signature = f"{entry.action.type}:{entry.action.reason}"
            if signature == previous_signature:
                streak += 1
            else:
                streak = 1
                previous_signature = signature
            if streak >= 3:
                repeated += 1
        return repeated

    def _failures_for(self, session_id: SessionId, traces: list[TraceEntry]) -> list[FailureLabel]:
        metrics = {metric.key: metric.value for metric in self._metrics_for(session_id, traces)}
        labels: list[FailureLabel] = []
        if metrics["missing_structured_affordance_count"] > 0:
            labels.extend([FailureLabel.NO_VISIBLE_ACTION, FailureLabel.MISSING_AGENT_ACTION])
        if metrics["no_op_click_count"] > 0:
            labels.append(FailureLabel.NO_OP_CLICK)
        if metrics["loop_count"] > 0:
            labels.append(FailureLabel.LOOP_DETECTED)
        if metrics["blocked_unsafe_action_count"] > 0:
            labels.append(FailureLabel.UNSAFE_ACTION_BLOCKED)
        if metrics["task_completion_rate"] == 100:
            labels.append(FailureLabel.TASK_COMPLETED)
        elif len(traces) >= 6:
            labels.append(FailureLabel.TASK_FAILED)
        return labels

    def _score_for(self, metrics: list[TelemetryMetric], failures: list[FailureLabel]) -> int:
        metric_values = {metric.key: metric.value for metric in metrics}
        base_score = (
            metric_values["task_completion_rate"] * 0.32
            + metric_values["action_success_rate"] * 0.22
            + metric_values["dom_action_coverage"] * 0.22
            + metric_values["screenshot_state_confidence"] * 0.14
            + (100 - min(metric_values["blocked_unsafe_action_count"] * 25, 100)) * 0.10
        )
        penalty = 8 * len([label for label in failures if label not in {FailureLabel.TASK_COMPLETED}])
        return max(0, min(100, round(base_score - penalty)))

    def _summary_for(self, score: int, failures: list[FailureLabel]) -> str:
        if FailureLabel.TASK_COMPLETED in failures:
            return "The autonomous CUA simulation completed the core cart task and produced replayable telemetry."
        if score >= 70:
            return "The site exposes useful agent affordances, but the simulation still found reliability gaps."
        return "The site needs stronger agent-readable affordances, state confirmation, and MCP/tool surfaces."

    def _recommendations_for(self, failures: list[FailureLabel]) -> list[str]:
        recommendations = [
            "Expose product search, product facts, and cart preparation as MCP tools/resources.",
            "Keep checkout and payment behind explicit human confirmation.",
            "Retain data-agent attributes for key buttons so computer-use actions can be validated.",
        ]
        if FailureLabel.NO_VISIBLE_ACTION in failures:
            recommendations.insert(0, "Add explicit data-agent-action attributes to primary commerce controls.")
        if FailureLabel.LOOP_DETECTED in failures:
            recommendations.insert(0, "Add clearer state transitions after clicks so agents can stop retrying.")
        if FailureLabel.NO_OP_CLICK in failures:
            recommendations.insert(0, "Add visual or DOM state confirmation after each important interaction.")
        return recommendations
