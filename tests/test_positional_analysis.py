"""Tests for explainable positional feature analysis."""
import chess
import pytest

from knightforge_engine.positional_analysis import analyze_position


def test_analyze_initial_position_and_passed_pawn_detection():
    report = analyze_position(chess.STARTING_FEN, ["e2e4", "d2d4"])
    assert len(report["candidates"]) == 2
    fen = "4k3/8/8/4P3/8/8/8/3RK3 w - - 0 1"
    rep2 = analyze_position(fen, ["d1d7"])
    assert "e5" in rep2["position_features"]["white_pawns"]["passed"]
    assert "d" in rep2["position_features"]["white_rooks"]["open_files"]


def test_rejects_invalid_fen():
    with pytest.raises(ValueError, match="Invalid FEN"):
        analyze_position("not-a-fen")
