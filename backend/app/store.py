from __future__ import annotations

from dataclasses import dataclass, field

from app.errors import NotFoundError
from app.ids import EventId, SessionId, SimulationId, new_event_id
from app.models import (
    Cart,
    MerchantEvent,
    MerchantEventCreate,
    MerchantSession,
    SessionStatus,
    SimulationRun,
    TraceEntry,
    utc_now,
)


@dataclass
class InMemoryStore:
    sessions: dict[SessionId, MerchantSession] = field(default_factory=dict)
    carts: dict[SessionId, Cart] = field(default_factory=dict)
    events: dict[SessionId, list[MerchantEvent]] = field(default_factory=dict)
    traces: dict[SessionId, list[TraceEntry]] = field(default_factory=dict)
    simulations: dict[SimulationId, SimulationRun] = field(default_factory=dict)
    simulation_ids_by_session: dict[SessionId, SimulationId] = field(default_factory=dict)

    def create_session(self, session: MerchantSession, cart: Cart) -> MerchantSession:
        self.sessions[session.session_id] = session
        self.carts[session.session_id] = cart
        self.events[session.session_id] = []
        self.traces[session.session_id] = []
        return session

    def get_session(self, session_id: SessionId) -> MerchantSession:
        if session_id not in self.sessions:
            raise NotFoundError(f"Session {session_id} was not found")
        return self.sessions[session_id]

    def update_session(self, session: MerchantSession) -> MerchantSession:
        session.updated_at = utc_now()
        self.sessions[session.session_id] = session
        return session

    def set_status(self, session_id: SessionId, status: SessionStatus) -> MerchantSession:
        session = self.get_session(session_id)
        updated = session.model_copy(update={"status": status, "updated_at": utc_now()})
        return self.update_session(updated)

    def get_cart(self, session_id: SessionId) -> Cart:
        if session_id not in self.carts:
            raise NotFoundError(f"Cart for session {session_id} was not found")
        return self.carts[session_id]

    def save_cart(self, cart: Cart) -> Cart:
        self.carts[cart.session_id] = cart
        return cart

    def add_event(self, session_id: SessionId, event_create: MerchantEventCreate) -> MerchantEvent:
        event_id = EventId(new_event_id())
        event = MerchantEvent(
            event_id=event_id,
            session_id=session_id,
            type=event_create.type,
            source=event_create.source,
            product_id=event_create.product_id,
            variant_id=event_create.variant_id,
            message=event_create.message,
        )
        event_list = self.events_for_session(session_id)
        event_list.append(event)
        self.events[session_id] = event_list
        return event

    def events_for_session(self, session_id: SessionId) -> list[MerchantEvent]:
        if session_id not in self.events:
            raise NotFoundError(f"Events for session {session_id} were not found")
        return self.events[session_id]

    def add_trace(self, entry: TraceEntry) -> TraceEntry:
        trace_list = self.traces_for_session(entry.session_id)
        trace_list.append(entry)
        self.traces[entry.session_id] = trace_list
        return entry

    def traces_for_session(self, session_id: SessionId) -> list[TraceEntry]:
        if session_id not in self.traces:
            raise NotFoundError(f"Traces for session {session_id} were not found")
        return self.traces[session_id]

    def create_simulation(self, simulation: SimulationRun) -> SimulationRun:
        self.simulations[simulation.simulation_id] = simulation
        self.simulation_ids_by_session[simulation.session_id] = simulation.simulation_id
        return simulation

    def get_simulation(self, simulation_id: SimulationId) -> SimulationRun:
        if simulation_id not in self.simulations:
            raise NotFoundError(f"Simulation {simulation_id} was not found")
        return self.simulations[simulation_id]

    def update_simulation(self, simulation: SimulationRun) -> SimulationRun:
        updated = simulation.model_copy(update={"updated_at": utc_now()})
        self.simulations[simulation.simulation_id] = updated
        return updated

    def list_simulations(self) -> list[SimulationRun]:
        return list(self.simulations.values())

    def simulation_id_for_session(self, session_id: SessionId) -> SimulationId | None:
        return self.simulation_ids_by_session.get(session_id)


store = InMemoryStore()
