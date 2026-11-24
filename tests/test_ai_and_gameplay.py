"""Tests for 7-tier ChessAIOpponent, FullChessMatch, ChessClock, and PGN I/O."""
import chess
import pytest

from knightforge_engine.ai_opponent import DIFFICULTY_PROFILES, ChessAIOpponent
from knightforge_engine.game_manager import ChessClock, FullChessMatch


def test_ai_opponent_all_seven_difficulties_return_legal_moves():
    ai = ChessAIOpponent(stockfish_path=None)
    board = chess.Board()
    for diff in DIFFICULTY_PROFILES:
        decision = ai.choose_move(board, difficulty=diff, seed=42)
        mv = chess.Move.from_uci(decision.uci)
        assert mv in board.legal_moves
        assert decision.engine_source == "knightforge-builtin"


def test_ai_finds_immediate_checkmate():
    ai = ChessAIOpponent(stockfish_path=None)
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")
    decision = ai.choose_move(board, difficulty="expert")
    assert decision.uci == "d1d8"
    assert decision.mate_in == 1


def test_complete_local_pvp_game_to_checkmate_and_pgn_roundtrip():
    match = FullChessMatch(mode="local_pvp", time_control="unlimited")
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        match.submit_move(uci)
    assert match.is_over
    assert match.termination_reason == "checkmate"
    assert match.winner == "black"

    pgn = match.export_pgn()
    assert "0-1" in pgn
    imported = FullChessMatch.from_pgn(pgn)
    assert imported.is_over
    assert imported.winner == "black"


def test_chess_clock_increment_pause_and_timeout():
    clock = ChessClock(base_seconds=10.0, increment_seconds=2.0)
    clock.start_turn("white", now=100.0)
    assert clock.commit_move("white", now=103.0) is None
    assert clock.white_remaining == 9.0  # 10 - 3 + 2
    assert clock.active_side == "black"

    assert clock.toggle_pause(now=105.0) is True
    assert clock.black_remaining == 8.0
    assert clock.toggle_pause(now=200.0) is False  # paused time does not count
    assert clock.check_timeout(now=209.0) == "black"


def test_online_pvp_invite_and_turn_token_enforcement():
    match = FullChessMatch(mode="online_pvp", time_control="blitz_5_0")
    assert match.invite_code is not None
    with pytest.raises(RuntimeError, match="Waiting for opponent"):
        match.submit_move("e2e4", player_token=match.white_token)

    color, black_token = match.join_online()
    assert color == "black"
    with pytest.raises(RuntimeError, match="not your turn"):
        match.submit_move("e2e4", player_token=black_token)

    match.submit_move("e2e4", player_token=match.white_token)
    match.submit_move("e7e5", player_token=black_token)
    assert match.moves_san == ["e4", "e5"]


def test_draw_offer_and_threefold_repetition_claim():
    match = FullChessMatch(mode="local_pvp", time_control="unlimited")
    for uci in ("g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"):
        match.submit_move(uci)
    msg = match.handle_draw_action("claim")
    assert "threefold" in msg.lower()
    assert match.is_over and match.winner is None


def test_correspondence_time_control_and_deterministic_ai():
    match = FullChessMatch(mode="online_pvp", time_control="correspondence")
    assert match.clock.enabled is False
    ai = ChessAIOpponent(stockfish_path=None)
    board = chess.Board()
    first = ai.choose_move(board, difficulty="beginner")
    second = ai.choose_move(board, difficulty="beginner")
    assert first.uci == second.uci


def test_fen_history_and_material_summary_track_captures_and_undo():
    match = FullChessMatch(mode="local_pvp", time_control="unlimited")
    assert len(match.fen_history) == 1
    match.submit_move("e2e4")
    match.submit_move("d7d5")
    match.submit_move("e4d5")
    state = match.state_dict()
    assert len(state["fen_history"]) == 4
    assert state["material"]["white_advantage"] == 1
    assert state["material"]["captured_by_white"] == ["p"]

    match.undo()
    state_after_undo = match.state_dict()
    assert len(state_after_undo["fen_history"]) == 3
    assert state_after_undo["material"]["white_advantage"] == 0
