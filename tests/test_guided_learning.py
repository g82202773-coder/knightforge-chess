"""Tests for position-aware guided opening lessons."""
import pytest

from knightforge_engine import GuidedLesson, GuidedLessonSession, LessonNode


def sample_lesson():
    return GuidedLesson(
        lesson_id="open-game-basics",
        title="Open Game Basics",
        learner_color="white",
        roots=(LessonNode(
            "e2e4", "Control the centre and open lines for the queen and bishop.",
            children=(
                LessonNode("e7e5", "Black contests the centre.", children=(
                    LessonNode("g1f3", "Develop the knight and attack the e5 pawn."),
                )),
                LessonNode("c7c5", "Black chooses the Sicilian Defence.", children=(
                    LessonNode("g1f3", "Develop the knight and prepare to challenge the centre."),
                )),
            ),
        ),),
    )


def test_prompt_is_position_derived_and_includes_arrow_and_voice():
    session = GuidedLessonSession(sample_lesson())
    prompt = session.prompt()
    assert prompt.expected_uci == "e2e4"
    assert prompt.expected_san == "e4"
    assert (prompt.arrow_from, prompt.arrow_to) == ("e2", "e4")
    assert "E2" in prompt.voice_script
    assert "centre" in prompt.voice_script
    assert prompt.fen == session.game.fen


def test_wrong_legal_learner_move_is_not_applied_and_can_retry():
    session = GuidedLessonSession(sample_lesson())
    result = session.submit_uci("d2d4")
    assert not result.accepted and not result.applied
    assert result.correct is False
    assert session.game.fen == sample_lesson().starting_fen
    assert result.prompt.kind == "correction"
    assert result.prompt.expected_uci == "e2e4"


def test_actual_opponent_reply_selects_matching_branch():
    session = GuidedLessonSession(sample_lesson())
    session.submit_uci("e2e4")
    assert session.prompt().expected_uci == "e7e5"
    result = session.submit_uci("c7c5")
    assert result.correct is True
    assert result.prompt.expected_uci == "g1f3"
    assert result.prompt.explanation.startswith("Develop the knight")


def test_unexpected_opponent_move_applies_but_does_not_invent_line():
    session = GuidedLessonSession(sample_lesson())
    session.submit_uci("e2e4")
    result = session.submit_uci("d7d5")
    assert result.applied and result.correct is None
    assert result.prompt.kind == "opponent_deviation"
    assert result.prompt.expected_uci is None
    with pytest.raises(RuntimeError):
        session.submit_uci("g1f3")


def test_illegal_move_is_rejected():
    session = GuidedLessonSession(sample_lesson())
    with pytest.raises(ValueError, match="Illegal move"):
        session.submit_uci("e2e5")


def test_undo_restores_board_and_lesson_progress():
    session = GuidedLessonSession(sample_lesson())
    session.submit_uci("e2e4")
    after = session.game.fen
    session.undo()
    assert session.game.fen == sample_lesson().starting_fen
    assert session.prompt().expected_uci == "e2e4"
    session.submit_uci("e2e4")
    assert session.game.fen == after


def test_restart_clears_session_state():
    session = GuidedLessonSession(sample_lesson())
    session.submit_uci("e2e4")
    session.restart()
    assert session.prompt().expected_uci == "e2e4"
    assert session.game.fen == sample_lesson().starting_fen


def test_lesson_validation_rejects_illegal_branch():
    lesson = GuidedLesson("bad", "Bad lesson", "white", (LessonNode("e2e5", "Illegal."),))
    with pytest.raises(ValueError, match="Illegal lesson move"):
        lesson.validate()
