"""Tests for structured position and legal-move inspection."""

import pytest

from knightforge_engine import ChessGame, PositionInspector


def test_initial_board_squares_and_piece_names():
    inspector = PositionInspector(ChessGame())
    assert inspector.square("e2").piece == "P"
    assert inspector.square("e2").piece_name == "pawn"
    assert inspector.square("e2").color == "white"
    assert inspector.square("e4").piece is None
    assert inspector.turn == "white"


def test_legal_moves_from_pawn_square_include_san_and_uci():
    options = PositionInspector(ChessGame()).legal_moves_from("e2")
    assert {(move.san, move.uci, move.to_square) for move in options} == {
        ("e3", "e2e3", "e3"), ("e4", "e2e4", "e4")
    }


def test_knight_legal_destinations_are_rules_backed():
    options = PositionInspector(ChessGame()).legal_moves_from("g1")
    assert {move.to_square for move in options} == {"f3", "h3"}
    assert {move.san for move in options} == {"Nf3", "Nh3"}


def test_capture_metadata():
    game = ChessGame()
    for move in ("e4", "d5", "exd5", "Qxd5"):
        game.push_san(move)
    options = PositionInspector(game).legal_moves_from("d8")
    queen_capture = next(move for move in options if move.to_square == "d5")
    assert queen_capture.is_capture
    assert queen_capture.captured_piece == "pawn"


def test_invalid_square_is_rejected():
    with pytest.raises(ValueError, match="Invalid chess square"):
        PositionInspector(ChessGame()).square("z9")


def test_inspector_does_not_mutate_game():
    game = ChessGame()
    before = game.fen
    PositionInspector(game).legal_moves_from("e2")
    assert game.fen == before
