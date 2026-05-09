from __future__ import annotations

from app.browser.kernel_driver import KernelBrowserSession
from app.browser.kernel_runner import KernelSimulationRunner
from app.config import AppSettings
from app.models import (
    ActionExpectation,
    BrowserActionResult,
    BrowserDomSummary,
    BrowserObservation,
    ComputerAction,
    GuideStatus,
    SimulationCreateRequest,
    SimulationStatus,
    Viewport,
)
from app.services.simulation_service import SimulationService
from app.store import InMemoryStore


class FakeKernelDriver:
    def __init__(self) -> None:
        self.selected_variant = False
        self.cart_count = 0

    async def create_session(self, target_url: str) -> KernelBrowserSession:
        return KernelBrowserSession(
            session_id="kernel_browser_123",
            live_view_url="https://kernel.example/live/kernel_browser_123",
            target_url=target_url,
        )

    async def capture_observation(self, session: KernelBrowserSession) -> BrowserObservation:
        return self._observation(session.target_url)

    async def execute_action(
        self,
        session: KernelBrowserSession,
        action: ComputerAction,
        expected: ActionExpectation,
    ) -> BrowserActionResult:
        if "select" in action.reason.lower():
            self.selected_variant = True
        if "add" in action.reason.lower():
            self.cart_count = 1
        return BrowserActionResult(
            action_id=action.action_id,
            success=True,
            url=session.target_url,
            observation=self._observation(session.target_url),
            events=[],
            message="Fake Kernel driver executed action",
        )

    def _observation(self, url: str) -> BrowserObservation:
        return BrowserObservation(
            url=url,
            screenshot="data:image/png;base64,iVBORw0KGgo=",
            viewport=Viewport(width=1280, height=800),
            dom_summary=BrowserDomSummary(
                selected_variant_id="shoe_123_105_wide" if self.selected_variant else None,
                cart_count=self.cart_count,
                cart_product_ids=["shoe_123"] if self.cart_count > 0 else [],
            ),
        )


async def test_kernel_runner_reuses_deep_guidance_flow_with_managed_browser() -> None:
    local_store = InMemoryStore()
    settings = AppSettings(
        _env_file=None,
        KERNEL_API_KEY="ker-test",
        TZAFON_API_KEY="tz-test",
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_PUBLIC_STOREFRONT_URL="https://merchant.example",
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )
    simulation_service = SimulationService(local_store, settings)
    simulation = simulation_service.create_simulation(SimulationCreateRequest())

    status = await KernelSimulationRunner(settings, local_store, FakeKernelDriver()).run(simulation.simulation_id)
    updated = simulation_service.get_simulation(simulation.simulation_id)
    trace = simulation_service.trace_response(simulation.simulation_id)

    assert status == GuideStatus.DONE
    assert updated.status == SimulationStatus.COMPLETED
    assert updated.browser_environment == "kernel"
    assert updated.browser_session_id == "kernel_browser_123"
    assert updated.browser_live_view_url == "https://kernel.example/live/kernel_browser_123"
    assert len(trace.entries) >= 3
