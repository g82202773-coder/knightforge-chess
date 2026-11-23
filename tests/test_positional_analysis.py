import chess
import pytest

from knightforge_engine.positional_analysis import analyze_position


def test_detects_isolated_and_passed_pawn():
    result = analyze_position("7k/8/8/8/3P4/8/8/7K w - - 0 1", ["d4d5"])
    report = result["position_features"]["white_pawns"]
    assert "d4" in report["isolated"]
    assert "d4" in report["passed"]


def test_detects_doubled_pawns():
    result = analyze_position("7k/8/8/8/3P4/3P4/8/7K w - - 0 1", ["d4d5"])
    assert set(result["position_features"]["white_pawns"]["doubled"]) == {"d4", "d3"}


def test_identifies_pawn_supported_outpost_square():
    result = analyze_position("7k/8/8/8/2P5/8/8/7K w - - 0 1", ["c4c5"])
    assert "d5" in result["position_features"]["white_outpost_squares"]
    assert "d5" in result["position_features"]["white_weak_squares"]


def test_reports_open_file_and_active_rook():
    result = analyze_position("7k/8/8/8/8/8/8/R6K w - - 0 1", ["a1a2"])
    rook_report = result["position_features"]["white_rooks"]
    assert "a" in rook_report["open_files"]
    assert "a1" in rook_report["rooks_on_open_or_half_open_files"]


def test_compares_legal_candidates_and_includes_practical_reply():
    result = analyze_position(chess.STARTING_FEN, ["e2e4", "d2d4"])
    assert {item["uci"] for item in result["candidates"]} == {"e2e4", "d2d4"}
    assert all(item["opponent_practical_reply"] for item in result["candidates"])
    assert "heuristic points, not centipawns" == result["methodology"]["score_unit"]


def test_rejects_illegal_candidate_and_invalid_fen():
    with pytest.raises(ValueError, match="illegal"):
        analyze_position(chess.STARTING_FEN, ["e2e5"])
    with pytest.raises(ValueError, match="Invalid FEN"):
        analyze_position("not a fen", ["e2e4"])


def test_candidate_limit_is_enforced():
    with pytest.raises(ValueError, match="at most 12"):
        analyze_position(chess.STARTING_FEN, ["e2e4"] * 13)


def test_default_analysis_limits_to_twelve_legal_candidates():
    result = analyze_position(chess.STARTING_FEN)
    assert len(result["candidates"]) == 12
    assert all(item["uci"] in {move.uci() for move in chess.Board().legal_moves} for item in result["candidates"])
