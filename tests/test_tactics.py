"""Tests for the rules-backed tactical candidate scanner."""

from knightforge_engine import ChessGame, TacticalScanner


def test_finds_legal_checking_moves_and_mate_in_one():
    game = ChessGame("7k/6pp/5KQ1/8/8/8/8/8 w - - 0 1")
    scan = TacticalScanner(game).scan()
    mate = next(candidate for candidate in scan.candidates if candidate.san == "Qg7#")
    assert mate.is_checkmate
    assert mate.gives_check
    assert mate.motifs[:2] == ("checkmate", "check")


def test_finds_capture_and_reports_heuristic_priority():
    game = ChessGame()
    game.push_san("e4")
    game.push_san("d5")
    scan = TacticalScanner(game).scan()
    capture = next(candidate for candidate in scan.candidates if candidate.san == "exd5")
    assert "capture" in capture.motifs
    assert capture.captured_piece == "pawn"
    assert capture.capture_priority_cp == 0


def test_en_passant_capture_is_detected():
    game = ChessGame()
    for move in ("e4", "a6", "e5", "d5"):
        game.push_san(move)
    scan = TacticalScanner(game).scan()
    capture = next(candidate for candidate in scan.candidates if candidate.san == "exd6")
    assert capture.captured_piece == "pawn"
    assert "capture" in capture.motifs


def test_scanner_does_not_mutate_game():
    game = ChessGame()
    game.push_san("e4")
    before = game.fen
    TacticalScanner(game).scan()
    assert game.fen == before


def test_quiet_position_returns_no_forcing_candidates():
    scan = TacticalScanner(ChessGame()).scan()
    assert scan.candidates == ()
