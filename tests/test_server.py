"""HTTP and session lifecycle tests for the KnightForge browser server."""
import chess
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
    feedback = state.get("feedback")
    if feedback is not None:
        assert feedback.get("best_uci") is None
        assert feedback.get("best_san") is None
        assert feedback.get("engine_top_choice") is None


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
        # Regression: legal move options are not answer leakage.
        assert "e2e4" in payload["state"]["board"]["legal_moves_uci"]

        # A separate GET must apply the same privacy policy.
        refreshed = client.get(f"/api/sessions/{session_id}")
        assert refreshed.status_code == 200
        _assert_test_mode_answer_hidden(refreshed.json()["state"])



def test_opening_explorer_lists_curated_studies_with_review_status():
    response = client.get("/api/openings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 9
    assert payload["content_status"] == "in_review"
    assert {item["opening_id"] for item in payload["items"]} >= {
        "italian-game", "open-sicilian", "french", "caro-kann",
        "queens-gambit", "london", "kings-gambit", "english", "jobava-london",
    }
    assert all(item["review_status"] == "in_review" for item in payload["items"])
    assert client.get("/api/openings?query=najdorf").json()["items"][0]["opening_id"] == "open-sicilian"
    assert client.get("/api/openings?query=sicilian").json()["items"][0]["opening_id"] == "open-sicilian"
    assert all(item["side"] == "white" for item in client.get("/api/openings?side=white").json()["items"])
    assert client.get("/api/openings?side=invalid").status_code == 422


def test_opening_explorer_detail_contains_san_fen_and_selectable_variations():
    response = client.get("/api/openings/open-sicilian")
    assert response.status_code == 200
    opening = response.json()
    assert opening["name"] == "Open Sicilian"
    assert opening["family_name"] == "Sicilian Defence"
    assert opening["review_status"] == "in_review"
    assert opening["branch_count"] > 10
    assert opening["mainline_san"][:4] == ["e4", "c5", "Nf3", "d6"]

    def walk(nodes):
        for node in nodes:
            assert node["san"]
            assert node["uci"]
            assert len(node["fen_after"].split()) == 6
            yield node
            yield from walk(node["children"])

    nodes = list(walk(opening["roots"]))
    labels = {node["label"] for node in nodes}
    assert {"Najdorf Variation", "Dragon Variation", "Sveshnikov Variation"} <= labels
    assert all(node["path_uci"][-1] == node["uci"] for node in nodes)
    assert client.get("/api/openings/not-a-real-opening").status_code == 404



def test_opening_training_practice_hides_answer_and_accepts_only_stored_moves():
    created = client.post("/api/training", json={
        "opening_id": "italian-game", "mode": "practice",
    })
    assert created.status_code == 200
    payload = created.json()
    training_id = payload["training_id"]
    state = payload["state"]
    assert state["turn"] == "white"
    assert state["expected_move"] is None
    assert state["hints_available"] is True

    wrong = client.post(f"/api/training/{training_id}/moves", json={"uci": "d2d4"})
    assert wrong.status_code == 200
    assert wrong.json()["applied"] is False
    assert wrong.json()["state"]["fen"] == state["fen"]

    correct = client.post(f"/api/training/{training_id}/moves", json={"uci": "e2e4"})
    assert correct.status_code == 200
    next_state = correct.json()["state"]
    assert correct.json()["applied"] is True
    assert next_state["turn"] == "white"  # Black's stored e5 reply was automatic.
    assert next_state["progress"]["correct_moves"] == 1
    assert next_state["expected_move"] is None
    assert client.get(f"/api/training/{training_id}").json()["state"] == next_state


def test_opening_training_black_side_auto_plays_white_and_supports_hints():
    created = client.post("/api/training", json={
        "opening_id": "open-sicilian", "mode": "practice",
    })
    assert created.status_code == 200
    training_id = created.json()["training_id"]
    state = created.json()["state"]
    assert state["learner_color"] == "black"
    assert state["turn"] == "black"
    assert state["fen"].split()[0] != chess.STARTING_FEN.split()[0]

    hint = client.post(f"/api/training/{training_id}/hints", json={"level": 1})
    assert hint.status_code == 200
    assert hint.json()["state"]["hint"]["level"] == 1
    move = client.post(f"/api/training/{training_id}/moves", json={"uci": "c7c5"})
    assert move.status_code == 200
    assert move.json()["applied"] is True


def test_opening_training_mastery_redacts_answers_and_disables_hints():
    created = client.post("/api/training", json={
        "opening_id": "italian-game", "mode": "mastery",
    })
    assert created.status_code == 200
    training_id = created.json()["training_id"]
    state = created.json()["state"]
    assert state["expected_move"] is None
    assert state["hint"] is None
    assert state["hints_available"] is False
    assert client.post(
        f"/api/training/{training_id}/hints", json={"level": 1}
    ).status_code == 403


def test_opening_training_undo_restart_and_validation():
    assert client.post("/api/training", json={"opening_id": "missing"}).status_code == 404
    assert client.post("/api/training", json={
        "opening_id": "italian-game", "learner_color": "black",
    }).status_code == 422

    created = client.post("/api/training", json={
        "opening_id": "italian-game", "mode": "guided",
    }).json()
    training_id = created["training_id"]
    assert created["state"]["expected_move"] == "e2e4"
    client.post(f"/api/training/{training_id}/moves", json={"uci": "e2e4"})
    undone = client.post(f"/api/training/{training_id}/undo")
    assert undone.status_code == 200
    assert undone.json()["state"]["fen"] == created["state"]["fen"]
    assert undone.json()["state"]["progress"]["correct_moves"] == 0
    restarted = client.post(f"/api/training/{training_id}/restart")
    assert restarted.status_code == 200
    assert restarted.json()["state"]["fen"] == created["state"]["fen"]


def test_tactics_catalog_contains_legally_validated_mate_in_one_puzzles():
    from knightforge_engine.tactics_training import PUZZLES

    response = client.get("/api/tactics")
    assert response.status_code == 200
    assert response.json()["count"] == len(PUZZLES) == 3
    assert response.json()["themes"] == ["checkmate"]
    for puzzle in PUZZLES:
        board = chess.Board(puzzle.fen)
        assert board.is_valid()
        move = chess.Move.from_uci(puzzle.solution_uci)
        assert move in board.legal_moves
        board.push(move)
        assert board.is_checkmate()


def test_tactics_practice_hides_answer_validates_move_and_reveals_solution():
    created = client.post("/api/tactics", json={
        "puzzle_id": "queen-mate-f8", "mode": "practice",
    })
    assert created.status_code == 200
    tactics_id = created.json()["tactics_id"]
    state = created.json()["state"]
    assert state["expected_move"] is None
    assert state["hints_available"] is True
    assert state["theme"] == "checkmate"

    wrong = client.post(f"/api/tactics/{tactics_id}/moves", json={"uci": "f7e7"})
    assert wrong.status_code == 200
    assert wrong.json()["correct"] is False
    assert wrong.json()["state"]["fen"] == state["fen"]

    for level in (1, 2, 3):
        hint = client.post(f"/api/tactics/{tactics_id}/hints", json={"level": level})
        assert hint.status_code == 200
        if level < 3:
            assert hint.json()["state"]["expected_move"] is None
    assert hint.json()["state"]["expected_move"] == "f7f8"

    solved = client.post(f"/api/tactics/{tactics_id}/moves", json={"uci": "f7f8"})
    assert solved.status_code == 200
    assert solved.json()["correct"] is True
    assert solved.json()["state"]["solved"] is True
    assert solved.json()["state"]["explanation"]
    assert solved.json()["state"]["progress"]["attempts"] == 2


def test_tactics_mastery_disables_hints_and_hides_solution():
    created = client.post("/api/tactics", json={
        "puzzle_id": "queen-mate-g7", "mode": "mastery",
    })
    assert created.status_code == 200
    tactics_id = created.json()["tactics_id"]
    state = created.json()["state"]
    assert state["expected_move"] is None
    assert state["hint"] is None
    assert state["hints_available"] is False
    assert client.post(
        f"/api/tactics/{tactics_id}/hints", json={"level": 1}
    ).status_code == 403


def test_tactics_filters_restart_and_unknown_ids():
    assert client.get("/api/tactics?theme=pin").json()["count"] == 0
    assert client.get("/api/tactics?theme=checkmate").json()["count"] == 3
    assert client.post("/api/tactics", json={"puzzle_id": "missing"}).status_code == 404
    created = client.post("/api/tactics", json={
        "puzzle_id": "queen-mate-b7", "mode": "practice",
    }).json()
    tactics_id = created["tactics_id"]
    client.post(f"/api/tactics/{tactics_id}/hints", json={"level": 1})
    restarted = client.post(f"/api/tactics/{tactics_id}/restart")
    assert restarted.status_code == 200
    assert restarted.json()["state"]["hint_level"] == 0
    assert restarted.json()["state"]["progress"]["attempts"] == 0
    assert client.get("/api/tactics/unknown").status_code == 404


def test_strategy_lesson_catalog_and_detail():
    response = client.get("/api/strategy/lessons")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 6
    assert payload["content_status"] == "editorial_draft"
    assert {"development", "pawn_structure", "open_files", "outposts",
            "king_safety", "planning"} <= set(payload["themes"])
    detail = client.get("/api/strategy/lessons/pawn-structure")
    assert detail.status_code == 200
    assert detail.json()["checklist"]
    assert "long-term" in detail.json()["principle"]
    assert client.get("/api/strategy/lessons/missing").status_code == 404


def test_strategy_exercises_are_valid_and_solutions_are_legal():
    from knightforge_engine.strategy_training import EXERCISES

    response = client.get("/api/strategy/exercises")
    assert response.status_code == 200
    assert response.json()["count"] == len(EXERCISES) == 8
    for exercise in EXERCISES:
        board = chess.Board(exercise.fen)
        assert board.is_valid()
        assert chess.Move.from_uci(exercise.solution_uci) in board.legal_moves
    assert client.get("/api/strategy/exercises?theme=development").json()["count"] == 3
    assert client.get("/api/strategy/exercises?theme=nonexistent").json()["count"] == 0


def test_strategy_practice_hides_answer_and_explains_correct_decision():
    created = client.post("/api/strategy", json={
        "exercise_id": "develop-knight", "mode": "practice",
    })
    assert created.status_code == 200
    strategy_id = created.json()["strategy_id"]
    state = created.json()["state"]
    assert state["expected_move"] is None
    assert state["hints_available"] is True
    assert state["expected_move"] is None

    wrong = client.post(f"/api/strategy/{strategy_id}/moves", json={"uci": "a2a3"})
    assert wrong.status_code == 200
    assert wrong.json()["correct"] is False
    assert wrong.json()["state"]["fen"] == state["fen"]

    solved = client.post(f"/api/strategy/{strategy_id}/moves", json={"uci": "g1f3"})
    assert solved.status_code == 200
    assert solved.json()["correct"] is True
    assert solved.json()["state"]["solved"] is True
    assert "controls e5 and d4" in solved.json()["state"]["explanation"]


def test_strategy_hints_mastery_restart_and_unknown_session():
    mastery = client.post("/api/strategy", json={
        "exercise_id": "claim-centre", "mode": "mastery",
    }).json()
    strategy_id = mastery["strategy_id"]
    assert mastery["state"]["hints_available"] is False
    assert client.post(f"/api/strategy/{strategy_id}/hints", json={"level": 1}).status_code == 403

    practice = client.post("/api/strategy", json={
        "exercise_id": "develop-bishop", "mode": "practice",
    }).json()
    strategy_id = practice["strategy_id"]
    for level in (1, 2, 3):
        hint = client.post(f"/api/strategy/{strategy_id}/hints", json={"level": level})
        assert hint.status_code == 200
    assert hint.json()["state"]["expected_move"] == "f1c4"
    restarted = client.post(f"/api/strategy/{strategy_id}/restart")
    assert restarted.status_code == 200
    assert restarted.json()["state"]["hint_level"] == 0
    assert restarted.json()["state"]["progress"]["attempts"] == 0
    assert client.get("/api/strategy/not-a-session").status_code == 404
    assert client.post("/api/strategy", json={"exercise_id": "missing"}).status_code == 404


def test_middlegame_strategy_positions_and_solution_reviews():
    from knightforge_engine.strategy_training import EXERCISES, StrategySession

    middlegame = [item for item in EXERCISES if item.exercise_id.startswith("middlegame-")]
    assert len(middlegame) == 4
    for exercise in middlegame:
        board = chess.Board(exercise.fen)
        assert board.is_valid(), exercise.exercise_id
        assert board.fullmove_number >= 15, exercise.exercise_id
        move = chess.Move.from_uci(exercise.solution_uci)
        assert move in board.legal_moves, exercise.exercise_id
        session = StrategySession(exercise)
        assert session.state()["strategic_review"] is None
        result = session.submit(exercise.solution_uci)
        assert result["correct"] is True
        review = result["state"]["strategic_review"]
        assert review["plan"], exercise.exercise_id
        assert review["positional_gains"], exercise.exercise_id
        assert review["concessions"], exercise.exercise_id
        assert review["opponent_plan"], exercise.exercise_id
        assert review["candidate_comparison"], exercise.exercise_id
        assert "no engine score" in review["evaluation_basis"].lower()


def test_middlegame_catalog_marks_phase_and_hides_evaluation_until_solved():
    response = client.get("/api/strategy/exercises?difficulty=intermediate")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 4
    assert all(item["position_phase"] == "middlegame" for item in items)
    created = client.post("/api/strategy", json={
        "exercise_id": "middlegame-open-file", "mode": "practice",
    })
    assert created.status_code == 200
    state = created.json()["state"]
    assert state["position_phase"] == "middlegame"
    assert state["strategic_review"] is None
    assert state["expected_move"] is None
    solved = client.post(
        f"/api/strategy/{created.json()['strategy_id']}/moves",
        json={"uci": "d1e1"},
    )
    assert solved.status_code == 200
    review = solved.json()["state"]["strategic_review"]
    assert "e-file" in review["plan"].lower()
    assert any("rook" in item.lower() for item in review["positional_gains"])
