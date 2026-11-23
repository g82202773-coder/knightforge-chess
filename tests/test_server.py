"""HTTP and session lifecycle tests for the KnightForge browser server."""
from fastapi.testclient import TestClient

from knightforge_engine.server import app

client = TestClient(app)


def test_health_and_create_session():
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    created = client.post("/api/sessions", json={"mode": "guided"})
    assert created.status_code == 200
    payload = created.json()
    assert payload["session_id"]
    assert payload["state"]["board"]["turn"] == "white"
    assert payload["state"]["coach"]["expected_move"]["uci"] == "e2e4"


def test_move_endpoint_updates_board_and_coach_atomically():
    created = client.post("/api/sessions", json={"mode": "guided"}).json()
    session_id = created["session_id"]
    response = client.post(f"/api/sessions/{session_id}/moves", json={"uci": "e2e4"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["move"]["applied"] is True
    assert payload["move"]["actual_san"] == "e4"
    assert payload["state"]["board"]["turn"] == "black"
    assert payload["state"]["coach"]["expected_move"]["uci"] == "e7e5"


def test_illegal_move_and_unknown_session_are_rejected():
    session_id = client.post("/api/sessions", json={}).json()["session_id"]
    illegal = client.post(f"/api/sessions/{session_id}/moves", json={"uci": "e2e5"})
    assert illegal.status_code == 422
    assert client.get("/api/sessions/not-a-session").status_code == 404


def test_hints_and_mastery_mode_policy():
    guided = client.post("/api/sessions", json={"mode": "guided"}).json()
    hint = client.post(f"/api/sessions/{guided['session_id']}/hints", json={"level": 2})
    assert hint.status_code == 200
    assert hint.json()["state"]["coach"]["active_hint"]["level"] == 2
    mastery = client.post("/api/sessions", json={"mode": "mastery"}).json()
    assert mastery["state"]["coach"]["active_hint"] is None
    assert mastery["state"]["engine"]["recommendation_arrow"] is None
    blocked = client.post(f"/api/sessions/{mastery['session_id']}/hints", json={"level": 2})
    assert blocked.status_code == 403


def test_undo_and_restart():
    session_id = client.post("/api/sessions", json={}).json()["session_id"]
    client.post(f"/api/sessions/{session_id}/moves", json={"uci": "e2e4"})
    undone = client.post(f"/api/sessions/{session_id}/undo")
    assert undone.status_code == 200
    assert undone.json()["state"]["board"]["turn"] == "white"
    restarted = client.post(f"/api/sessions/{session_id}/restart")
    assert restarted.status_code == 200
    assert restarted.json()["state"]["coach"]["expected_move"]["uci"] == "e2e4"


def test_root_serves_browser_app():
    response = client.get("/")
    assert response.status_code == 200
    assert "KnightForge" in response.text
