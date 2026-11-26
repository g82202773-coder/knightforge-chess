"""SQLite-backed user accounts, ratings, achievements, games, and progress store.

Uses stdlib sqlite3 + PBKDF2-HMAC-SHA256 password hashing and secure random
bearer tokens. Designed behind a clean class boundary so PostgreSQL can drop
in when scaling to multi-worker cloud deployments.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_password(password: str, salt: str | None = None) -> str:
    used_salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), used_salt.encode("utf-8"), 120_000)
    return f"{used_salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    if "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    candidate = _hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected)


class ProgressStore:
    """Thread-safe SQLite database for accounts, lessons, puzzles, and saved games."""

    def __init__(self, db_path: str | Path = "data/knightforge.db") -> None:
        self.db_path = str(db_path)
        self._lock = threading.RLock()
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    chess_rating INTEGER NOT NULL DEFAULT 1000,
                    puzzle_rating INTEGER NOT NULL DEFAULT 1000,
                    daily_streak INTEGER NOT NULL DEFAULT 1,
                    last_active_date TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recovery_tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    user_id INTEGER NOT NULL DEFAULT 0,
                    lesson_id TEXT NOT NULL,
                    best_mode TEXT NOT NULL,
                    completions INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, lesson_id)
                );
                CREATE TABLE IF NOT EXISTS puzzle_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    puzzle_id TEXT NOT NULL,
                    solved INTEGER NOT NULL,
                    hints_used INTEGER NOT NULL,
                    mistakes INTEGER NOT NULL,
                    rating_delta INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS saved_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    mode TEXT NOT NULL,
                    player_color TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    result TEXT NOT NULL,
                    termination TEXT NOT NULL,
                    plies INTEGER NOT NULL,
                    pgn TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            # Ensure default guest profile (id=0) exists so zero-login play works seamlessly.
            guest = self._conn.execute("SELECT id FROM users WHERE id = 0").fetchone()
            if guest is None:
                today = date.today().isoformat()
                self._conn.execute(
                    "INSERT INTO users (id, username, password_hash, last_active_date, created_at) "
                    "VALUES (0, 'guest', '', ?, ?)",
                    (today, _utc_now()),
                )

    def _touch_streak(self, user_id: int) -> None:
        today = date.today()
        row = self._conn.execute(
            "SELECT daily_streak, last_active_date FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return
        last_str = str(row["last_active_date"])
        try:
            last_day = date.fromisoformat(last_str)
        except ValueError:
            last_day = today
        delta = (today - last_day).days
        if delta == 1:
            streak = int(row["daily_streak"]) + 1
        elif delta > 1:
            streak = 1
        else:
            streak = int(row["daily_streak"])
        self._conn.execute(
            "UPDATE users SET daily_streak = ?, last_active_date = ? WHERE id = ?",
            (streak, today.isoformat(), user_id),
        )

    # ---------------- Accounts ----------------
    def register_user(self, username: str, password: str) -> dict[str, Any]:
        clean = username.strip()
        if len(clean) < 3 or len(clean) > 32:
            raise ValueError("Username must be between 3 and 32 characters.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        pw_hash = _hash_password(password)
        token = secrets.token_urlsafe(24)
        today = date.today().isoformat()
        now = _utc_now()
        with self._lock, self._conn:
            try:
                cur = self._conn.execute(
                    "INSERT INTO users (username, password_hash, last_active_date, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (clean, pw_hash, today, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Username already exists.") from exc
            user_id = int(cur.lastrowid)
            self._conn.execute(
                "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, now),
            )
        return {"user_id": user_id, "username": clean, "token": token}

    def login_user(self, username: str, password: str) -> dict[str, Any]:
        clean = username.strip()
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ? AND id > 0",
                (clean,),
            ).fetchone()
            if row is None or not _verify_password(password, str(row["password_hash"])):
                raise ValueError("Invalid username or password.")
            token = secrets.token_urlsafe(24)
            user_id = int(row["id"])
            self._conn.execute(
                "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, _utc_now()),
            )
            self._touch_streak(user_id)
        return {"user_id": user_id, "username": str(row["username"]), "token": token}

    def create_recovery_token(self, username: str) -> str:
        """Issue a one-time password recovery token for an existing account."""
        clean = username.strip()
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT id FROM users WHERE username = ? AND id > 0", (clean,)
            ).fetchone()
            if row is None:
                raise ValueError("Account not found.")
            token = secrets.token_urlsafe(18)
            self._conn.execute(
                "DELETE FROM recovery_tokens WHERE user_id = ?", (int(row["id"]),)
            )
            self._conn.execute(
                "INSERT INTO recovery_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, int(row["id"]), _utc_now()),
            )
            return token

    def reset_password_with_token(self, recovery_token: str, new_password: str) -> str:
        """Verify recovery token, update password hash, and invalidate old tokens."""
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters.")
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT user_id FROM recovery_tokens WHERE token = ?",
                (recovery_token.strip(),),
            ).fetchone()
            if row is None:
                raise ValueError("Invalid or expired recovery token.")
            uid = int(row["user_id"])
            self._conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (_hash_password(new_password), uid),
            )
            self._conn.execute("DELETE FROM recovery_tokens WHERE user_id = ?", (uid,))
            self._conn.execute("DELETE FROM auth_tokens WHERE user_id = ?", (uid,))
            user_row = self._conn.execute(
                "SELECT username FROM users WHERE id = ?", (uid,)
            ).fetchone()
            return str(user_row["username"]) if user_row else ""

    def resolve_user_id(self, token: str | None) -> int:
        if not token:
            return 0
        with self._lock:
            row = self._conn.execute(
                "SELECT user_id FROM auth_tokens WHERE token = ?", (token,)
            ).fetchone()
            return int(row["user_id"]) if row is not None else 0

    def update_notes(self, user_id: int, notes: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET notes = ? WHERE id = ?",
                (notes[:4000], user_id),
            )

    def get_profile(self, user_id: int) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, username, chess_rating, puzzle_rating, daily_streak, notes, created_at "
                "FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return {
                "user_id": 0,
                "username": "guest",
                "chess_rating": 1000,
                "puzzle_rating": 1000,
                "daily_streak": 1,
                "notes": "",
            }
        return {
            "user_id": int(row["id"]),
            "username": str(row["username"]),
            "chess_rating": int(row["chess_rating"]),
            "puzzle_rating": int(row["puzzle_rating"]),
            "daily_streak": int(row["daily_streak"]),
            "notes": str(row["notes"]),
            "created_at": str(row["created_at"]),
        }

    # ---------------- Learning & Game Records ----------------
    def record_lesson_completion(self, lesson_id: str, mode: str, user_id: int = 0) -> None:
        mode_rank = {"guided": 1, "practice": 2, "mastery": 3}
        now = _utc_now()
        with self._lock, self._conn:
            self._touch_streak(user_id)
            row = self._conn.execute(
                "SELECT best_mode, completions FROM lesson_progress "
                "WHERE user_id = ? AND lesson_id = ?",
                (user_id, lesson_id),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO lesson_progress "
                    "(user_id, lesson_id, best_mode, completions, updated_at) "
                    "VALUES (?, ?, ?, 1, ?)",
                    (user_id, lesson_id, mode, now),
                )
            else:
                best = (
                    mode
                    if mode_rank.get(mode, 0) >= mode_rank.get(str(row["best_mode"]), 0)
                    else str(row["best_mode"])
                )
                self._conn.execute(
                    "UPDATE lesson_progress SET best_mode = ?, completions = ?, updated_at = ? "
                    "WHERE user_id = ? AND lesson_id = ?",
                    (best, int(row["completions"]) + 1, now, user_id, lesson_id),
                )

    def record_puzzle_attempt(
        self,
        puzzle_id: str,
        solved: bool,
        hints_used: int,
        mistakes: int,
        rating_delta: int = 0,
        user_id: int = 0,
    ) -> int:
        with self._lock, self._conn:
            self._touch_streak(user_id)
            self._conn.execute(
                "INSERT INTO puzzle_attempts "
                "(user_id, puzzle_id, solved, hints_used, mistakes, rating_delta, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id, puzzle_id, int(solved), int(hints_used),
                    int(mistakes), rating_delta, _utc_now(),
                ),
            )
            self._conn.execute(
                "UPDATE users SET puzzle_rating = MAX(400, puzzle_rating + ?) WHERE id = ?",
                (rating_delta, user_id),
            )
            row = self._conn.execute(
                "SELECT puzzle_rating FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return int(row["puzzle_rating"]) if row else 1000

    def record_saved_game(
        self,
        *,
        mode: str,
        player_color: str,
        difficulty: str,
        result: str,
        termination: str,
        plies: int,
        pgn: str,
        user_id: int = 0,
    ) -> None:
        delta = 14 if result == "win" else (-10 if result == "loss" else 2)
        with self._lock, self._conn:
            self._touch_streak(user_id)
            self._conn.execute(
                "INSERT INTO saved_games "
                "(user_id, mode, player_color, difficulty, result, "
                "termination, plies, pgn, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id, mode, player_color, difficulty, result,
                    termination, int(plies), pgn, _utc_now(),
                ),
            )
            if mode == "human_vs_ai":
                self._conn.execute(
                    "UPDATE users SET chess_rating = MAX(400, chess_rating + ?) WHERE id = ?",
                    (delta, user_id),
                )

    def completed_lesson_ids(self, user_id: int = 0) -> set[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT lesson_id FROM lesson_progress WHERE user_id = ?", (user_id,)
            ).fetchall()
            return {str(row["lesson_id"]) for row in rows}

    def mistake_puzzle_ids(self, user_id: int = 0) -> set[str]:
        """Return puzzle IDs where the learner made mistakes (for spaced review)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT puzzle_id FROM puzzle_attempts "
                "WHERE user_id = ? AND mistakes > 0",
                (user_id,),
            ).fetchall()
            return {str(row["puzzle_id"]) for row in rows}

    def solved_puzzle_ids(self, user_id: int = 0) -> set[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT puzzle_id FROM puzzle_attempts WHERE user_id = ? AND solved = 1",
                (user_id,),
            ).fetchall()
            return {str(row["puzzle_id"]) for row in rows}

    def summary(
        self,
        all_lesson_ids: tuple[str, ...],
        all_puzzle_ids: tuple[str, ...],
        user_id: int = 0,
    ) -> dict[str, Any]:
        profile = self.get_profile(user_id)
        with self._lock:
            lessons = [
                dict(row)
                for row in self._conn.execute(
                    "SELECT lesson_id, best_mode, completions, updated_at "
                    "FROM lesson_progress WHERE user_id = ? ORDER BY updated_at DESC",
                    (user_id,),
                ).fetchall()
            ]
            puz_row = self._conn.execute(
                "SELECT COUNT(*) AS attempts, COALESCE(SUM(solved), 0) AS solved_count "
                "FROM puzzle_attempts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            solved_unique = self.solved_puzzle_ids(user_id)
            games = [
                dict(row)
                for row in self._conn.execute(
                    "SELECT id, mode, player_color, difficulty, result, "
                    "termination, plies, pgn, created_at "
                    "FROM saved_games WHERE user_id = ? ORDER BY id DESC LIMIT 15",
                    (user_id,),
                ).fetchall()
            ]
            record = {"win": 0, "loss": 0, "draw": 0}
            for row in self._conn.execute(
                "SELECT result, COUNT(*) AS cnt FROM saved_games WHERE user_id = ? GROUP BY result",
                (user_id,),
            ).fetchall():
                if row["result"] in record:
                    record[row["result"]] = int(row["cnt"])

        completed_ids = {item["lesson_id"] for item in lessons}
        attempts = int(puz_row["attempts"]) if puz_row else 0
        solved_count = int(puz_row["solved_count"]) if puz_row else 0
        accuracy = round((solved_count / attempts) * 100, 1) if attempts else 0.0

        achievements: list[str] = []
        if len(completed_ids) >= 1:
            achievements.append("First Lesson Completed")
        if len(completed_ids) >= 5:
            achievements.append("Academy Scholar (5+ Lessons)")
        if len(solved_unique) >= 1:
            achievements.append("Tactical Eye (First Puzzle)")
        if len(solved_unique) >= 10:
            achievements.append("Tactician (10+ Puzzles)")
        if record["win"] >= 1:
            achievements.append("First Victory")
        if profile["daily_streak"] >= 3:
            achievements.append("3-Day Training Streak")

        next_lesson = next((lid for lid in all_lesson_ids if lid not in completed_ids), None)
        next_puzzle = next((pid for pid in all_puzzle_ids if pid not in solved_unique), None)
        if next_lesson:
            rec_next = {
                "kind": "lesson",
                "target_id": next_lesson,
                "reason": "Continue your structured 5-level Academy path.",
            }
        elif next_puzzle:
            rec_next = {
                "kind": "puzzle",
                "target_id": next_puzzle,
                "reason": "Build tactical vision with your next unsolved puzzle.",
            }
        else:
            rec_next = {
                "kind": "play",
                "target_id": "advanced",
                "reason": "Challenge KnightForge AI at Advanced or Master strength.",
            }

        return {
            "profile": profile,
            "lessons_completed": len(completed_ids),
            "lessons_total": len(all_lesson_ids),
            "lesson_records": lessons,
            "puzzles_solved": len(solved_unique),
            "puzzles_total": len(all_puzzle_ids),
            "puzzle_attempts": attempts,
            "puzzle_accuracy_pct": accuracy,
            "game_record": record,
            "recent_games": games,
            "achievements": achievements,
            "recommended_next": rec_next,
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
