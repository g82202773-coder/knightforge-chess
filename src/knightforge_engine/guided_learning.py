"""Position-aware guided chess lessons and coach prompts.

The service emits validated move guidance, not audio or an animated avatar.
Clients can render its voice script, arrow, highlighted squares, and feedback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import chess

from .core import ChessGame, GameStatus


@dataclass(frozen=True, slots=True)
class LessonNode:
    """A move in a branching lesson tree with position-specific coaching."""
    move_uci: str
    explanation: str
    children: tuple[LessonNode, ...] = field(default_factory=tuple)
    hint: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.move_uci, str) or not self.move_uci.strip():
            raise ValueError("Lesson move_uci must be a non-empty UCI move.")
        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("Every lesson move needs a non-empty explanation.")
        if not isinstance(self.hint, str):
            raise TypeError("Lesson hint must be a string.")


@dataclass(frozen=True, slots=True)
class GuidedLesson:
    """A legally validated, branching lesson from a declared starting FEN."""
    lesson_id: str
    title: str
    learner_color: Literal["white", "black"]
    roots: tuple[LessonNode, ...]
    starting_fen: str = chess.STARTING_FEN

    def validate(self) -> None:
        if not self.lesson_id.strip() or not self.title.strip():
            raise ValueError("lesson_id and title are required.")
        if self.learner_color not in {"white", "black"}:
            raise ValueError("learner_color must be white or black.")
        try:
            board = chess.Board(self.starting_fen)
        except ValueError as exc:
            raise ValueError(f"Invalid lesson starting FEN: {exc}") from exc
        if not board.is_valid():
            raise ValueError("Lesson starting FEN is not a valid position.")

        def visit(position: chess.Board, nodes: tuple[LessonNode, ...]) -> None:
            seen: set[chess.Move] = set()
            for node in nodes:
                try:
                    move = chess.Move.from_uci(node.move_uci)
                except ValueError as exc:
                    raise ValueError(f"Invalid lesson UCI move: {node.move_uci}") from exc
                if move in seen:
                    raise ValueError(f"Duplicate alternative lesson move: {node.move_uci}")
                seen.add(move)
                if move not in position.legal_moves:
                    raise ValueError(
                        f"Illegal lesson move {node.move_uci} in position {position.fen()}."
                    )
                next_position = position.copy()
                next_position.push(move)
                visit(next_position, node.children)

        visit(board, self.roots)


@dataclass(frozen=True, slots=True)
class CoachMistakeFeedback:
    """Concrete, rules-checked explanation for a rejected learner move."""

    title: str
    text: str
    detail: str
    voice_script: str
    severity: Literal["warning", "info"]
    threat_arrow_from: str | None = None
    threat_arrow_to: str | None = None
    threatened_square: str | None = None


def _mistake_feedback(board: chess.Board, attempted: chess.Move) -> CoachMistakeFeedback:
    """Explain a concrete hanging piece only when a legal capture cannot be recaptured."""
    attempted_san = board.san(attempted)
    mover = board.turn
    after = board.copy()
    after.push(attempted)

    piece_names = {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight",
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
    }
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }
    hanging: list[tuple[int, chess.Move, chess.Piece, int, bool]] = []
    for reply in list(after.legal_moves):
        if not after.is_capture(reply):
            continue
        captured_square = reply.to_square
        if after.is_en_passant(reply):
            captured_square += -8 if after.turn == chess.WHITE else 8
        victim = after.piece_at(captured_square)
        if victim is None or victim.color != mover or victim.piece_type == chess.KING:
            continue

        capture_san = after.san(reply)
        after_capture = after.copy()
        after_capture.push(reply)
        recaptures = [
            response
            for response in after_capture.legal_moves
            if response.to_square == reply.to_square and after_capture.is_capture(response)
        ]
        if not recaptures:
            hanging.append(
                (piece_values[victim.piece_type], reply, victim, captured_square,
                 after_capture.is_checkmate())
            )

    if hanging:
        _, capture, victim, victim_square, is_mate = max(hanging, key=lambda item: item[0])
        attacker = after.piece_at(capture.from_square)
        attacker_name = piece_names.get(attacker.piece_type, "piece") if attacker else "piece"
        victim_name = piece_names[victim.piece_type]
        attacker_square = chess.square_name(capture.from_square).upper()
        target_square = chess.square_name(victim_square).upper()
        capture_san = after.san(capture)
        if is_mate:
            text = (
                f"After {attempted_san}, your opponent has {capture_san} — "
                f"a checkmating capture."
            )
            detail = f"The {attacker_name} on {attacker_square} can capture on {target_square} with checkmate."
        else:
            text = (
                f"This move leaves your {victim_name} on {target_square} "
                f"vulnerable to capture by the {attacker_name}."
            )
            detail = (
                f"{capture_san} is legal, and there is no legal immediate recapture. "
                "That loses material."
            )
        return CoachMistakeFeedback(
            title="Can I show you something?",
            text=text,
            detail=detail,
            voice_script=f"Can I show you something? {text} {detail}",
            severity="warning",
            threat_arrow_from=chess.square_name(capture.from_square),
            threat_arrow_to=chess.square_name(victim_square),
            threatened_square=chess.square_name(victim_square),
        )

    text = (
        f"{attempted_san} is legal, but it does not follow the reviewed continuation "
        "for this lesson. Your move has not been played, so you can try again."
    )
    detail = (
        "Look at the task and the position before choosing another move. "
        "The coach will not label a piece as hanging unless a legal capture is verified."
    )
    return CoachMistakeFeedback(
        title="Let's review that move",
        text=text,
        detail=detail,
        voice_script=f"Let's review that move. {text} {detail}",
        severity="info",
    )


@dataclass(frozen=True, slots=True)
class CoachPrompt:
    """Presentation-ready instruction derived from the live chess position."""
    kind: Literal["move", "correction", "opponent_deviation", "complete", "free_play"]
    text: str
    voice_script: str
    expected_uci: str | None
    expected_san: str | None
    arrow_from: str | None
    arrow_to: str | None
    highlighted_squares: tuple[str, ...]
    explanation: str
    legal_moves_uci: tuple[str, ...]
    fen: str
    turn: str
    game_status: str
    mistake_feedback: CoachMistakeFeedback | None = None


@dataclass(frozen=True, slots=True)
class MoveSubmission:
    """Outcome of one learner/opponent move submission."""
    accepted: bool
    correct: bool | None
    applied: bool
    actual_san: str | None
    prompt: CoachPrompt
    message: str


class GuidedLessonSession:
    """Stateful, rules-backed lesson session for one learner and one board.

    Correct learner moves and expected opponent replies advance the curated
    branch. A wrong learner move is not applied, allowing an immediate retry.
    An unexpected opponent move is applied, but guided continuation pauses:
    the caller must request fresh analysis or choose a reviewed branch rather
    than receiving an invented book continuation.
    """

    def __init__(self, lesson: GuidedLesson) -> None:
        lesson.validate()
        self.lesson = lesson
        self.game = ChessGame(lesson.starting_fen)
        self._nodes = lesson.roots
        self._history: list[tuple[str, tuple[LessonNode, ...]]] = []
        self._deviation = False

    @property
    def is_complete(self) -> bool:
        return not self._deviation and not self._nodes and self.game.status not in {
            GameStatus.CHECKMATE, GameStatus.STALEMATE,
            GameStatus.INSUFFICIENT_MATERIAL, GameStatus.SEVENTYFIVE_MOVES,
            GameStatus.FIVEFOLD_REPETITION,
        }

    def prompt(self) -> CoachPrompt:
        board = self.game.copy_board()
        if self._deviation:
            kind = "opponent_deviation"
            text = "Your opponent chose a move outside this reviewed lesson line. Let's inspect the new position before continuing."
            voice = text
            selected = None
            explanation = "The stored lesson does not contain this continuation."
        elif not self._nodes:
            kind = "complete" if self.game.status not in {GameStatus.ACTIVE, GameStatus.CHECK} else "free_play"
            text = "Lesson line complete. You can continue playing freely." if kind == "free_play" else "The game has reached a terminal position."
            voice = text
            selected = None
            explanation = ""
        else:
            selected = self._nodes[0]
            move = chess.Move.from_uci(selected.move_uci)
            san = board.san(move)
            source = chess.square_name(move.from_square)
            target = chess.square_name(move.to_square)
            piece = board.piece_at(move.from_square)
            piece_name = chess.piece_name(piece.piece_type) if piece else "piece"
            if move.promotion:
                piece_name = "pawn"
            text = f"Move the {piece_name} from {source.upper()} to {target.upper()} ({san})."
            if selected.hint:
                text += " " + selected.hint
            voice = text + " " + selected.explanation
            kind = "move"
            explanation = selected.explanation
        legal = tuple(sorted(self.game.legal_moves))
        expected_move = chess.Move.from_uci(selected.move_uci) if selected else None
        expected_san = board.san(expected_move) if expected_move else None
        squares = (
            (chess.square_name(expected_move.from_square), chess.square_name(expected_move.to_square))
            if expected_move else ()
        )
        return CoachPrompt(
            kind=kind, text=text, voice_script=voice,
            expected_uci=selected.move_uci if selected else None,
            expected_san=expected_san,
            arrow_from=squares[0] if squares else None,
            arrow_to=squares[1] if squares else None,
            highlighted_squares=squares, explanation=explanation,
            legal_moves_uci=legal, fen=self.game.fen,
            turn=self.game.turn, game_status=self.game.status.value,
        )

    def submit_uci(self, uci: str) -> MoveSubmission:
        """Submit a move from the current side; validate it against live state."""
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci}") from exc
        board = self.game.copy_board()
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move in current position: {uci}")
        if self._deviation:
            raise RuntimeError("Guided continuation paused; resolve the new position first.")

        matching = next((node for node in self._nodes if node.move_uci == move.uci()), None)
        learner_turn = self.game.turn == self.lesson.learner_color
        if matching is None and learner_turn:
            expected = self.prompt()
            corrected = CoachPrompt(
                kind="correction",
                text=f"That move is legal, but it is not one of the moves in this lesson. Try {expected.expected_san or 'the highlighted move'} instead.",
                voice_script=f"Good try. That move is legal, but it is not the move this lesson is practising. {expected.text}",
                expected_uci=expected.expected_uci, expected_san=expected.expected_san,
                arrow_from=expected.arrow_from, arrow_to=expected.arrow_to,
                highlighted_squares=expected.highlighted_squares,
                explanation=expected.explanation,
                legal_moves_uci=expected.legal_moves_uci,
                fen=self.game.fen, turn=self.game.turn,
                game_status=self.game.status.value,
                mistake_feedback=_mistake_feedback(board, move),
            )
            return MoveSubmission(False, False, False, None, corrected, "Review the feedback, then retry or continue.")

        self._history.append((self.game.fen, self._nodes))
        result = self.game.push_uci(move.uci())
        if matching is None:
            self._deviation = True
            return MoveSubmission(
                True, None, True, result.san, self.prompt(),
                "Opponent move applied; curated lesson continuation paused for fresh analysis.",
            )

        self._nodes = matching.children
        return MoveSubmission(True, True, True, result.san, self.prompt(), "Expected lesson move accepted.")

    def undo(self) -> None:
        """Restore the exact previous game state and lesson branch."""
        if not self._history:
            raise ValueError("There is no move to undo.")
        fen, nodes = self._history.pop()
        self.game = ChessGame(fen)
        self._nodes = nodes
        self._deviation = False

    def restart(self) -> None:
        """Reset the session to the validated lesson start."""
        self.game = ChessGame(self.lesson.starting_fen)
        self._nodes = self.lesson.roots
        self._history.clear()
        self._deviation = False
