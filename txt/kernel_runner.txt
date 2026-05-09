from __future__ import annotations

from app.agents.merchant_harness import build_merchant_harness
from app.browser.kernel_driver import (
    KernelBrowserDriverProtocol,
    KernelBrowserSession,
    KernelHttpBrowserDriver,
    kernel_target_url,
)
from app.config import AppSettings
from app.ids import SessionId, SimulationId
from app.models import ActionExpectation, BrowserActionResult, BrowserObservation, ComputerAction, GuideStatus, TraceEntry
from app.policies import merchant_policy_for_public_url
from app.services.cart_service import CartService
from app.services.computer_service import ComputerService
from app.services.event_service import EventService
from app.services.guide_service import GuideService
from app.services.session_service import SessionService
from app.services.simulation_service import SimulationService
from app.services.trace_service import TraceService
from app.store import InMemoryStore


def kernel_policy_url(settings: AppSettings) -> str | None:
    if settings.kernel_public_storefront_url is not None and settings.kernel_public_storefront_url.strip() != "":
        return settings.kernel_public_storefront_url
    return settings.kernel_local_storefront_url


class KernelBrowserChannel:
    def __init__(
        self,
        settings: AppSettings,
        simulation_id: SimulationId,
        simulation_service: SimulationService,
        driver: KernelBrowserDriverProtocol,
    ) -> None:
        self._settings = settings
        self._simulation_id = simulation_id
        self._simulation_service = simulation_service
        self._driver = driver
        self._browser_session: KernelBrowserSession | None = None
        self._latest_assistant_message = ""

    async def request_observation(self, session_id: SessionId) -> BrowserObservation:
        browser_session = await self._ensure_browser_session(session_id)
        return await self._driver.capture_observation(browser_session)

    async def execute_action(
        self,
        session_id: SessionId,
        action: ComputerAction,
        expected: ActionExpectation,
    ) -> BrowserActionResult:
        browser_session = await self._ensure_browser_session(session_id)
        return await self._driver.execute_action(browser_session, action, expected)

    async def send_assistant_update(self, session_id: SessionId, message: str) -> None:
        self._latest_assistant_message = message

    async def send_trace_update(self, session_id: SessionId, trace_entry: TraceEntry) -> None:
        return None

    async def send_done(self, session_id: SessionId, message: str) -> None:
        self._latest_assistant_message = message

    async def send_error(self, session_id: SessionId, message: str) -> None:
        self._latest_assistant_message = message

    def latest_assistant_message(self) -> str:
        return self._latest_assistant_message

    async def _ensure_browser_session(self, session_id: SessionId) -> KernelBrowserSession:
        if self._browser_session is not None:
            return self._browser_session
        target_url = kernel_target_url(self._settings, session_id)
        if (
            self._settings.kernel_existing_browser_session_id is not None
            and self._settings.kernel_existing_browser_session_id.strip() != ""
        ):
            browser_session = await self._driver.connect_session(
                self._settings.kernel_existing_browser_session_id.strip(),
                target_url,
                self._settings.kernel_existing_browser_live_view_url,
            )
        else:
            browser_session = await self._driver.create_session(target_url)
        self._simulation_service.attach_browser_session(
            self._simulation_id,
            browser_session.session_id,
            browser_session.live_view_url,
        )
        self._browser_session = browser_session
        return browser_session


class KernelSimulationRunner:
    def __init__(
        self,
        settings: AppSettings,
        store: InMemoryStore,
        driver: KernelBrowserDriverProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._driver = driver if driver is not None else KernelHttpBrowserDriver(settings)

    async def run(self, simulation_id: SimulationId) -> GuideStatus:
        simulation_service = SimulationService(self._store, self._settings)
        simulation = simulation_service.mark_running(simulation_id)
        session_service = SessionService(self._store)
        cart_service = CartService(self._store)
        channel = KernelBrowserChannel(
            settings=self._settings,
            simulation_id=simulation_id,
            simulation_service=simulation_service,
            driver=self._driver,
        )
        guide_service = GuideService(
            channel=channel,
            harness=build_merchant_harness(self._settings, session_service, cart_service),
            computer_service=ComputerService(self._settings),
            policy=merchant_policy_for_public_url(kernel_policy_url(self._settings)),
            session_service=session_service,
            cart_service=cart_service,
            event_service=EventService(self._store),
            trace_service=TraceService(self._store, self._settings),
        )
        status = await guide_service.run_guided_session(simulation.session_id)
        if status == GuideStatus.DONE:
            simulation_service.mark_completed(simulation_id)
        else:
            simulation_service.mark_failed(
                simulation_id,
                channel.latest_assistant_message() or "Kernel simulation did not complete successfully",
            )
        return status
