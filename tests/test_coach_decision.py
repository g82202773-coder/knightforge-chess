"""Tests for evidence-grounded coach decisions."""

import chess
import pytest

from knightforge_engine.analysis import AnalysisResult, EngineLine
from knightforge_engine.coach_decision import CoachDecisionLayer


def result(lines=None, fen=chess.STARTING_FEN):
    defaults = (
        EngineLine(1, 12, 35, None, ("g1f3", "g8f6"), ("Nf3", "Nf6")),
        EngineLine(2, 12, 20, None, ("d2d4", "d7d5"), ("d4", "d5")),
    )
    return AnalysisResult(
        engine_name="Test Engine",
        engine_version="1",
        fen=fen,
        depth=12,
        nodes=1000,
        lines=tuple(defaults if lines is None else lines),
    )


def test_recommendations_are_legal_and_explain_concrete_board_facts():
    layer = CoachDecisionLayer(result())
    best = layer.best
    assert best.uci == "g1f3"
    assert best.san == "Nf3"
    assert best.piece == "knight"
    assert (best.from_square, best.to_square) == ("g1", "f3")
    assert best.principal_variation_san == ("Nf3", "Nf6")
    assert best.engine_score_cp == 35
    assert "not a win probability" in best.evaluation_disclaimer


def test_progressive_hints_reveal_piece_then_source_then_destination_then_move():
    hints = CoachDecisionLayer(result()).best.hints
    assert [hint.level for hint in hints] == [1, 2, 3, 4]
    assert hints[0].arrow_from is None
    assert hints[1].arrow_from == "g1" and hints[1].arrow_to is None
    assert (hints[2].arrow_from, hints[2].arrow_to) == ("g1", "f3")
    assert hints[3].reveal_uci == "g1f3"


def test_comparison_uses_same_pre_move_position_and_candidate_rank():
    layer = CoachDecisionLayer(result())
    comparison = layer.compare_move("d2d4", position_fen=chess.STARTING_FEN)
    assert comparison.played_san == "d4"
    assert comparison.matched_candidate_rank == 2
    assert not comparison.is_engine_top_choice
    assert "not the top-ranked" in comparison.explanation


def test_legal_move_outside_returned_candidates_is_not_called_a_blunder():
    layer = CoachDecisionLayer(result())
    comparison = layer.compare_move("e2e4", position_fen=chess.STARTING_FEN)
    assert comparison.matched_candidate_rank is None
    assert "does not prove the move is a blunder" in comparison.explanation


def test_comparison_rejects_analysis_from_a_different_position():
    layer = CoachDecisionLayer(result())
    board = chess.Board()
    board.push_uci("e2e4")
    with pytest.raises(ValueError, match="same position"):
        layer.compare_move("e7e5", position_fen=board.fen())


def test_comparison_rejects_illegal_move():
    layer = CoachDecisionLayer(result())
    with pytest.raises(ValueError, match="not legal"):
        layer.compare_move("e2e5", position_fen=chess.STARTING_FEN)


def test_invalid_engine_principal_variation_is_rejected():
    bad = EngineLine(1, 10, 0, None, ("e2e5",), ("e5",))
    with pytest.raises(ValueError, match="illegal move sequence"):
        CoachDecisionLayer(result((bad,)))


def test_empty_or_terminal_analysis_cannot_make_recommendation():
    with pytest.raises(ValueError, match="at least one"):
        CoachDecisionLayer(result(()))
    board = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    with pytest.raises(ValueError, match="finished position"):
        CoachDecisionLayer(result((EngineLine(1, 1, 0, None, (), ()),), board.fen()))
