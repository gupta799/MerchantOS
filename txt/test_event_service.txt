from __future__ import annotations

from app.config import AppSettings
from app.models import AgentIntentRequest, MerchantEventCreate, MerchantEventType
from app.services.event_service import EventService
from app.services.intent_service import IntentService
from app.store import InMemoryStore


def test_event_service_stores_merchant_event() -> None:
    local_store = InMemoryStore()
    intent = IntentService(local_store, AppSettings(AGENTREADY_COMPUTER_CLIENT="scripted"))
    created = intent.create_intent_session(AgentIntentRequest(user_goal="Find shoes"))
    event_service = EventService(local_store)
    ack = event_service.store_event(
        created.session_id,
        MerchantEventCreate(type=MerchantEventType.GUIDED_SESSION_OPENED),
    )
    assert ack.stored is True
    assert len(event_service.list_events(created.session_id)) == 1

