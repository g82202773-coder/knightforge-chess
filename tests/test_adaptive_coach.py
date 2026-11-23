"""Tests for adaptive opening-coach orchestration."""
import chess

from knightforge_engine import (
    AdaptiveOpeningCoach,
    GuidedLesson,
    LessonNode,
    OpeningRepository,
    OpeningTree,
    VariationNode,
)


def reviewed_repository():
    tree = OpeningTree(
        opening_id="open-game",
        name="Open Game",
        side="both",
        source_name="Curated test source",
        license_name="CC0",
        review_status="reviewed",
        anchor_uci=("e2e4", "e7e5"),
        roots=(VariationNode(
            "e2e4",
            children=(VariationNode(
                "e7e5",
                label="Open Game",
                children=(VariationNode(
                    "g1f3", label="King's Knight Opening"
                ),),
            ),),
        ),),
    )
    repository = OpeningRepository()
    repository.add(tree)
    return repository


def lesson():
    return GuidedLesson(
        "open-game-coach",
        "Open Game Coach",
        "white",
        (LessonNode(
            "e2e4",
            "Occupy the centre.",
            children=(LessonNode(
                "e7e5",
                "Black mirrors the central pawn move.",
                children=(LessonNode(
                    "g1f3", "Develop the knight toward the centre."
                ),),
            ),),
        ),),
    )


def test_coach_connects_lesson_to_reviewed_opening_and_variation():
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository())
    initial = coach.prompt()
    assert initial.prompt.expected_uci == "e2e4"
    assert initial.knowledge_status == "no_reviewed_match"

    coach.submit_uci("e2e4")
    after_black = coach.submit_uci("e7e5").state
    assert after_black.knowledge_status == "reviewed_opening_anchor_only"
    assert after_black.recognition.matches[0].name == "Open Game"

    after_knight = coach.submit_uci("g1f3").state
    assert after_knight.knowledge_status == "reviewed_variation_match"
    assert after_knight.variation_match.matches[0].matched_line_san == (
        "e4", "e5", "Nf3"
    )
    assert after_knight.prompt.expected_uci is None


def test_coach_reports_unreviewed_deviation_without_inventing_theory():
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository())
    coach.submit_uci("e2e4")
    deviation = coach.submit_uci("d7d5").state
    assert deviation.prompt.kind == "opponent_deviation"
    assert deviation.knowledge_status == "no_reviewed_match"
    assert not deviation.variation_match.matches


def test_coach_undo_refreshes_position_knowledge():
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository())
    coach.submit_uci("e2e4")
    coach.submit_uci("e7e5")
    undone = coach.undo()
    assert undone.fen == chess.Board().fen()
    assert undone.prompt.expected_uci == "e2e4"
