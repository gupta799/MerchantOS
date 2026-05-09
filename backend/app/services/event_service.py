from __future__ import annotations

from app.ids import SessionId
from app.models import MerchantEvent, MerchantEventAck, MerchantEventCreate
from app.store import InMemoryStore


class EventService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def store_event(self, session_id: SessionId, event: MerchantEventCreate) -> MerchantEventAck:
        stored = self._store.add_event(session_id, event)
        return MerchantEventAck(event_id=stored.event_id)

    def list_events(self, session_id: SessionId) -> list[MerchantEvent]:
        return self._store.events_for_session(session_id)

