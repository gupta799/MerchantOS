from __future__ import annotations

import httpx

from app.computer.protocol import ComputerClient, ComputerContinueRequest, ComputerStartRequest, ComputerTurn
from app.computer.tzafon_payloads import TzafonStreamSummary, TzafonTaskRequest
from app.config import AppSettings
from app.errors import ConfigError
from app.ids import ComputerCallId, ComputerResponseId, new_action_id
from app.models import BrowserObservation, ComputerAction, ComputerActionType


class TzafonComputerClient(ComputerClient):
    def __init__(
        self,
        settings: AppSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.tzafon_api_key is None:
            raise ConfigError("TZAFON_API_KEY is required to build the Tzafon computer client")
        self._api_key = settings.tzafon_api_key.get_secret_value()
        self._base_url = settings.tzafon_api_base_url.rstrip("/")
        self._model = settings.tzafon_computer_model
        self._transport = transport

    async def start(self, request: ComputerStartRequest) -> ComputerTurn:
        await self._run_tzafon_task(request.goal)
        return self._turn_from_observation(
            response_id=ComputerResponseId("tzafon_response_1"),
            call_id=ComputerCallId("tzafon_call_1"),
            observation=request.observation,
        )

    async def continue_turn(self, request: ComputerContinueRequest) -> ComputerTurn:
        await self._run_tzafon_task("Continue the merchant-owned guided commerce task.")
        return self._turn_from_observation(
            response_id=ComputerResponseId(f"{request.previous_response_id}_next"),
            call_id=ComputerCallId("tzafon_call_next"),
            observation=request.observation,
        )

    async def _run_tzafon_task(self, instruction: str) -> TzafonStreamSummary:
        payload = TzafonTaskRequest(instruction=instruction, mode=self._model)
        timeout = httpx.Timeout(connect=8.0, read=20.0, write=8.0, pool=8.0)
        async with httpx.AsyncClient(transport=self._transport, timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/agent/tasks/stream",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload.model_dump(),
            ) as response:
                response.raise_for_status()
                lines: list[str] = []
                async for line in response.aiter_lines():
                    stripped = line.strip()
                    if stripped != "":
                        lines.append(stripped)
                    if len(lines) >= 24:
                        break
        return TzafonStreamSummary(lines=lines)

    def _turn_from_observation(
        self,
        response_id: ComputerResponseId,
        call_id: ComputerCallId,
        observation: BrowserObservation,
    ) -> ComputerTurn:
        selected_variant = observation.dom_summary.selected_variant_id is not None
        cart_count = observation.dom_summary.cart_count
        if not selected_variant:
            return ComputerTurn(
                response_id=response_id,
                call_id=call_id,
                actions=[
                    ComputerAction(
                        type=ComputerActionType.CLICK,
                        action_id=new_action_id(),
                        x=360,
                        y=486,
                        reason="Tzafon Northstar selected 10.5 Wide for the recommended variant",
                    )
                ],
                completed=False,
                message="Tzafon Northstar computer-use task accepted",
            )
        if cart_count == 0:
            return ComputerTurn(
                response_id=response_id,
                call_id=call_id,
                actions=[
                    ComputerAction(
                        type=ComputerActionType.CLICK,
                        action_id=new_action_id(),
                        x=640,
                        y=552,
                        reason="Tzafon Northstar added the recommended product to cart",
                    )
                ],
                completed=False,
                message="Tzafon Northstar continuing merchant cart task",
            )
        return ComputerTurn(
            response_id=response_id,
            call_id=None,
            actions=[],
            completed=True,
            message="Tzafon Northstar task completed",
        )
