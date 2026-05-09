from __future__ import annotations

import base64
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field

from app.config import AppSettings
from app.errors import BrowserEnvironmentError, ConfigError
from app.ids import ProductId, SessionId, VariantId
from app.models import (
    ActionExpectation,
    BrowserActionResult,
    BrowserDomSummary,
    BrowserObservation,
    ComputerAction,
    ComputerActionType,
    DomActionSummary,
    MerchantEventCreate,
    MerchantEventType,
    Viewport,
)


class KernelBrowserSession(BaseModel):
    session_id: str
    live_view_url: str | None
    target_url: str


class KernelBrowserDriverProtocol(Protocol):
    async def create_session(self, target_url: str) -> KernelBrowserSession:
        ...

    async def capture_observation(self, session: KernelBrowserSession) -> BrowserObservation:
        ...

    async def execute_action(
        self,
        session: KernelBrowserSession,
        action: ComputerAction,
        expected: ActionExpectation,
    ) -> BrowserActionResult:
        ...


class KernelViewportRequest(BaseModel):
    width: int
    height: int
    refresh_rate: int = 60


class KernelCreateBrowserRequest(BaseModel):
    headless: Literal[False] = False
    stealth: Literal[True] = True
    timeout_seconds: int = 600
    viewport: KernelViewportRequest


class KernelBrowserCreateResponse(BaseModel):
    session_id: str
    browser_live_view_url: str | None = None


class KernelClickMouseRequest(BaseModel):
    x: int
    y: int
    button: Literal["left"] = "left"
    click_type: Literal["click"] = "click"
    num_clicks: int = 1


class KernelMoveMouseRequest(BaseModel):
    x: int
    y: int


class KernelScrollRequest(BaseModel):
    x: int
    y: int
    delta_x: int = 0
    delta_y: int = 240


class KernelTypeTextRequest(BaseModel):
    text: str
    smooth: Literal[False] = False
    delay: int = 0


class KernelPressKeyRequest(BaseModel):
    keys: list[str]


class KernelPlaywrightExecuteRequest(BaseModel):
    code: str
    timeout_sec: int = 60


class KernelActionSnapshot(BaseModel):
    action: str
    label: str
    selector: str
    product_id: ProductId | None = None
    variant_id: VariantId | None = None
    requires_confirmation: bool = False

    def to_dom_action(self) -> DomActionSummary:
        return DomActionSummary(
            action=self.action,
            label=self.label,
            selector=self.selector,
            product_id=self.product_id,
            variant_id=self.variant_id,
            requires_confirmation=self.requires_confirmation,
        )


class KernelPageSnapshot(BaseModel):
    url: str
    actions: list[KernelActionSnapshot] = Field(default_factory=list)
    selected_variant_id: VariantId | None = None
    cart_count: int = 0
    cart_product_ids: list[ProductId] = Field(default_factory=list)

    def to_dom_summary(self) -> BrowserDomSummary:
        return BrowserDomSummary(
            visible_agent_actions=[action.to_dom_action() for action in self.actions],
            selected_variant_id=self.selected_variant_id,
            cart_count=self.cart_count,
            cart_product_ids=self.cart_product_ids,
        )


class KernelPlaywrightExecuteResponse(BaseModel):
    success: bool
    result: KernelPageSnapshot | None = None
    error: str | None = None
    stderr: str | None = None


SNAPSHOT_SCRIPT = """
const actions = await page.$$eval('[data-agent-action]', (elements) =>
  elements.map((element) => {
    const action = element.getAttribute('data-agent-action') ?? 'unknown';
    const productId = element.getAttribute('data-agent-product-id');
    const variantId = element.getAttribute('data-agent-variant-id');
    let selector = `[data-agent-action="${action}"]`;
    if (variantId !== null) {
      selector = `[data-agent-action="${action}"][data-agent-variant-id="${variantId}"]`;
    } else if (productId !== null) {
      selector = `[data-agent-action="${action}"][data-agent-product-id="${productId}"]`;
    }
    return {
      action,
      label: element.textContent?.trim() || 'Unlabeled action',
      selector,
      product_id: productId,
      variant_id: variantId,
      requires_confirmation: element.getAttribute('data-agent-requires-confirmation') === 'true'
    };
  })
);
const selected = await page.locator('[data-agent-variant-id][data-selected="true"]').first();
const selectedCount = await selected.count();
const cartProductIds = await page.$$eval('[data-agent-cart-product-id]', (elements) =>
  elements.map((element) => element.getAttribute('data-agent-cart-product-id')).filter(Boolean)
);
return {
  url: page.url(),
  actions,
  selected_variant_id: selectedCount > 0 ? await selected.getAttribute('data-agent-variant-id') : null,
  cart_count: cartProductIds.length,
  cart_product_ids: cartProductIds
};
"""


class KernelHttpBrowserDriver(KernelBrowserDriverProtocol):
    def __init__(self, settings: AppSettings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if settings.kernel_api_key is None:
            raise ConfigError("KERNEL_API_KEY is required to build the Kernel browser driver")
        self._api_key = settings.kernel_api_key.get_secret_value()
        self._base_url = settings.kernel_api_base_url.rstrip("/")
        self._viewport = Viewport(
            width=settings.kernel_viewport_width,
            height=settings.kernel_viewport_height,
            device_scale_factor=1.0,
        )
        self._transport = transport

    async def create_session(self, target_url: str) -> KernelBrowserSession:
        request = KernelCreateBrowserRequest(
            viewport=KernelViewportRequest(width=self._viewport.width, height=self._viewport.height)
        )
        async with self._client() as client:
            response = await client.post("/browsers", json=request.model_dump(mode="json"))
            self._raise_for_kernel(response, "create Kernel browser")
            browser = KernelBrowserCreateResponse.model_validate(response.json())
            await self._execute_playwright(
                client,
                browser.session_id,
                f"await page.goto({target_url!r}, {{ waitUntil: 'networkidle', timeout: 45000 }});\n{SNAPSHOT_SCRIPT}",
            )
        return KernelBrowserSession(
            session_id=browser.session_id,
            live_view_url=browser.browser_live_view_url,
            target_url=target_url,
        )

    async def capture_observation(self, session: KernelBrowserSession) -> BrowserObservation:
        async with self._client() as client:
            screenshot = await self._capture_screenshot(client, session.session_id)
            snapshot = await self._snapshot_page(client, session.session_id, session.target_url)
        return BrowserObservation(
            url=snapshot.url,
            screenshot=screenshot,
            viewport=self._viewport,
            dom_summary=snapshot.to_dom_summary(),
        )

    async def execute_action(
        self,
        session: KernelBrowserSession,
        action: ComputerAction,
        expected: ActionExpectation,
    ) -> BrowserActionResult:
        success = True
        message = "Kernel computer controls executed action"
        async with self._client() as client:
            try:
                await self._execute_kernel_action(client, session.session_id, action)
            except BrowserEnvironmentError as exc:
                success = False
                message = str(exc)
            snapshot = await self._snapshot_page(client, session.session_id, session.target_url)
            screenshot = await self._capture_screenshot(client, session.session_id)
        observation = BrowserObservation(
            url=snapshot.url,
            screenshot=screenshot,
            viewport=self._viewport,
            dom_summary=snapshot.to_dom_summary(),
        )
        return BrowserActionResult(
            action_id=action.action_id,
            success=success,
            url=snapshot.url,
            observation=observation,
            events=self._events_for_snapshot(snapshot, expected),
            message=message,
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0),
            transport=self._transport,
        )

    async def _execute_kernel_action(
        self,
        client: httpx.AsyncClient,
        kernel_session_id: str,
        action: ComputerAction,
    ) -> None:
        if action.type in {ComputerActionType.CLICK, ComputerActionType.DOUBLE_CLICK}:
            request = KernelClickMouseRequest(
                x=action.x or 0,
                y=action.y or 0,
                num_clicks=2 if action.type == ComputerActionType.DOUBLE_CLICK else 1,
            )
            response = await client.post(
                f"/browsers/{kernel_session_id}/computer/click_mouse",
                json=request.model_dump(mode="json"),
            )
            self._raise_for_kernel(response, "click Kernel browser")
            return
        if action.type == ComputerActionType.MOVE:
            request = KernelMoveMouseRequest(x=action.x or 0, y=action.y or 0)
            response = await client.post(
                f"/browsers/{kernel_session_id}/computer/move_mouse",
                json=request.model_dump(mode="json"),
            )
            self._raise_for_kernel(response, "move Kernel mouse")
            return
        if action.type == ComputerActionType.SCROLL:
            request = KernelScrollRequest(
                x=action.x or 500,
                y=action.y or 500,
                delta_x=action.scroll_x or 0,
                delta_y=action.scroll_y or 240,
            )
            response = await client.post(
                f"/browsers/{kernel_session_id}/computer/scroll",
                json=request.model_dump(mode="json"),
            )
            self._raise_for_kernel(response, "scroll Kernel browser")
            return
        if action.type == ComputerActionType.TYPE:
            request = KernelTypeTextRequest(text=action.text or "")
            response = await client.post(
                f"/browsers/{kernel_session_id}/computer/type_text",
                json=request.model_dump(mode="json"),
            )
            self._raise_for_kernel(response, "type into Kernel browser")
            return
        if action.type == ComputerActionType.KEYPRESS:
            request = KernelPressKeyRequest(keys=[action.key or "Enter"])
            response = await client.post(
                f"/browsers/{kernel_session_id}/computer/press_key",
                json=request.model_dump(mode="json"),
            )
            self._raise_for_kernel(response, "press Kernel key")
            return
        if action.type in {ComputerActionType.WAIT, ComputerActionType.SCREENSHOT}:
            return
        raise BrowserEnvironmentError(f"Kernel browser does not support action {action.type}")

    async def _snapshot_page(
        self,
        client: httpx.AsyncClient,
        kernel_session_id: str,
        fallback_url: str,
    ) -> KernelPageSnapshot:
        response = await self._execute_playwright(client, kernel_session_id, SNAPSHOT_SCRIPT)
        if response.result is None:
            return KernelPageSnapshot(url=fallback_url)
        return response.result

    async def _capture_screenshot(self, client: httpx.AsyncClient, kernel_session_id: str) -> str:
        response = await client.post(f"/browsers/{kernel_session_id}/computer/screenshot", json={})
        self._raise_for_kernel(response, "capture Kernel screenshot")
        encoded = base64.b64encode(response.content).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    async def _execute_playwright(
        self,
        client: httpx.AsyncClient,
        kernel_session_id: str,
        code: str,
    ) -> KernelPlaywrightExecuteResponse:
        request = KernelPlaywrightExecuteRequest(code=code)
        response = await client.post(
            f"/browsers/{kernel_session_id}/playwright/execute",
            json=request.model_dump(mode="json"),
        )
        self._raise_for_kernel(response, "execute Kernel Playwright code")
        result = KernelPlaywrightExecuteResponse.model_validate(response.json())
        if not result.success:
            detail = result.error or result.stderr or "unknown Kernel Playwright error"
            raise BrowserEnvironmentError(f"Kernel Playwright execution failed: {detail}")
        return result

    def _events_for_snapshot(
        self,
        snapshot: KernelPageSnapshot,
        expected: ActionExpectation,
    ) -> list[MerchantEventCreate]:
        events: list[MerchantEventCreate] = []
        if expected.variant_id is not None and snapshot.selected_variant_id == expected.variant_id:
            events.append(
                MerchantEventCreate(
                    type=MerchantEventType.VARIANT_SELECTED,
                    product_id=expected.product_id,
                    variant_id=expected.variant_id,
                )
            )
        if expected.product_id is not None and expected.product_id in snapshot.cart_product_ids:
            events.extend(
                [
                    MerchantEventCreate(
                        type=MerchantEventType.ADD_TO_CART_CLICKED,
                        product_id=expected.product_id,
                        variant_id=expected.variant_id,
                    ),
                    MerchantEventCreate(
                        type=MerchantEventType.CART_UPDATED,
                        product_id=expected.product_id,
                        variant_id=expected.variant_id,
                    ),
                ]
            )
        return events

    def _raise_for_kernel(self, response: httpx.Response, operation: str) -> None:
        if response.is_success:
            return
        raise BrowserEnvironmentError(
            f"Failed to {operation}: Kernel returned HTTP {response.status_code}"
        )


def kernel_target_url(settings: AppSettings, session_id: SessionId) -> str:
    public_storefront_url = (
        settings.kernel_public_storefront_url.strip()
        if settings.kernel_public_storefront_url is not None
        else ""
    )
    configured = (
        public_storefront_url
        if public_storefront_url != ""
        else settings.kernel_local_storefront_url.strip()
    )
    if configured == "":
        raise ConfigError(
            "AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL or AGENTREADY_PUBLIC_STOREFRONT_URL "
            "is required for Kernel browser sessions"
        )
    if "{session_id}" in configured:
        return configured.replace("{session_id}", str(session_id))
    if "/agent-session/" in configured:
        return configured
    return f"{configured.rstrip('/')}/agent-session/{session_id}"
