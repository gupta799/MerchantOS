from __future__ import annotations

from typing import NewType
from uuid import uuid4

MerchantId = NewType("MerchantId", str)
SessionId = NewType("SessionId", str)
SimulationId = NewType("SimulationId", str)
ProductId = NewType("ProductId", str)
VariantId = NewType("VariantId", str)
ActionId = NewType("ActionId", str)
TraceId = NewType("TraceId", str)
EventId = NewType("EventId", str)
ComputerCallId = NewType("ComputerCallId", str)
ComputerResponseId = NewType("ComputerResponseId", str)


def new_session_id() -> SessionId:
    return SessionId(f"sess_{uuid4().hex[:10]}")


def new_simulation_id() -> SimulationId:
    return SimulationId(f"sim_{uuid4().hex[:10]}")


def new_action_id() -> ActionId:
    return ActionId(f"act_{uuid4().hex[:10]}")


def new_trace_id() -> TraceId:
    return TraceId(f"trace_{uuid4().hex[:10]}")


def new_event_id() -> EventId:
    return EventId(f"evt_{uuid4().hex[:10]}")
