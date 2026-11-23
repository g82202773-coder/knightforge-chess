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
    practice = client.post("/api/sessions", json={"mode": "practice"}).json()
    practice_id = practice["session_id"]
    assert practice["state"]["coach"]["active_hint"] is None
    first_hint = client.post(f"/api/sessions/{practice_id}/hints", json={"level": 1})
    assert first_hint.status_code == 200
    assert first_hint.json()["state"]["coach"]["active_hint"]["level"] == 1
    guided = client.post("/api/sessions", json={"mode": "guided"}).json()
    hint = client.post(f"/api/sessions/{guided['session_id']}/hints", json={"level": 2})
    assert hint.status_code == 200
    assert hint.json()["state"]["coach"]["active_hint"]["level"] == 2
    mastery = client.post("/api/sessions", json={"mode": "mastery"}).json()
    assert mastery["state"]["coach"]["active_hint"] is None
    assert mastery["state"]["engine"]["recommendation_arrow"] is None
    blocked = client.post(f"/api/sessions/{mastery['session_id']}/hints", json={"level": 2})
    assert blocked.status_code == 403



def test_practice_hint_endpoint_works_without_stockfish():
    practice = client.post("/api/sessions", json={"mode": "practice"}).json()
    session_id = practice["session_id"]
    hint = client.post(f"/api/sessions/{session_id}/hints", json={"level": 1})
    assert hint.status_code == 200
    assert hint.json()["state"]["coach"]["active_hint"]["level"] == 1


def test_practice_and_mastery_do_not_leak_the_lesson_answer():
    for mode in ("practice", "mastery"):
        created = client.post("/api/sessions", json={"mode": mode}).json()
        coach = created["state"]["coach"]
        assert coach["expected_move"] is None
        assert "E2" not in coach["text"]
        assert "e2e4" not in str(coach)
        assert created["state"]["board"]["highlighted_squares"] == []
        assert created["state"]["engine"]["recommendation"] is None
    practice = client.post("/api/sessions", json={"mode": "practice"}).json()
    assert practice["state"]["coach"]["hints_available"] is True
    mastery = client.post("/api/sessions", json={"mode": "mastery"}).json()
    assert mastery["state"]["coach"]["hints_available"] is False


def test_test_modes_redact_best_move_from_comparison_feedback(tmp_path):
    from knightforge_engine.server import apply_mode_policy, store

    for mode in ("practice", "mastery"):
        _, record = store.create(mode)
        feedback = {
            "played_uci": "d2d4",
            "played_san": "d4",
            "best_uci": "e2e4",
            "best_san": "e4",
            "engine_top_choice": "e4",
            "matched_candidate_rank": None,
            "is_engine_top_choice": False,
            "explanation": "Legal move, not among returned candidates.",
            "analysis_fen": "starting-position",
            "comparison_scope": "candidate-list membership only",
        }
        payload = {
            "state": {
                "board": {"highlighted_squares": []},
                "coach": {"text": "", "voice_script": "", "explanation": "",
                          "expected_move": None, "active_hint": None},
                "engine": {"recommendation": None, "recommendation_arrow": None},
                "feedback": feedback.copy(),
            }
        }
        result = apply_mode_policy(payload, record)
        redacted = result["state"]["feedback"]
        assert redacted["best_uci"] is None
        assert redacted["best_san"] is None
        assert redacted["engine_top_choice"] is None
        assert redacted["played_uci"] == "d2d4"

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

def _assert_test_mode_answer_hidden(state):
    """Check answer-bearing fields without banning ordinary legal move options."""
    assert state["coach"]["expected_move"] is None
    assert "e2e4" not in str(state["coach"])
    assert state["board"]["highlighted_squares"] == []
    assert state["engine"]["recommendation"] is None
    assert state["engine"]["recommendation_arrow"] is None
    assert "e2e4" not in str(state["engine"])
    assert "e4" not in str(state.get("feedback"))


def test_test_modes_keep_answer_hidden_after_move_and_state_refresh():
    for mode in ("practice", "mastery"):
        created = client.post("/api/sessions", json={"mode": mode}).json()
        session_id = created["session_id"]
        _assert_test_mode_answer_hidden(created["state"])

        # A legal but off-lesson learner move must not expose the curated answer.
        moved = client.post(
            f"/api/sessions/{session_id}/moves",
            json={"uci": "d2d4"},
        )
        assert moved.status_code == 200
        payload = moved.json()
        assert payload["move"]["applied"] is False
        _assert_test_mode_answer_hidden(payload["state"])

        # Legal move options remain visible so the board can operate normally.
        assert "e2e4" in payload["state"]["board"]["legal_moves_uci"]

        # A separate GET must apply the same privacy policy.
        refreshed = client.get(f"/api/sessions/{session_id}")
        assert refreshed.status_code == 200
        _assert_test_mode_answer_hidden(refreshed.json()["state"])

