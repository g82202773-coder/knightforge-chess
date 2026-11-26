"""Regression tests for the user-requested 40-repertoire Gambit Academy."""

from pathlib import Path

from knightforge_engine.gambit_curriculum import build_gambit_library
from knightforge_engine.guided_learning import GuidedLessonSession
from knightforge_engine.opening_trainer import build_opening_lesson, list_opening_variations
from knightforge_engine.server import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_all_40_gambits_and_all_210_supplied_lines_are_legal():
    library = build_gambit_library(Path("data/openings/gambit_curriculum.json"))
    assert len(library.entries) == 40
    assert len(library.trees) == 40
    assert library.report()["white_count"] == 20
    assert library.report()["black_count"] == 20
    assert library.report()["source_line_count"] == 210
    assert library.issues == (), [issue.to_dict() for issue in library.issues]
    assert library.report()["validated_line_count"] == 210


def test_each_gambit_exposes_named_variations_and_a_guided_coach_lesson():
    library = build_gambit_library()
    for tree in library.trees:
        variations = list_opening_variations(tree)
        assert variations, tree.opening_id
        selected = variations[0]
        lesson = build_opening_lesson(
            tree,
            variation_id=selected.variation_id,
            learner_color=tree.side,
        )
        session = GuidedLessonSession(lesson)
        for uci in selected.moves_uci:
            outcome = session.submit_uci(uci)
            assert outcome.applied is True, (tree.opening_id, selected.label, uci)
            assert outcome.correct is True, (tree.opening_id, selected.label, uci)
        assert session.prompt().kind in {"complete", "free_play"}


def test_gambit_api_lists_twenty_white_and_twenty_black_repertoires():
    white = client.get("/api/gambits?side=white").json()
    black = client.get("/api/gambits?side=black").json()
    assert white["report"]["gambit_count"] == 40
    assert len(white["gambits"]) == 20
    assert len(black["gambits"]) == 20
    assert {item["side"] for item in white["gambits"]} == {"white"}
    assert {item["side"] for item in black["gambits"]} == {"black"}


def test_learner_can_select_variation_and_start_coach_training():
    guide = client.get("/api/gambits/white-kings-gambit")
    assert guide.status_code == 200
    assert guide.json()["validated_line_count"] >= 5
    variations = client.get("/api/openings/white-kings-gambit/variations")
    assert variations.status_code == 200
    selected = variations.json()["variations"][0]
    started = client.post(
        "/api/openings/white-kings-gambit/train",
        json={
            "variation_id": selected["variation_id"],
            "mode": "guided",
            "learner_color": "white",
            "auto_reply": True,
        },
    )
    assert started.status_code == 200, started.text
    payload = started.json()
    assert payload["session_id"]
    assert payload["state"]["coach"]["expected_move"]["uci"] == selected["moves_uci"][0]
