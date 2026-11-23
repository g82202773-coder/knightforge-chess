"""Rules-validated tactical puzzle sessions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import chess

TacticsMode = Literal["practice", "mastery"]


@dataclass(frozen=True)
class TacticalPuzzle:
    puzzle_id: str
    title: str
    theme: str
    difficulty: str
    fen: str
    solution_uci: str
    explanation: str
    hints: tuple[str, str, str]


PUZZLES: tuple[TacticalPuzzle, ...] = (
    TacticalPuzzle(
        "queen-mate-f8", "Queen’s finishing move", "checkmate", "beginner",
        "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1", "f7f8",
        "The queen checks along the eighth rank. The white king covers g7 while the queen controls g8 and h7, leaving no legal escape.",
        ("Look for a forcing check.", "Give check along the back rank.", "Move the queen from f7 to f8."),
    ),
    TacticalPuzzle(
        "queen-mate-g7", "Queen and king coordination", "checkmate", "beginner",
        "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", "g6g7",
        "The queen checks on g7. The white king protects the queen and the queen controls the enemy king’s escape squares.",
        ("Look for a forcing check.", "The queen can give check next to the enemy king.", "Move the queen from g6 to g7."),
    ),
    TacticalPuzzle(
        "queen-mate-b7", "Box in the cornered king", "checkmate", "beginner",
        "k7/8/1QK5/8/8/8/8/8 w - - 0 1", "b6b7",
        "The queen checks on b7, protected by the white king. The queen controls a7 and b8, leaving no legal escape.",
        ("Look for a forcing check.", "Place the queen next to the cornered king, protected by your king.", "Move the queen from b6 to b7."),
    ),
)


@dataclass
class TacticsSession:
    puzzle: TacticalPuzzle
    mode: TacticsMode = "practice"
    board: chess.Board = field(init=False)
    attempts: int = 0
    solved: bool = False
    hint_level: int = 0

    def __post_init__(self) -> None:
        if self.mode not in {"practice", "mastery"}:
            raise ValueError("mode must be practice or mastery.")
        self.board = chess.Board(self.puzzle.fen)
        if not self.board.is_valid():
            raise ValueError(f"Invalid puzzle position: {self.puzzle.puzzle_id}")
        move = chess.Move.from_uci(self.puzzle.solution_uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal puzzle solution: {self.puzzle.puzzle_id}")
        probe = self.board.copy()
        probe.push(move)
        if not probe.is_checkmate():
            raise ValueError(f"Puzzle solution is not checkmate: {self.puzzle.puzzle_id}")

    def state(self) -> dict:
        reveal = self.mode == "practice" and self.hint_level == 3
        return {
            "puzzle_id": self.puzzle.puzzle_id,
            "title": self.puzzle.title,
            "theme": self.puzzle.theme,
            "difficulty": self.puzzle.difficulty,
            "mode": self.mode,
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn else "black",
            "legal_moves_uci": sorted(move.uci() for move in self.board.legal_moves),
            "prompt": "Puzzle solved!" if self.solved else "Find the strongest tactical move.",
            "hint": self.puzzle.hints[self.hint_level - 1] if self.hint_level else None,
            "hint_level": self.hint_level,
            "hints_available": not self.solved and self.mode == "practice" and self.hint_level < 3,
            "expected_move": self.puzzle.solution_uci if reveal else None,
            "explanation": self.puzzle.explanation if self.solved else None,
            "solved": self.solved,
            "progress": {
                "attempts": self.attempts,
                "solved": int(self.solved),
                "accuracy_percent": round(100 / self.attempts) if self.solved and self.attempts else 0,
            },
        }

    def submit(self, uci: str) -> dict:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci}") from exc
        if self.solved:
            raise RuntimeError("This puzzle is already solved.")
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move in current position: {uci}")
        self.attempts += 1
        if move.uci() != self.puzzle.solution_uci:
            return {"correct": False, "applied": False, "message": "Legal move, but it misses the tactic. Look for a forcing move.", "state": self.state()}
        san = self.board.san(move)
        self.board.push(move)
        self.solved = True
        return {"correct": True, "applied": True, "san": san, "message": "Correct! Checkmate.", "state": self.state()}

    def reveal_hint(self, level: int) -> dict:
        if self.mode != "practice":
            raise PermissionError("Hints are disabled in Mastery mode.")
        if self.solved:
            raise RuntimeError("This puzzle is already solved.")
        if level != self.hint_level + 1 or not 1 <= level <= 3:
            raise ValueError("Reveal hints one level at a time, from 1 to 3.")
        self.hint_level = level
        return self.state()

    def restart(self) -> dict:
        self.board = chess.Board(self.puzzle.fen)
        self.attempts = 0
        self.solved = False
        self.hint_level = 0
        return self.state()
