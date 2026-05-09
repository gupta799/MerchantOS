from __future__ import annotations

import httpx
from pydantic import ValidationError

from app.computer.protocol import ComputerClient, ComputerContinueRequest, ComputerStartRequest, ComputerTurn
from app.computer.tzafon_payloads import (
    TzafonActionPayload,
    TzafonComputerCallOutput,
    TzafonComputerCallOutputImage,
    TzafonComputerTool,
    TzafonInputImage,
    TzafonInputText,
    TzafonOutputItem,
    TzafonResponsesRequest,
    TzafonResponsesResponse,
    TzafonUserMessage,
)
from app.config import AppSettings
from app.errors import BrowserEnvironmentError, ConfigError, UnsupportedComputerActionError
from app.ids import ComputerCallId, ComputerResponseId, new_action_id
from app.models import BrowserObservation, ComputerAction, ComputerActionType, DomActionSummary


class TzafonComputerClient(ComputerClient):
    def __init__(
        self,
        settings: AppSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.tzafon_api_key is None:
            raise ConfigError("TZAFON_API_KEY is required to build the Tzafon computer client")
        self._api_key = settings.tzafon_api_key.get_secret_value()
        self._base_url = self._responses_base_url(settings.tzafon_api_base_url)
        self._model = settings.tzafon_computer_model
        self._transport = transport

    async def start(self, request: ComputerStartRequest) -> ComputerTurn:
        response = await self._create_initial_response(request.goal, request.observation)
        return self._turn_from_response(response, request.observation)

    async def continue_turn(self, request: ComputerContinueRequest) -> ComputerTurn:
        response = await self._create_followup_response(request.previous_response_id, request.call_id, request.observation)
        return self._turn_from_response(response, request.observation)

    async def _create_initial_response(self, goal: str, observation: BrowserObservation) -> TzafonResponsesResponse:
        payload = TzafonResponsesRequest(
            model=self._model,
            instructions=self._instructions(),
            input=[
                TzafonUserMessage(
                    content=[
                        TzafonInputText(text=self._initial_prompt(goal, observation)),
                        TzafonInputImage(image_url=observation.screenshot),
                    ]
                )
            ],
            tools=[self._computer_tool()],
        )
        return await self._post_response(payload)

    async def _create_followup_response(
        self,
        previous_response_id: ComputerResponseId,
        call_id: ComputerCallId,
        observation: BrowserObservation,
    ) -> TzafonResponsesResponse:
        payload = TzafonResponsesRequest(
            model=self._model,
            previous_response_id=str(previous_response_id),
            input=[
                TzafonComputerCallOutput(
                    call_id=str(call_id),
                    output=TzafonComputerCallOutputImage(image_url=observation.screenshot),
                )
            ],
            tools=[self._computer_tool()],
        )
        return await self._post_response(payload)

    async def _post_response(self, payload: TzafonResponsesRequest) -> TzafonResponsesResponse:
        timeout = httpx.Timeout(connect=8.0, read=45.0, write=8.0, pool=8.0)
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=timeout) as client:
                response = await client.post(
                    f"{self._base_url}/responses",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload.model_dump(exclude_none=True),
                )
        except httpx.TimeoutException as exc:
            raise BrowserEnvironmentError(
                f"Tzafon Responses API timed out at {self._base_url}/responses while waiting for Northstar."
            ) from exc
        except httpx.HTTPError as exc:
            raise BrowserEnvironmentError(
                f"Tzafon Responses API request failed at {self._base_url}/responses: "
                f"{exc.__class__.__name__}: {repr(exc)}"
            ) from exc
        if response.status_code == 401:
            raise BrowserEnvironmentError(
                "Tzafon returned 401 Unauthorized. Check TZAFON_API_KEY and Lightcone model access."
            )
        if response.status_code >= 400:
            raise BrowserEnvironmentError(f"Tzafon returned HTTP {response.status_code}: {response.text[:300]}")
        try:
            return TzafonResponsesResponse.model_validate_json(response.text)
        except ValidationError as exc:
            raise BrowserEnvironmentError(
                f"Tzafon returned an unexpected Responses payload: {response.text[:500]}"
            ) from exc

    def _responses_base_url(self, configured_base_url: str) -> str:
        base_url = configured_base_url.rstrip("/")
        if base_url.endswith("/v1"):
            return base_url
        return f"{base_url}/v1"

    def _turn_from_response(self, response: TzafonResponsesResponse, observation: BrowserObservation) -> ComputerTurn:
        computer_calls = [item for item in response.output if item.type == "computer_call" and item.action is not None]
        actions = [self._action_from_payload(item.action, observation) for item in computer_calls if item.action is not None]
        first_call_id = self._first_call_id(computer_calls)
        completed = len(actions) == 0
        return ComputerTurn(
            response_id=ComputerResponseId(response.id),
            call_id=first_call_id,
            actions=actions,
            completed=completed,
            message=self._turn_message(completed, len(actions)),
        )

    def _action_from_payload(self, payload: TzafonActionPayload, observation: BrowserObservation) -> ComputerAction:
        action_type = payload.type.lower()
        if action_type == "click":
            return ComputerAction(
                type=ComputerActionType.CLICK,
                action_id=new_action_id(),
                x=self._scale_x(payload.x, observation),
                y=self._scale_y(payload.y, observation),
                reason="Tzafon Northstar click action",
            )
        if action_type == "double_click":
            return ComputerAction(
                type=ComputerActionType.DOUBLE_CLICK,
                action_id=new_action_id(),
                x=self._scale_x(payload.x, observation),
                y=self._scale_y(payload.y, observation),
                reason="Tzafon Northstar double-click action",
            )
        if action_type == "move":
            return ComputerAction(
                type=ComputerActionType.MOVE,
                action_id=new_action_id(),
                x=self._scale_x(payload.x, observation),
                y=self._scale_y(payload.y, observation),
                reason="Tzafon Northstar pointer move",
            )
        if action_type == "scroll":
            return ComputerAction(
                type=ComputerActionType.SCROLL,
                action_id=new_action_id(),
                x=self._scale_x(payload.x, observation),
                y=self._scale_y(payload.y, observation),
                scroll_x=payload.scroll_x if payload.scroll_x is not None else payload.delta_x,
                scroll_y=payload.scroll_y if payload.scroll_y is not None else payload.delta_y,
                reason="Tzafon Northstar scroll action",
            )
        if action_type == "type":
            return ComputerAction(
                type=ComputerActionType.TYPE,
                action_id=new_action_id(),
                text=payload.text,
                reason="Tzafon Northstar text input",
            )
        if action_type == "keypress":
            return ComputerAction(
                type=ComputerActionType.KEYPRESS,
                action_id=new_action_id(),
                key=payload.key if payload.key is not None else self._join_keys(payload.keys),
                reason="Tzafon Northstar keypress",
            )
        if action_type == "wait":
            return ComputerAction(
                type=ComputerActionType.WAIT,
                action_id=new_action_id(),
                reason="Tzafon Northstar wait action",
            )
        if action_type == "screenshot":
            return ComputerAction(
                type=ComputerActionType.SCREENSHOT,
                action_id=new_action_id(),
                reason="Tzafon Northstar screenshot request",
            )
        raise UnsupportedComputerActionError(f"Tzafon returned unsupported computer action: {payload.type}")

    def _initial_prompt(self, goal: str, observation: BrowserObservation) -> str:
        return "\n".join(
            [
                "MerchantOS is testing whether this storefront is ready for autonomous computer-use agents.",
                f"Goal: {goal}",
                "Stop before checkout, payment, account login, or credential entry.",
                f"Current URL: {observation.url}",
                f"Viewport: {observation.viewport.width}x{observation.viewport.height}",
                f"Selected variant: {observation.dom_summary.selected_variant_id}",
                f"Cart count: {observation.dom_summary.cart_count}",
                "Visible structured actions:",
                self._visible_actions_text(observation.dom_summary.visible_agent_actions),
            ]
        )

    def _visible_actions_text(self, actions: list[DomActionSummary]) -> str:
        if len(actions) == 0:
            return "- none"
        return "\n".join(
            f"- {action.action}: {action.label} product={action.product_id} variant={action.variant_id}"
            for action in actions
        )

    def _instructions(self) -> str:
        return (
            "You are Tzafon Northstar controlling a browser for a merchant computer-use telemetry simulation. "
            "Use only browser actions grounded in the screenshot. Prefer safe, visible actions. "
            "Never go to checkout, place an order, enter payment details, enter credentials, or leave the merchant site."
        )

    def _computer_tool(self) -> TzafonComputerTool:
        return TzafonComputerTool(display_width=1000, display_height=1000)

    def _first_call_id(self, computer_calls: list[TzafonOutputItem]) -> ComputerCallId | None:
        for item in computer_calls:
            if item.call_id is not None:
                return ComputerCallId(item.call_id)
        return None

    def _turn_message(self, completed: bool, action_count: int) -> str:
        if completed:
            return "Tzafon Northstar completed the computer-use turn"
        return f"Tzafon Northstar proposed {action_count} computer-use action"

    def _scale_x(self, value: int | None, observation: BrowserObservation) -> int | None:
        if value is None:
            return None
        return round(value / 1000 * observation.viewport.width)

    def _scale_y(self, value: int | None, observation: BrowserObservation) -> int | None:
        if value is None:
            return None
        return round(value / 1000 * observation.viewport.height)

    def _join_keys(self, keys: list[str] | None) -> str | None:
        if keys is None:
            return None
        return "+".join(keys)
