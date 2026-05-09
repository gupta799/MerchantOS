from __future__ import annotations

from fastapi.testclient import TestClient


def test_session_route_returns_merchant_owned_state(client: TestClient) -> None:
    intent_response = client.post(
        "/api/agent-intent",
        json={"user_goal": "Find waterproof trail running shoes under $150"},
    )
    assert intent_response.status_code == 200
    session_id = intent_response.json()["session_id"]
    session_response = client.get(f"/api/sessions/{session_id}")
    assert session_response.status_code == 200
    body = session_response.json()
    assert body["recommended_products"][0]["name"] == "StormRunner GTX"
    assert body["cart"]["items"] == []


def test_runtime_route_returns_active_demo_modes(client: TestClient) -> None:
    response = client.get("/api/runtime")
    assert response.status_code == 200
    body = response.json()
    assert body["harness_mode"] == "scripted"
    assert body["harness_model_provider"] == "llamacpp"
    assert body["harness_model"] == "gemma4-e4b-it"
    assert body["computer_client_mode"] == "scripted"
    assert body["browser_environment"] == "local_sdk"
    assert body["demo_mode"] is True


def test_simulation_routes_return_telemetry_and_mcp_recommendations(client: TestClient) -> None:
    created = client.post(
        "/api/simulations",
        json={"merchant_id": "demo_shop", "scenario_id": "autonomous_commerce_readiness"},
    )
    assert created.status_code == 200
    simulation_id = created.json()["simulation_id"]

    simulation = client.get(f"/api/simulations/{simulation_id}")
    telemetry = client.get(f"/api/simulations/{simulation_id}/telemetry")
    mcp = client.get(f"/api/simulations/{simulation_id}/mcp-readiness")

    assert simulation.status_code == 200
    assert telemetry.status_code == 200
    assert mcp.status_code == 200
    assert simulation.json()["scenario"]["title"] == "Autonomous commerce readiness probe"
    assert simulation.json()["browser_environment"] == "local_sdk"
    assert telemetry.json()["metrics"][0]["key"] == "task_completion_rate"
    assert mcp.json()["recommendations"][0]["name"] == "catalog.search"
