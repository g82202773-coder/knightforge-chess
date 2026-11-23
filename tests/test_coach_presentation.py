"""JSON presentation contract tests for chess clients."""

import json

import chess

from knightforge_engine import (
    AdaptiveOpeningCoach,
    GuidedLesson,
    LessonNode,
    OpeningRepository,
    coach_state_payload,
    submission_payload,
)
from knightforge_engine.analysis import AnalysisResult, EngineLine


class FakeAnalyzer:
    def analyse(self, fen, *, time_limit=1.0, depth=None, multipv=3):
        board = chess.Board(fen)
        move = chess.Move.from_uci(
            "g1f3" if fen == chess.STARTING_FEN else "e7e5"
        )
        assert move in board.legal_moves
        return AnalysisResult(
            engine_name="Fake",
            engine_version="test",
            fen=board.fen(),
            depth=depth or 8,
            nodes=100,
            lines=(EngineLine(
                multipv=1,
                depth=depth or 8,
                score_cp=20,
                score_mate=None,
                moves_uci=(move.uci(),),
                moves_san=(board.san(move),),
            ),),
        )


def make_coach(tmp_path):
    lesson = GuidedLesson(
        "presentation-test",
        "Presentation Test",
        "white",
        (LessonNode("e2e4", "Control the centre."),),
    )
    repository = OpeningRepository.load(tmp_path / "openings.json")
    return AdaptiveOpeningCoach(lesson, repository, analyzer=FakeAnalyzer())


def test_state_payload_contains_board_prompt_recommendation_hint_and_arrow(tmp_path):
    coach = make_coach(tmp_path)
    payload = coach_state_payload(coach.state)

    assert payload["board"]["fen"] == chess.STARTING_FEN
    assert payload["board"]["turn"] == "white"
    assert payload["coach"]["kind"] == "move"
    assert payload["engine"]["recommendation"]["uci"] == "g1f3"
    assert payload["coach"]["active_hint"]["level"] == 1
    assert payload["engine"]["recommendation_arrow"] == {
        "from": "g1",
        "to": "f3",
    }
    json.dumps(payload)


def test_submission_payload_includes_comparison_and_new_position_guidance(tmp_path):
    coach = make_coach(tmp_path)
    result = coach.submit_uci("e2e4")
    payload = submission_payload(result)

    assert payload["move"]["applied"] is True
    assert payload["move"]["actual_san"] == "e4"
    assert payload["state"]["feedback"]["played_uci"] == "e2e4"
    assert payload["state"]["board"]["turn"] == "black"
    assert payload["state"]["engine"]["recommendation"]["uci"] == "e7e5"
    assert payload["state"]["coach"]["active_hint"]["level"] == 1
    json.dumps(payload)


def test_payload_represents_missing_engine_analysis_without_breaking_board(tmp_path):
    lesson = GuidedLesson(
        "no-engine-test",
        "No Engine",
        "white",
        (LessonNode("e2e4", "Control the centre."),),
    )
    repository = OpeningRepository.load(tmp_path / "empty.json")
    coach = AdaptiveOpeningCoach(lesson, repository)
    payload = coach_state_payload(coach.state)

    assert payload["board"]["fen"] == chess.STARTING_FEN
    assert payload["engine"]["recommendation"] is None
    assert payload["engine"]["recommendation_arrow"] is None
    assert payload["engine"]["analysis_error"] is None
    json.dumps(payload)
