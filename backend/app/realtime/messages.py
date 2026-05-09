from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from app.ids import ActionId, SessionId
from app.models import (
    ActionExpectation,
    BrowserActionResult,
    BrowserObservation,
    ComputerAction,
    TraceEntry,
)


class GuideReadyMessage(BaseModel):
    type: Literal["guide_ready"]
    session_id: SessionId
    observation: BrowserObservation


class ObservationMessage(BaseModel):
    type: Literal["observation"]
    session_id: SessionId
    observation: BrowserObservation


class ActionResultMessage(BaseModel):
    type: Literal["action_result"]
    session_id: SessionId
    result: BrowserActionResult


class CustomerMessage(BaseModel):
    type: Literal["customer_message"]
    session_id: SessionId
    message: str


class CustomerApprovalMessage(BaseModel):
    type: Literal["customer_approval"]
    session_id: SessionId
    approved: bool


BrowserToBackendMessage = Annotated[
    GuideReadyMessage
    | ObservationMessage
    | ActionResultMessage
    | CustomerMessage
    | CustomerApprovalMessage,
    Field(discriminator="type"),
]


class RequestObservationMessage(BaseModel):
    type: Literal["request_observation"] = "request_observation"
    session_id: SessionId


class ExecuteActionMessage(BaseModel):
    type: Literal["execute_action"] = "execute_action"
    session_id: SessionId
    action_id: ActionId
    action: ComputerAction
    expected: ActionExpectation


class AssistantUpdateMessage(BaseModel):
    type: Literal["assistant_update"] = "assistant_update"
    session_id: SessionId
    message: str


class ConfirmationRequestMessage(BaseModel):
    type: Literal["confirmation_request"] = "confirmation_request"
    session_id: SessionId
    message: str


class TraceUpdateMessage(BaseModel):
    type: Literal["trace_update"] = "trace_update"
    session_id: SessionId
    trace: TraceEntry


class GuideDoneMessage(BaseModel):
    type: Literal["guide_done"] = "guide_done"
    session_id: SessionId
    message: str


class GuideErrorMessage(BaseModel):
    type: Literal["guide_error"] = "guide_error"
    session_id: SessionId
    message: str


BackendToBrowserMessage = (
    RequestObservationMessage
    | ExecuteActionMessage
    | AssistantUpdateMessage
    | ConfirmationRequestMessage
    | TraceUpdateMessage
    | GuideDoneMessage
    | GuideErrorMessage
)


browser_message_adapter: TypeAdapter[BrowserToBackendMessage] = TypeAdapter(BrowserToBackendMessage)


def parse_browser_message(payload: str) -> BrowserToBackendMessage:
    return browser_message_adapter.validate_json(payload)

