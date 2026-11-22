import chess
import pytest

from knightforge_engine.core import ChessGame, GameStatus


def _perft(board: chess.Board, depth: int) -> int:
    if depth == 0:
        return 1
    nodes = 0
    for move in board.legal_moves:
        child = board.copy()
        child.push(move)
        nodes += _perft(child, depth - 1)
    return nodes


def test_initial_position_and_basic_move() -> None:
    game = ChessGame()
    assert len(game.legal_moves) == 20
    result = game.push_san("e4")
    assert result.san == "e4"
    assert result.turn == "black"


def test_rejects_illegal_move() -> None:
    game = ChessGame()
    with pytest.raises(ValueError):
        game.push_uci("e2e5")


def test_castling_and_en_passant_are_legal() -> None:
    castle = ChessGame("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert "e1g1" in castle.legal_moves
    assert "e1c1" in castle.legal_moves

    ep = ChessGame()
    for move in ("e4", "a6", "e5", "d5"):
        ep.push_san(move)
    assert "e5d6" in ep.legal_moves


def test_promotion_is_supported() -> None:
    game = ChessGame("7k/P7/8/8/8/8/8/7K w - - 0 1")
    assert "a7a8q" in game.legal_moves
    assert "a7a8n" in game.legal_moves


def test_checkmate_is_detected() -> None:
    game = ChessGame()
    for move in ("f3", "e5", "g4", "Qh4#"):
        result = game.push_san(move)
    assert result.status == GameStatus.CHECKMATE


def test_undo_restores_previous_position() -> None:
    game = ChessGame()
    initial = game.fen
    game.push_san("e4")
    game.undo()
    assert game.fen == initial



def test_initial_position_perft_depths_one_to_three() -> None:
    # Standard reference counts: catches accidental changes in legal move handling.
    board = ChessGame().copy_board()
    assert _perft(board, 1) == 20
    assert _perft(board, 2) == 400
    assert _perft(board, 3) == 8902


def test_castling_through_attacked_square_is_illegal() -> None:
    game = ChessGame("r3k2r/8/8/8/2b5/8/8/R3K2R w KQkq - 0 1")
    assert "e1g1" not in game.legal_moves
    assert "e1c1" in game.legal_moves


def test_en_passant_is_illegal_when_it_exposes_own_king() -> None:
    # The e5 pawn is pinned on the e-file by the black rook.
    game = ChessGame("k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    assert "e5d6" not in game.legal_moves


def test_threefold_repetition_is_not_automatically_adjudicated() -> None:
    game = ChessGame()
    for move in ("Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"):
        game.push_san(move)
    # Threefold is claimable; fivefold is the automatic draw threshold.
    assert game.status == GameStatus.ACTIVE
