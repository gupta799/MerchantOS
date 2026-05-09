from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket

from app.errors import GuideChannelError
from app.ids import SessionId
from app.models import ActionExpectation, BrowserActionResult, BrowserObservation, ComputerAction, TraceEntry
from app.realtime.messages import (
    ActionResultMessage,
    AssistantUpdateMessage,
    BackendToBrowserMessage,
    BrowserToBackendMessage,
    ExecuteActionMessage,
    GuideDoneMessage,
    GuideErrorMessage,
    ObservationMessage,
    RequestObservationMessage,
    TraceUpdateMessage,
    parse_browser_message,
)


@dataclass
class BrowserConnection:
    session_id: SessionId
    websocket: WebSocket
    inbox: asyncio.Queue[BrowserToBackendMessage] = field(default_factory=asyncio.Queue)


class SessionChannel:
    def __init__(self) -> None:
        self._connections: dict[SessionId, BrowserConnection] = {}

    async def connect(self, session_id: SessionId, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id] = BrowserConnection(session_id=session_id, websocket=websocket)

    def disconnect(self, session_id: SessionId) -> None:
        if session_id in self._connections:
            del self._connections[session_id]

    async def receive_text(self, session_id: SessionId, payload: str) -> None:
        connection = self._connection(session_id)
        message = parse_browser_message(payload)
        await connection.inbox.put(message)

    async def request_observation(self, session_id: SessionId) -> BrowserObservation:
        await self._send(session_id, RequestObservationMessage(session_id=session_id))
        message = await self._wait_for(session_id, "observation")
        if not isinstance(message, ObservationMessage):
            raise GuideChannelError("Expected observation message from browser SDK")
        return message.observation

    async def execute_action(
        self,
        session_id: SessionId,
        action: ComputerAction,
        expected: ActionExpectation,
    ) -> BrowserActionResult:
        await self._send(
            session_id,
            ExecuteActionMessage(
                session_id=session_id,
                action_id=action.action_id,
                action=action,
                expected=expected,
            ),
        )
        message = await self._wait_for(session_id, "action_result")
        if not isinstance(message, ActionResultMessage):
            raise GuideChannelError("Expected action_result message from browser SDK")
        return message.result

    async def send_assistant_update(self, session_id: SessionId, message: str) -> None:
        await self._send(session_id, AssistantUpdateMessage(session_id=session_id, message=message))

    async def send_trace_update(self, session_id: SessionId, trace_entry: TraceEntry) -> None:
        await self._send(session_id, TraceUpdateMessage(session_id=session_id, trace=trace_entry))

    async def send_done(self, session_id: SessionId, message: str) -> None:
        await self._send(session_id, GuideDoneMessage(session_id=session_id, message=message))

    async def send_error(self, session_id: SessionId, message: str) -> None:
        await self._send(session_id, GuideErrorMessage(session_id=session_id, message=message))

    def has_connection(self, session_id: SessionId) -> bool:
        return session_id in self._connections

    def _connection(self, session_id: SessionId) -> BrowserConnection:
        if session_id not in self._connections:
            raise GuideChannelError(f"No live browser SDK channel for session {session_id}")
        return self._connections[session_id]

    async def _send(self, session_id: SessionId, message: BackendToBrowserMessage) -> None:
        connection = self._connection(session_id)
        await connection.websocket.send_json(message.model_dump(mode="json"))

    async def _wait_for(self, session_id: SessionId, message_type: str) -> BrowserToBackendMessage:
        connection = self._connection(session_id)
        deadline = 10.0
        while deadline > 0:
            try:
                message = await asyncio.wait_for(connection.inbox.get(), timeout=deadline)
            except TimeoutError as exc:
                raise GuideChannelError(f"Timed out waiting for {message_type}") from exc
            if message.type == message_type:
                return message
            deadline = deadline - 0.5
        raise GuideChannelError(f"Timed out waiting for {message_type}")


session_channel = SessionChannel()

