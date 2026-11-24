"""Tests for post-game PGN analysis and grounded AI Chess Coach."""
from pathlib import Path

import chess
import pytest

from knightforge_engine.game_analyzer import ChessCoachAssistant, analyze_pgn_game
from knightforge_engine.opening_repository import OpeningRepository


def test_analyze_pgn_game_returns_accuracy_classifications_and_eval_graph():
    pgn = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. d3 Nf6 *"
    report = analyze_pgn_game(pgn)
    assert report["evaluation_source"] in {"stockfish", "knightforge-builtin"}
    assert 0.0 <= report["white_accuracy"] <= 100.0
    assert 0.0 <= report["black_accuracy"] <= 100.0
    assert len(report["moves"]) == 8
    assert len(report["eval_graph"]) == 9


def test_analyze_pgn_rejects_empty_game():
    with pytest.raises(ValueError):
        analyze_pgn_game("")


def test_coach_assistant_grounds_answers_in_real_board_state(tmp_path: Path):
    repo = OpeningRepository.load(tmp_path / "openings.json")
    coach = ChessCoachAssistant(repo)
    advice = coach.advise(
        "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        question="What tactical threat is on the board?",
        player_level="beginner",
    )
    assert advice["turn"] == "white"
    assert advice["candidates"][0]["uci"] == "d1d8"
    assert "Rd8#" in advice["answer"] or any(t["san"] == "Rd8#" for t in advice["tactics"])


def test_coach_rejects_invalid_fen(tmp_path: Path):
    repo = OpeningRepository.load(tmp_path / "openings.json")
    coach = ChessCoachAssistant(repo)
    with pytest.raises(ValueError):
        coach.advise("invalid-fen")
