from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.ids import ComputerCallId, ComputerResponseId
from app.models import BrowserObservation, ComputerAction


class ComputerStartRequest(BaseModel):
    goal: str
    observation: BrowserObservation


class ComputerContinueRequest(BaseModel):
    previous_response_id: ComputerResponseId
    call_id: ComputerCallId
    observation: BrowserObservation


class ComputerTurn(BaseModel):
    response_id: ComputerResponseId
    call_id: ComputerCallId | None = None
    actions: list[ComputerAction]
    completed: bool = False
    message: str = ""


class ComputerClient(Protocol):
    async def start(self, request: ComputerStartRequest) -> ComputerTurn:
        ...

    async def continue_turn(self, request: ComputerContinueRequest) -> ComputerTurn:
        ...

