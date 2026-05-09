from __future__ import annotations

import os

os.environ.setdefault("AGENTREADY_HARNESS_MODE", "scripted")
os.environ.setdefault("AGENTREADY_COMPUTER_CLIENT", "scripted")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store


@pytest.fixture(autouse=True)
def clear_store() -> None:
    store.sessions.clear()
    store.carts.clear()
    store.events.clear()
    store.traces.clear()
    store.simulations.clear()
    store.simulation_ids_by_session.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
