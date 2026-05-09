from __future__ import annotations

from app.ids import SessionId, new_trace_id
from app.models import (
    ActionVerification,
    BrowserObservation,
    ComputerAction,
    TraceEntry,
    TraceResponse,
    VerificationStatus,
)
from app.store import InMemoryStore


class TraceService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def record_observation(self, session_id: SessionId, observation: BrowserObservation) -> TraceEntry:
        return self._store.add_trace(
            TraceEntry(
                trace_id=new_trace_id(),
                session_id=session_id,
                observation=observation,
                verification=ActionVerification(
                    status=VerificationStatus.PENDING,
                    message="Browser observation captured",
                ),
            )
        )

    def record_action(
        self,
        session_id: SessionId,
        action: ComputerAction,
        observation: BrowserObservation,
        status: VerificationStatus,
        message: str,
    ) -> TraceEntry:
        return self._store.add_trace(
            TraceEntry(
                trace_id=new_trace_id(),
                session_id=session_id,
                action=action,
                observation=observation,
                verification=ActionVerification(status=status, message=message),
            )
        )

    def response(self, session_id: SessionId) -> TraceResponse:
        return TraceResponse(session_id=session_id, entries=self._store.traces_for_session(session_id))

