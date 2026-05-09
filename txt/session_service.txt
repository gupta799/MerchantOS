from __future__ import annotations

from app.demo_data import demo_catalog
from app.ids import SessionId
from app.models import SessionResponse, SessionStatus
from app.store import InMemoryStore


class SessionService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get_session_response(self, session_id: SessionId) -> SessionResponse:
        session = self._store.get_session(session_id)
        cart = self._store.get_cart(session_id)
        return SessionResponse(
            session_id=session.session_id,
            merchant_id=session.merchant_id,
            source_agent=session.source_agent,
            intent_goal=session.user_goal,
            preferences=session.preferences,
            status=session.status,
            recommended_products=session.recommended_products,
            products=demo_catalog(),
            cart=cart,
            relationship_prompts=session.relationship_prompts,
            consent=session.consent,
            assistant_message="Automated CUA simulation environment is ready to collect telemetry.",
        )

    def set_status(self, session_id: SessionId, status: SessionStatus) -> None:
        self._store.set_status(session_id, status)
