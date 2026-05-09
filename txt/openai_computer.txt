from __future__ import annotations

from openai import AsyncOpenAI

from app.computer.mapper import map_computer_call
from app.computer.openai_payloads import computer_tool_payload, continue_input_payload, start_input_payload
from app.computer.protocol import ComputerClient, ComputerContinueRequest, ComputerStartRequest, ComputerTurn
from app.config import AppSettings
from app.ids import ComputerResponseId


class OpenAIComputerClient(ComputerClient):
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key is not None else None
        self._client = AsyncOpenAI(api_key=api_key)

    async def start(self, request: ComputerStartRequest) -> ComputerTurn:
        response = await self._client.responses.create(
            model=self._settings.openai_computer_model,
            tools=computer_tool_payload(),
            input=start_input_payload(request),
        )
        return self._map_response(response.id, response.output)

    async def continue_turn(self, request: ComputerContinueRequest) -> ComputerTurn:
        response = await self._client.responses.create(
            model=self._settings.openai_computer_model,
            tools=computer_tool_payload(),
            previous_response_id=str(request.previous_response_id),
            input=continue_input_payload(request),
        )
        return self._map_response(response.id, response.output)

    def _map_response(self, response_id: str, output_items: object) -> ComputerTurn:
        if not isinstance(output_items, list):
            return ComputerTurn(
                response_id=ComputerResponseId(response_id),
                actions=[],
                completed=True,
                message="OpenAI response contained no output list",
            )
        for item in output_items:
            item_type = getattr(item, "type", "")
            if item_type == "computer_call":
                call_id = getattr(item, "call_id")
                actions = getattr(item, "actions")
                call_payload = {
                    "type": "computer_call",
                    "call_id": call_id,
                    "actions": [action.model_dump() for action in actions],
                }
                return map_computer_call(response_id, call_payload)
        return ComputerTurn(
            response_id=ComputerResponseId(response_id),
            actions=[],
            completed=True,
            message="OpenAI computer task completed",
        )

