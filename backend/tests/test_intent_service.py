from __future__ import annotations

from app.config import AppSettings
from app.models import AgentIntentRequest
from app.services.intent_service import IntentService
from app.store import InMemoryStore


def test_intent_service_creates_session_with_stormrunner() -> None:
    service = IntentService(InMemoryStore(), AppSettings(AGENTREADY_COMPUTER_CLIENT="scripted"))
    response = service.create_intent_session(
        AgentIntentRequest(user_goal="Find waterproof trail running shoes under $150")
    )
    assert response.session_id.startswith("sess_")
    assert "/agent-session/" in response.handoff_url

