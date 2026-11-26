"""Tests for 5-level Curriculum, 15 Puzzles, and SQLite Accounts & Progress."""
from pathlib import Path

import pytest

from knightforge_engine.curriculum import CurriculumCatalog
from knightforge_engine.puzzles import PuzzleCatalog, PuzzleSession, compute_elo_delta
from knightforge_engine.storage import ProgressStore


def test_five_level_curriculum_covers_all_academies():
    catalog = CurriculumCatalog()
    assert len(catalog.all()) >= 20
    for cat in ("rules", "opening", "gambit", "strategy", "middlegame", "endgame"):
        assert len(catalog.filter(category=cat)) >= 1
    for level in (1, 2, 3, 4, 5):
        assert len(catalog.filter(level=level)) >= 1


def test_puzzle_mate_in_three_philidors_legacy_and_rating():
    catalog = PuzzleCatalog()
    assert len(catalog.all()) >= 15
    assert catalog.daily() is not None
    puz = catalog.get("puz-philidor-legacy-15")
    assert puz is not None
    session = PuzzleSession(puz)

    r1 = session.submit_uci("f7h6")
    assert r1.correct and r1.opponent_reply_uci == "g8h8"
    r2 = session.submit_uci("b3g8")
    assert r2.correct and r2.opponent_reply_uci == "f8g8"
    r3 = session.submit_uci("h6f7")
    assert r3.correct and r3.solved
    assert compute_elo_delta(1000, puz.rating, True) > 0


def test_accounts_register_login_notes_and_progress(tmp_path: Path):
    db = ProgressStore(tmp_path / "kf.db")
    reg = db.register_user("mustafa", "securepass123")
    uid = reg["user_id"]
    assert db.resolve_user_id(reg["token"]) == uid

    logged = db.login_user("mustafa", "securepass123")
    assert logged["user_id"] == uid
    with pytest.raises(ValueError, match="Invalid"):
        db.login_user("mustafa", "wrongpass")

    db.update_notes(uid, "Review Lucena bridge and Sicilian Najdorf.")
    db.record_lesson_completion("open-game-first-five", "mastery", user_id=uid)
    db.record_puzzle_attempt("puz-back-rank-01", True, 0, 0, rating_delta=12, user_id=uid)
    db.record_saved_game(
        mode="human_vs_ai",
        player_color="white",
        difficulty="club",
        result="win",
        termination="checkmate",
        plies=28,
        pgn="1. e4 e5 *",
        user_id=uid,
    )

    summary = db.summary(
        ("open-game-first-five",), ("puz-back-rank-01",), user_id=uid
    )
    assert summary["profile"]["username"] == "mustafa"
    assert summary["profile"]["puzzle_rating"] == 1012
    assert "First Victory" in summary["achievements"]
    assert "Lucena" in summary["profile"]["notes"]
    db.close()


def test_password_recovery_resets_password_and_invalidates_old_tokens(tmp_path: Path):
    db = ProgressStore(tmp_path / "kf_recover.db")
    reg = db.register_user("knightplayer", "oldpass123")
    old_token = reg["token"]
    assert db.resolve_user_id(old_token) == reg["user_id"]

    rec_token = db.create_recovery_token("knightplayer")
    reset_user = db.reset_password_with_token(rec_token, "newpass456")
    assert reset_user == "knightplayer"
    assert db.resolve_user_id(old_token) == 0

    with pytest.raises(ValueError, match="Invalid"):
        db.login_user("knightplayer", "oldpass123")
    logged = db.login_user("knightplayer", "newpass456")
    assert logged["user_id"] == reg["user_id"]
    db.close()
