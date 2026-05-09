from __future__ import annotations

from app.config import AppSettings
from app.ids import ProductId, VariantId
from app.models import (
    BrowserDomSummary,
    BrowserObservation,
    ComputerAction,
    ComputerActionType,
    SimulationCreateRequest,
    SimulationStatus,
    VerificationStatus,
    Viewport,
)
from app.services.simulation_service import SimulationService
from app.services.trace_service import TraceService
from app.store import InMemoryStore


def observation(cart_count: int = 0) -> BrowserObservation:
    return BrowserObservation(
        url="http://127.0.0.1:5175/",
        screenshot="data:image/png;base64,abc123",
        viewport=Viewport(width=900, height=700),
        dom_summary=BrowserDomSummary(
            selected_variant_id=VariantId("shoe_123_105_wide"),
            cart_count=cart_count,
            cart_product_ids=[ProductId("shoe_123")] if cart_count > 0 else [],
        ),
    )


def test_simulation_service_creates_run_with_report() -> None:
    local_store = InMemoryStore()
    service = SimulationService(
        local_store,
        AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted"),
    )

    run = service.create_simulation(SimulationCreateRequest())

    assert run.simulation_id.startswith("sim_")
    assert run.session_id.startswith("sess_")
    assert run.status == SimulationStatus.CONNECTING
    assert run.report.readiness_score >= 0
    assert run.scenario.title == "Autonomous commerce readiness probe"


def test_simulation_telemetry_aggregates_trace_entries() -> None:
    local_store = InMemoryStore()
    service = SimulationService(
        local_store,
        AppSettings(AGENTREADY_HARNESS_MODE="scripted", AGENTREADY_COMPUTER_CLIENT="scripted"),
    )
    run = service.create_simulation(SimulationCreateRequest())
    trace_service = TraceService(local_store)
    trace_service.record_observation(run.session_id, observation(cart_count=0))
    trace_service.record_action(
        run.session_id,
        ComputerAction(
            type=ComputerActionType.CLICK,
            action_id="act_test",
            x=10,
            y=10,
            reason="Add StormRunner GTX to cart",
        ),
        observation(cart_count=1),
        VerificationStatus.SUCCEEDED,
        "Browser SDK executed action",
    )

    telemetry = service.telemetry_response(run.simulation_id)
    metric_values = {metric.key: metric.value for metric in telemetry.metrics}

    assert metric_values["action_success_rate"] == 100
    assert metric_values["screenshot_state_confidence"] == 95
    assert "task_completed" not in telemetry.failures
