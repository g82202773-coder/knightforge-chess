import chess
import pytest

from knightforge_engine.full_game import FullGame


def test_new_game_starts_from_standard_position_with_20_legal_moves():
    game = FullGame()
    state = game.state()
    assert state["fen"] == chess.STARTING_FEN
    assert state["turn"] == "white"
    assert len(state["legal_moves_uci"]) == 20
    assert state["game_over"] is False


def test_moves_are_legal_and_history_can_be_undone():
    game = FullGame()
    assert game.play("e2e4")["played"] == "e4"
    assert game.play("e7e5")["played"] == "e5"
    assert len(game.state()["move_history"]) == 2
    state = game.undo()
    assert state["turn"] == "black"
    assert len(state["move_history"]) == 1


def test_illegal_moves_are_rejected_without_changing_position():
    game = FullGame()
    before = game.state()["fen"]
    with pytest.raises(ValueError, match="not legal"):
        game.play("e2e5")
    assert game.state()["fen"] == before


def test_pawn_captures_diagonally_and_not_forward():
    game = FullGame()
    for move in ("e2e4", "d7d5"):
        game.play(move)
    legal = game.state()["legal_moves_uci"]
    assert "e4d5" in legal
    assert "e4e5" in legal


def test_castling_en_passant_and_promotion_are_legal():
    castle = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    game = FullGame()
    game.board = castle
    assert "e1g1" in game.state()["legal_moves_uci"]
    assert "e1c1" in game.state()["legal_moves_uci"]

    ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    game.board = ep
    assert "e5d6" in game.state()["legal_moves_uci"]

    promotion = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    game.board = promotion
    assert {"a7a8q", "a7a8r", "a7a8b", "a7a8n"}.issubset(
        set(game.state()["legal_moves_uci"])
    )


def test_checkmate_ends_game_and_blocks_more_moves():
    game = FullGame()
    for move in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.play(move)
    state = game.state()
    assert state["checkmate"] is True
    assert state["game_over"] is True
    assert state["result"] == "0-1"
    with pytest.raises(ValueError, match="game is over"):
        game.play("e2e4")


def test_restart_returns_to_initial_position():
    game = FullGame()
    game.play("e2e4")
    state = game.restart()
    assert state["fen"] == chess.STARTING_FEN
    assert state["move_history"] == []
