"""Curated, rules-validated tactics & endgame puzzle trainer for KnightForge."""
from __future__ import annotations

import datetime
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import chess

from .core import ChessGame

PuzzleDifficulty = Literal["beginner", "intermediate", "advanced"]


@dataclass(frozen=True, slots=True)
class Puzzle:
    """One rules-validated chess puzzle with provenance, rating, and solution."""

    puzzle_id: str
    title: str
    fen: str
    solution_uci: tuple[str, ...]
    themes: tuple[str, ...]
    difficulty: PuzzleDifficulty
    rating: int
    explanation: str
    source_name: str = "KnightForge Curated Tactics"
    license_name: str = "Original editorial content"

    def validate(self) -> None:
        if not self.puzzle_id.strip() or not self.title.strip():
            raise ValueError("puzzle_id and title are required.")
        if not self.solution_uci:
            raise ValueError("Puzzle must contain at least one solution move.")
        board = chess.Board(self.fen)
        if not board.is_valid():
            raise ValueError(f"Invalid FEN in puzzle {self.puzzle_id}")
        for index, uci in enumerate(self.solution_uci, start=1):
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise ValueError(
                    f"Illegal move {uci} at ply {index} in puzzle {self.puzzle_id}."
                )
            board.push(move)

    @property
    def solver_color(self) -> str:
        return "white" if chess.Board(self.fen).turn == chess.WHITE else "black"

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "puzzle_id": self.puzzle_id,
            "title": self.title,
            "fen": self.fen,
            "solver_color": self.solver_color,
            "themes": list(self.themes),
            "difficulty": self.difficulty,
            "rating": self.rating,
            "moves_to_solve": (len(self.solution_uci) + 1) // 2,
            "source_name": self.source_name,
            "license_name": self.license_name,
        }


@dataclass(frozen=True, slots=True)
class PuzzleHint:
    """One progressive hint for the current solver ply."""

    level: int
    text: str
    arrow_from: str | None = None
    arrow_to: str | None = None


@dataclass(frozen=True, slots=True)
class PuzzleAttemptOutcome:
    """Result of submitting a move inside a PuzzleSession."""

    accepted: bool
    correct: bool
    solved: bool
    played_san: str | None
    opponent_reply_san: str | None
    opponent_reply_uci: str | None
    message: str
    fen: str
    turn: str
    legal_moves_uci: tuple[str, ...]
    hints_used: int
    mistakes: int


def compute_elo_delta(player_rating: int, puzzle_rating: int, solved_cleanly: bool) -> int:
    """Standard Elo rating adjustment for a puzzle attempt."""
    expected = 1.0 / (1.0 + 10.0 ** ((puzzle_rating - player_rating) / 400.0))
    actual = 1.0 if solved_cleanly else 0.0
    return round(24 * (actual - expected))


class PuzzleSession:
    """Interactive, server-authoritative session for solving one Puzzle."""

    def __init__(self, puzzle: Puzzle) -> None:
        puzzle.validate()
        self.puzzle = puzzle
        self.game = ChessGame(puzzle.fen)
        self._ply = 0
        self.hints_used = 0
        self.mistakes = 0
        self.solved = False

    def state_dict(self) -> dict[str, object]:
        return {
            "puzzle_id": self.puzzle.puzzle_id,
            "title": self.puzzle.title,
            "themes": list(self.puzzle.themes),
            "difficulty": self.puzzle.difficulty,
            "rating": self.puzzle.rating,
            "solver_color": self.puzzle.solver_color,
            "fen": self.game.fen,
            "turn": self.game.turn,
            "game_status": self.game.status.value,
            "legal_moves_uci": [] if self.solved else list(self.game.legal_moves),
            "solved": self.solved,
            "hints_used": self.hints_used,
            "mistakes": self.mistakes,
            "explanation": self.puzzle.explanation if self.solved else "",
        }

    def reveal_hint(self, level: int) -> PuzzleHint:
        if not 1 <= level <= 3:
            raise ValueError("Puzzle hint level must be between 1 and 3.")
        if self.solved or self._ply >= len(self.puzzle.solution_uci):
            raise RuntimeError("Puzzle is already solved.")
        self.hints_used = max(self.hints_used, level)
        expected = chess.Move.from_uci(self.puzzle.solution_uci[self._ply])
        board = self.game.copy_board()
        piece = board.piece_at(expected.from_square)
        piece_name = chess.piece_name(piece.piece_type) if piece else "piece"
        source = chess.square_name(expected.from_square)
        target = chess.square_name(expected.to_square)
        if level == 1:
            theme_text = ", ".join(self.puzzle.themes)
            return PuzzleHint(1, f"Look for a {theme_text} tactic with your {piece_name}.")
        if level == 2:
            return PuzzleHint(
                2,
                f"Focus on your {piece_name} on {source.upper()}.",
                arrow_from=source,
            )
        return PuzzleHint(
            3,
            f"Move your {piece_name} from {source.upper()} to {target.upper()}.",
            arrow_from=source,
            arrow_to=target,
        )

    def submit_uci(self, uci: str) -> PuzzleAttemptOutcome:
        if self.solved:
            raise RuntimeError("Puzzle is already solved.")
        board = self.game.copy_board()
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci}") from exc
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move in current puzzle position: {uci}")

        expected_uci = self.puzzle.solution_uci[self._ply]
        if move.uci() != expected_uci:
            test_board = board.copy()
            test_board.push(move)
            is_alt_mate = (
                test_board.is_checkmate()
                and self._ply == len(self.puzzle.solution_uci) - 1
            )
            if not is_alt_mate:
                self.mistakes += 1
                return PuzzleAttemptOutcome(
                    accepted=False,
                    correct=False,
                    solved=False,
                    played_san=None,
                    opponent_reply_san=None,
                    opponent_reply_uci=None,
                    message="Legal move, but it misses the tactical solution. Try again.",
                    fen=self.game.fen,
                    turn=self.game.turn,
                    legal_moves_uci=self.game.legal_moves,
                    hints_used=self.hints_used,
                    mistakes=self.mistakes,
                )

        applied = self.game.push_uci(move.uci())
        self._ply += 1

        reply_san: str | None = None
        reply_uci: str | None = None
        if self._ply >= len(self.puzzle.solution_uci) or self.game.status.value == "checkmate":
            self.solved = True
            message = f"Solved! {self.puzzle.explanation}"
        else:
            reply_move = self.puzzle.solution_uci[self._ply]
            reply_res = self.game.push_uci(reply_move)
            reply_san = reply_res.san
            reply_uci = reply_res.uci
            self._ply += 1
            if self._ply >= len(self.puzzle.solution_uci):
                self.solved = True
                message = f"Solved! {self.puzzle.explanation}"
            else:
                message = (
                    f"Great move ({applied.san})! Opponent replied {reply_san}. Finish it."
                )

        return PuzzleAttemptOutcome(
            accepted=True,
            correct=True,
            solved=self.solved,
            played_san=applied.san,
            opponent_reply_san=reply_san,
            opponent_reply_uci=reply_uci,
            message=message,
            fen=self.game.fen,
            turn=self.game.turn,
            legal_moves_uci=() if self.solved else self.game.legal_moves,
            hints_used=self.hints_used,
            mistakes=self.mistakes,
        )


def _default_puzzles() -> tuple[Puzzle, ...]:
    puzzles = (
        Puzzle(
            "puz-back-rank-01", "Back-Rank Knockout",
            "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", ("d1d8",),
            ("mate-in-1", "back-rank"), "beginner", 850,
            "Rd8# delivers an immediate back-rank checkmate.",
        ),
        Puzzle(
            "puz-smothered-02", "Smothered Corner Mate",
            "6rk/6pp/7N/8/8/8/8/6K1 w - - 0 1", ("h6f7",),
            ("mate-in-1", "smothered-mate"), "beginner", 950,
            "Nf7# is a smothered mate; Black's own pieces block every escape.",
        ),
        Puzzle(
            "puz-arabian-03", "Arabian Mate Pattern",
            "7k/8/5N2/8/8/8/6R1/6K1 w - - 0 1", ("g2g8",),
            ("mate-in-1", "checkmate-pattern"), "beginner", 900,
            "Rg8# delivers the Arabian Mate with knight support on f6.",
        ),
        Puzzle(
            "puz-knight-fork-04", "Royal Knight Fork",
            "3qk3/8/8/4N3/8/8/8/4K3 w - - 0 1", ("e5c6",),
            ("fork", "double-attack"), "beginner", 920,
            "Nc6+ forks Black's king on e8 and queen on d8 simultaneously.",
        ),
        Puzzle(
            "puz-pin-win-05", "Pinning the Queen to the King",
            "4k3/4q3/8/8/8/8/8/3R2K1 w - - 0 1", ("d1e1",),
            ("pin", "tactic"), "beginner", 960,
            "Re1 pins Black's queen directly against the king on the e-file.",
        ),
        Puzzle(
            "puz-skewer-06", "Eighth-Rank Rook Skewer",
            "4k2q/8/8/8/8/8/8/R5K1 w - - 0 1", ("a1a8", "e8d7", "a8h8"),
            ("skewer", "endgame"), "intermediate", 1150,
            "Ra8+ skewers the king and queen, winning the queen next move.",
        ),
        Puzzle(
            "puz-mate-in-two-07", "Doubled-Rook Back-Rank Mate",
            "2r1r1k1/5ppp/8/8/8/8/4RPPP/4R1K1 w - - 0 1", ("e2e8", "c8e8", "e1e8"),
            ("mate-in-2", "back-rank", "deflection"), "intermediate", 1220,
            "Rxe8+ forces Rxe8, clearing the way for the second rook to mate.",
        ),
        Puzzle(
            "puz-promotion-08", "Promotion Checkmate",
            "7k/4P3/6K1/8/8/8/8/8 w - - 0 1", ("e7e8q",),
            ("promotion", "mate-in-1", "endgame"), "beginner", 820,
            "e8=Q# promotes to a queen with immediate checkmate.",
        ),
        Puzzle(
            "puz-black-mate-09", "Black Back-Rank Strike",
            "3r2k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1", ("d8d1",),
            ("mate-in-1", "back-rank"), "beginner", 860,
            "Rd1# punishes White's unguarded back rank.",
        ),
        Puzzle(
            "puz-queen-box-10", "Queen & King Box Mate in Two",
            "6k1/8/3Q1K2/8/8/8/8/8 w - - 0 1", ("d6e7", "g8h8", "e7g7"),
            ("mate-in-2", "endgame"), "intermediate", 1100,
            "Qe7 forces the king to h8, and Qg7# finishes the mate.",
        ),
        Puzzle(
            "puz-discovered-11", "Discovered Check Wins the Queen",
            "4k3/8/8/8/2q1B3/8/8/4R1K1 w - - 0 1", ("e4d5",),
            ("discovered-attack", "double-attack"), "intermediate", 1250,
            "Bd5+ unleashes a discovered check from the e1 rook while attacking the queen.",
        ),
        Puzzle(
            "puz-removing-def-12", "Winning the Undefended Queen",
            "6k1/5ppp/8/8/8/2q5/5PPP/2RR2K1 w - - 0 1", ("c1c3",),
            ("removing-defender", "capture"), "beginner", 880,
            "Rxc3 wins the undefended queen immediately.",
        ),
        Puzzle(
            "puz-underpromo-13", "Knight Underpromotion Royal Fork",
            "8/3k1P2/6q1/8/8/8/8/7K w - - 0 1", ("f7f8n",),
            ("promotion", "fork"), "advanced", 1550,
            "f8=N+ underpromotes to a knight, forking Black's king on d7 and queen on g6!",
        ),
        Puzzle(
            "puz-anastasia-14", "Anastasia Queen Sacrifice Mate in Two",
            "7k/4Nppp/8/7Q/8/3R4/8/6K1 w - - 0 1", ("h5h7", "h8h7", "d3h3"),
            ("mate-in-2", "decoy", "attraction"), "advanced", 1480,
            "Qxh7+! forces Kxh7, drawing the king onto the open h-file for Rh3#.",
        ),
        Puzzle(
            "puz-philidor-legacy-15", "Philidor's Legacy Smothered Mate in Three",
            "5rk1/5Npp/8/8/8/1Q6/8/6K1 w - - 0 1",
            ("f7h6", "g8h8", "b3g8", "f8g8", "h6f7"),
            ("mate-in-3", "smothered-mate", "double-attack"), "advanced", 1680,
            "1.Nh6+ Kh8 2.Qg8+! Rxg8 3.Nf7# — the immortal Philidor's Legacy mate in three.",
        ),
    )
    for puzzle in puzzles:
        puzzle.validate()
    return puzzles


def _load_extra_puzzles(path: Path | None = None) -> tuple[Puzzle, ...]:
    """Load pre-validated bulk puzzles from data/puzzles/puzzles_1000.json."""
    target = path or (Path(__file__).resolve().parents[2] / "data/puzzles/puzzles_1000.json")
    if not target.is_file():
        return ()
    raw = json.loads(target.read_text(encoding="utf-8"))
    out: list[Puzzle] = []
    for item in raw.get("puzzles", []):
        out.append(
            Puzzle(
                puzzle_id=str(item["puzzle_id"]),
                title=str(item["title"]),
                fen=str(item["fen"]),
                solution_uci=tuple(item["solution_uci"]),
                themes=tuple(item["themes"]),
                difficulty=item["difficulty"],
                rating=int(item["rating"]),
                explanation=str(item["explanation"]),
                source_name=str(item.get("source_name", "Source not recorded")),
                license_name=str(item.get("license_name", "License not recorded")),
            )
        )
        out[-1].validate()
    return tuple(out)


class PuzzleCatalog:
    """Registry of validated curated puzzles and an optional imported bulk dataset."""

    def __init__(
        self,
        puzzles: tuple[Puzzle, ...] | None = None,
        *,
        include_bulk: bool = True,
    ) -> None:
        if puzzles is not None:
            items = puzzles
            for item in items:
                item.validate()
        else:
            curated = _default_puzzles()
            extra = _load_extra_puzzles() if include_bulk else ()
            items = (*curated, *extra)
        self._by_id: dict[str, Puzzle] = {}
        for item in items:
            if item.puzzle_id in self._by_id:
                raise ValueError(f"Duplicate puzzle_id: {item.puzzle_id}")
            self._by_id[item.puzzle_id] = item

    def all(self) -> tuple[Puzzle, ...]:
        return tuple(self._by_id.values())

    def get(self, puzzle_id: str) -> Puzzle | None:
        return self._by_id.get(puzzle_id)

    def daily(self, day: datetime.date | None = None) -> Puzzle:
        target = day or datetime.date.today()
        items = self.all()
        return items[target.toordinal() % len(items)]

    def filter(
        self,
        *,
        difficulty: str | None = None,
        theme: str | None = None,
        min_rating: int | None = None,
        max_rating: int | None = None,
        only_ids: set[str] | None = None,
    ) -> tuple[Puzzle, ...]:
        items = self.all()
        if only_ids is not None:
            items = tuple(p for p in items if p.puzzle_id in only_ids)
        if difficulty:
            items = tuple(p for p in items if p.difficulty == difficulty)
        if theme:
            t = theme.casefold()
            items = tuple(p for p in items if any(t in th.casefold() for th in p.themes))
        if min_rating is not None:
            items = tuple(p for p in items if p.rating >= min_rating)
        if max_rating is not None:
            items = tuple(p for p in items if p.rating <= max_rating)
        return items

    def random_puzzle(
        self,
        *,
        difficulty: str | None = None,
        theme: str | None = None,
        seed: int | None = None,
    ) -> Puzzle:
        pool = self.filter(difficulty=difficulty, theme=theme) or self.all()
        return random.Random(seed).choice(pool)
