from __future__ import annotations

from app.computer.openai_computer import OpenAIComputerClient
from app.computer.protocol import ComputerClient, ComputerContinueRequest, ComputerStartRequest, ComputerTurn
from app.computer.scripted_computer import ScriptedComputerClient
from app.computer.tzafon_computer import TzafonComputerClient
from app.config import AppSettings
from app.privacy import sanitize_observation_for_computer_use


class ComputerService:
    def __init__(self, settings: AppSettings, client: ComputerClient | None = None) -> None:
        self._settings = settings
        self._client = client if client is not None else self._build_client(settings)

    async def start(self, request: ComputerStartRequest) -> ComputerTurn:
        sanitized = sanitize_observation_for_computer_use(request.observation)
        return await self._client.start(request.model_copy(update={"observation": sanitized}))

    async def continue_turn(self, request: ComputerContinueRequest) -> ComputerTurn:
        sanitized = sanitize_observation_for_computer_use(request.observation)
        return await self._client.continue_turn(request.model_copy(update={"observation": sanitized}))

    def _build_client(self, settings: AppSettings) -> ComputerClient:
        if settings.computer_client_mode == "openai":
            return OpenAIComputerClient(settings)
        if settings.computer_client_mode == "tzafon":
            return TzafonComputerClient(settings)
        return ScriptedComputerClient()
