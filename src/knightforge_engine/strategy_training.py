"""Curated strategy lessons and positional decision exercises.

This first content batch is editorial teaching material, not engine evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import chess

StrategyMode = Literal["practice", "mastery"]


@dataclass(frozen=True)
class StrategyLesson:
    lesson_id: str
    title: str
    theme: str
    level: str
    principle: str
    why_it_matters: str
    checklist: tuple[str, ...]
    example_plan: str


LESSONS: tuple[StrategyLesson, ...] = (
    StrategyLesson(
        "piece-activity", "Piece activity and development", "development", "beginner",
        "Develop minor pieces toward useful squares, connect the rooks, and improve your least-active piece.",
        "A piece is valuable only when it can influence the position. Active pieces create threats, defend important squares, and make future plans easier.",
        ("Which piece is doing the least?", "Can it move toward the centre without being trapped?", "Will the move help the king castle or connect the rooks?"),
        "A knight on f3 or c3 usually influences central squares more effectively than a knight stuck on the rim."
    ),
    StrategyLesson(
        "pawn-structure", "Pawn structure and weak squares", "pawn_structure", "intermediate",
        "Treat pawn moves as long-term commitments: every advance can create a strength and a weakness.",
        "Doubled, isolated, and backward pawns can become targets. A square that can no longer be challenged by an enemy pawn may become a lasting outpost.",
        ("Identify isolated, doubled, and backward pawns.", "Which files or diagonals became open after a pawn exchange?", "Can an enemy knight occupy a square your pawns cannot chase away?"),
        "When you create a weak pawn, attack it with pieces rather than rushing more pawns forward."
    ),
    StrategyLesson(
        "open-files", "Open files and rook activity", "open_files", "intermediate",
        "Place rooks on open files, or on half-open files that lead toward an enemy pawn or the seventh rank.",
        "A rook needs a route into the position. Controlling an open file can restrict the opponent and create entry squares.",
        ("Find files with no pawns or only enemy pawns.", "Can you double rooks or contest the file?", "Is there a safe invasion square on the seventh rank?"),
        "A rook on an open file is useful only when it can contest the file or penetrate; avoid placing it where it can be exchanged without a benefit."
    ),
    StrategyLesson(
        "outposts", "Outposts and strong squares", "outposts", "intermediate",
        "A protected square in enemy territory that enemy pawns cannot challenge can be an ideal home for a knight.",
        "An outpost can restrict enemy pieces, attack weaknesses, and support a kingside or queenside plan.",
        ("Find squares that enemy pawns cannot attack.", "Can a pawn or piece support your knight there?", "Can the opponent exchange or drive away the outposted piece?"),
        "A knight supported by a pawn on an unchallengeable central square can be stronger than a rook with no open file."
    ),
    StrategyLesson(
        "king-safety", "King safety and attacking plans", "king_safety", "intermediate",
        "Build an attack with enough pieces; do not launch pawn advances that expose your own king without a concrete reason.",
        "King safety is a positional asset. Open lines, weak dark or light squares, and missing defenders can create attacking chances.",
        ("Which king has fewer pawn defenders?", "Can you bring another piece before opening lines?", "What happens if the opponent trades your attacking piece?"),
        "Coordinate queen, rooks, and minor pieces toward a target before sacrificing material or weakening your own king."
    ),
    StrategyLesson(
        "middlegame-decisions", "Middlegame decision-making", "planning", "all_levels",
        "Compare candidate moves by king safety, material, piece activity, pawn structure, and the opponent's strongest reply.",
        "A strong positional move improves one feature without allowing a tactical refutation. A repeatable thinking process is more reliable than guessing.",
        ("What changed in the position after the opponent's last move?", "List two or three candidate moves.", "Check forcing replies: checks, captures, and threats.", "Choose the move that improves your worst feature and explain its drawback."),
        "Before moving, state your plan in one sentence and name the opponent's most annoying reply."
    ),
)


@dataclass(frozen=True)
class StrategyExercise:
    exercise_id: str
    title: str
    theme: str
    difficulty: str
    fen: str
    solution_uci: str
    explanation: str
    hints: tuple[str, str, str]


_START = chess.STARTING_FEN
EXERCISES: tuple[StrategyExercise, ...] = (
    StrategyExercise(
        "develop-knight", "Improve a minor piece", "development", "beginner", _START,
        "g1f3",
        "Nf3 develops a knight toward the centre, controls e5 and d4, and prepares castling. It improves a piece without creating a pawn weakness.",
        ("Look for a developing move that influences central squares.", "The king's knight has a natural route toward the centre.", "Play Ng1-f3.")
    ),
    StrategyExercise(
        "claim-centre", "Build a central pawn presence", "pawn_structure", "beginner", _START,
        "d2d4",
        "d4 claims central space and supports control of e5 and c5. It opens the diagonal for the c1-bishop; the pawn advance is a plan, not an automatic rule in every position.",
        ("Think about which move occupies central squares.", "A two-square advance by the queen's pawn claims space.", "Play d2-d4.")
    ),
    StrategyExercise(
        "develop-bishop", "Activate a bishop with tempo", "development", "beginner",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "f1c4",
        "Bc4 develops the bishop to an active diagonal and puts pressure on f7, a sensitive square near the black king. It also helps prepare kingside castling.",
        ("Develop a piece toward an active diagonal.", "The bishop can target f7 from a natural square.", "Play Bf1-c4.")
    ),
    StrategyExercise(
        "central-knight", "Challenge the centre with development", "outposts", "beginner",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "g1f3",
        "Nf3 attacks e5 while developing. It adds pressure to the centre and supports future central play; development and threats work together.",
        ("Find a developing move that also attacks a central pawn.", "The king's knight can attack e5.", "Play Ng1-f3.")
    ),
)


@dataclass
class StrategySession:
    exercise: StrategyExercise
    mode: StrategyMode = "practice"
    board: chess.Board = field(init=False)
    attempts: int = 0
    solved: bool = False
    hint_level: int = 0

    def __post_init__(self) -> None:
        if self.mode not in {"practice", "mastery"}:
            raise ValueError("mode must be practice or mastery.")
        self.board = chess.Board(self.exercise.fen)
        if not self.board.is_valid():
            raise ValueError(f"Invalid strategy position: {self.exercise.exercise_id}")
        move = chess.Move.from_uci(self.exercise.solution_uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal strategy solution: {self.exercise.exercise_id}")

    def state(self) -> dict:
        reveal = self.mode == "practice" and self.hint_level == 3
        return {
            "exercise_id": self.exercise.exercise_id,
            "title": self.exercise.title,
            "theme": self.exercise.theme,
            "difficulty": self.exercise.difficulty,
            "mode": self.mode,
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn else "black",
            "legal_moves_uci": sorted(move.uci() for move in self.board.legal_moves),
            "prompt": "Explain the strategic idea behind your move." if not self.solved else "Decision explained.",
            "hint": self.exercise.hints[self.hint_level - 1] if self.hint_level else None,
            "hint_level": self.hint_level,
            "hints_available": not self.solved and self.mode == "practice" and self.hint_level < 3,
            "expected_move": self.exercise.solution_uci if reveal else None,
            "explanation": self.exercise.explanation if self.solved else None,
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
            raise RuntimeError("This exercise is already completed.")
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move in current position: {uci}")
        self.attempts += 1
        if move.uci() != self.exercise.solution_uci:
            return {"correct": False, "applied": False,
                    "message": "Legal move, but it does not match this exercise's strategic idea. Re-check your plan.",
                    "state": self.state()}
        san = self.board.san(move)
        self.board.push(move)
        self.solved = True
        return {"correct": True, "applied": True, "san": san,
                "message": "Good decision. Review the positional explanation.",
                "state": self.state()}

    def reveal_hint(self, level: int) -> dict:
        if self.mode != "practice":
            raise PermissionError("Hints are disabled in Mastery mode.")
        if self.solved:
            raise RuntimeError("This exercise is already completed.")
        if level != self.hint_level + 1 or not 1 <= level <= 3:
            raise ValueError("Reveal hints one level at a time, from 1 to 3.")
        self.hint_level = level
        return self.state()

    def restart(self) -> dict:
        self.board = chess.Board(self.exercise.fen)
        self.attempts = 0
        self.solved = False
        self.hint_level = 0
        return self.state()
