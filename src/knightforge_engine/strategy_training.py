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
    strategic_plan: str = ""
    positional_gains: tuple[str, ...] = ()
    concessions: tuple[str, ...] = ()
    opponent_plan: str = ""
    candidate_comparison: str = ""
    evaluation_basis: str = "Human-authored positional explanation; no engine score is asserted."


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

    StrategyExercise(
        "middlegame-outpost", "Establish a protected knight outpost", "outposts", "intermediate",
        "2r3k1/pp3ppp/8/8/2P2N2/8/PP3PPP/R3R1K1 w - - 0 20",
        "f4d5",
        "Nd5 installs the knight on a protected central outpost. The c4-pawn supports d5, and Black has no c- or e-pawn available to chase the knight away. The knight restricts Black and eyes useful central and kingside squares.",
        ("Look for a square in enemy territory that a pawn cannot challenge.", "Check whether one of your pawns can support that square.", "Move the f4-knight to d5."),
        "Place the knight on d5, then use its central control to restrict Black's pieces and consider pressure against c7 and e7.",
        ("A durable central outpost for the knight.", "More control over c7, e7, f6, and b6.", "A piece that is difficult to exchange or drive away with a pawn."),
        ("The knight leaves f4, so it no longer influences e2 and g2.", "The outpost is valuable only while it remains tactically safe; watch for piece exchanges."),
        "Black should challenge the knight with pieces, consider ...Ne7 or ...Rd8, and avoid allowing White to consolidate without counterplay.",
        "A developing move such as Ne2 is playable but less ambitious: it retreats the knight and gives up the chance to occupy the protected outpost immediately.",
    ),
    StrategyExercise(
        "middlegame-open-file", "Take control of the open e-file", "open_files", "intermediate",
        "2r3k1/pp3ppp/2p5/3p4/3P4/2P5/PP3QPP/R2R2K1 w - - 0 20",
        "d1e1",
        "Re1 places the rook on the completely pawn-free e-file. The queen on f2 protects e1, so the rook is not simply hanging to a file invasion. White gains a route for lateral coordination and can contest entry squares.",
        ("Identify a file with no pawns.", "Before occupying it, check whether the rook can be captured or exchanged unfavourably.", "Move the d1-rook to e1."),
        "Occupy the e-file, coordinate the queen and rooks, and look for a safe route to the seventh rank if Black cannot contest the file.",
        ("A rook becomes active on an open file.", "The queen supports the rook on e1.", "White can contest central entry squares and improve rook coordination."),
        ("The rook leaves the d-file, reducing immediate pressure there.", "Black may challenge the file with ...Re8 or seek a trade; do not assume an open file automatically guarantees an invasion."),
        "Black should contest the e-file, trade the active rook if favourable, or create counterplay on the queenside.",
        "A quiet pawn move leaves the open file unoccupied. Re1 is more purposeful because it improves a major piece while maintaining protection.",
    ),
    StrategyExercise(
        "middlegame-prophylaxis", "Prevent a useful bishop pin and give the king luft", "king_safety", "intermediate",
        "r4rk1/pp3ppp/2p1b3/3p4/3P4/2P1PN2/PP3PPP/R2Q1RK1 w - - 0 18",
        "h2h3",
        "h3 is a useful prophylactic move: it controls g4, making ...Bg4 less comfortable against the knight on f3, and gives the king a potential luft square on h2. It is a modest improvement rather than a forced attack.",
        ("Look for an opponent's useful developing move or pin.", "Check whether a pawn move can remove that square without weakening your king excessively.", "Play h2-h3."),
        "Reduce the opponent's easy kingside piece activity, preserve the f3-knight's flexibility, and keep h2 available as a king escape square.",
        ("Controls g4 and discourages ...Bg4.", "Creates a possible luft square for the king.", "Improves the position without committing a central pawn."),
        ("The h-pawn advances and can become a target later.", "The move does not create an immediate threat; White must continue improving pieces."),
        "Black can seek counterplay with central breaks or reroute the bishop; the move does not stop every kingside plan.",
        "A forcing move is not required. h3 addresses a concrete positional detail and reduces Black's convenient options.",
    ),
    StrategyExercise(
        "middlegame-centralization", "Centralize the knight on a supported square", "development", "intermediate",
        "r4rk1/pp3ppp/2p1b3/3p4/3P4/2P1PN2/PP1B1PPP/R2Q1RK1 w - - 0 18",
        "f3e5",
        "Ne5 centralizes the knight on a square protected by the d4-pawn. From e5 it gains influence over c6, f7, g6, and d7 while increasing pressure on Black's position. The point is not merely moving forward: the square is supported and difficult for a pawn to challenge.",
        ("Find a central square your pawn structure can support.", "Check whether an enemy pawn can drive the knight away.", "Play Nf3-e5."),
        "Use the supported e5-square as a strong post, then coordinate queen and rooks around central or kingside targets.",
        ("A more active knight with central influence.", "The knight attacks c6 and f7 and controls important entry squares.", "White increases pressure without changing the pawn structure."),
        ("The knight leaves f3, so the kingside has one fewer defender near the king.", "Black may exchange the knight with a piece; assess whether the resulting structure favours White."),
        "Black should consider exchanging the centralized knight or challenging the centre with a timely pawn break.",
        "A routine rook move does not exploit the available central square. Ne5 improves the least active minor piece and creates a stable point of pressure.",
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
            "position_phase": "middlegame" if self.exercise.exercise_id.startswith("middlegame-") else "opening",
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn else "black",
            "legal_moves_uci": sorted(move.uci() for move in self.board.legal_moves),
            "prompt": "Explain the strategic idea behind your move." if not self.solved else "Decision explained.",
            "hint": self.exercise.hints[self.hint_level - 1] if self.hint_level else None,
            "hint_level": self.hint_level,
            "hints_available": not self.solved and self.mode == "practice" and self.hint_level < 3,
            "expected_move": self.exercise.solution_uci if reveal else None,
            "explanation": self.exercise.explanation if self.solved else None,
            "strategic_review": ({
                "plan": self.exercise.strategic_plan,
                "positional_gains": list(self.exercise.positional_gains),
                "concessions": list(self.exercise.concessions),
                "opponent_plan": self.exercise.opponent_plan,
                "candidate_comparison": self.exercise.candidate_comparison,
                "evaluation_basis": self.exercise.evaluation_basis,
            } if self.solved else None),
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
