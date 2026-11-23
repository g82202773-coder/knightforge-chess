"""Interactive opening training sessions built from validated opening trees."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import chess

from .opening_tree import OpeningTree, VariationNode

TrainingMode = Literal["guided", "practice", "mastery"]


@dataclass
class OpeningTrainingSession:
    """A learner plays one repertoire side while the opponent follows a stored line.

    Sibling nodes are accepted alternatives. The opponent follows the first
    available continuation deterministically; no unreviewed moves are invented.
    """
    opening: OpeningTree
    learner_color: Literal["white", "black"]
    mode: TrainingMode = "practice"
    board: chess.Board = field(init=False)
    nodes: tuple[VariationNode, ...] = field(init=False)
    history: list[tuple[str, tuple[VariationNode, ...], int]] = field(default_factory=list)
    correct_moves: int = 0
    attempts: int = 0
    hint_level: int = 0
    complete: bool = False

    def __post_init__(self) -> None:
        if self.learner_color not in {"white", "black"}:
            raise ValueError("learner_color must be white or black.")
        if self.mode not in {"guided", "practice", "mastery"}:
            raise ValueError("mode must be guided, practice, or mastery.")
        if self.opening.side not in {self.learner_color, "both"}:
            raise ValueError("The selected opening is not assigned to the learner's side.")
        self.opening.validate()
        self.board = chess.Board(self.opening.starting_fen)
        self.nodes = self.opening.roots
        self._advance_opponent()

    def _advance_opponent(self) -> None:
        while self.board.turn != (self.learner_color == "white") and self.nodes:
            node = self.nodes[0]
            move = chess.Move.from_uci(node.move_uci)
            self.board.push(move)
            self.nodes = node.children
            self.hint_level = 0
        self.complete = not self.nodes or self.board.is_game_over()

    def state(self) -> dict:
        expected = self.nodes[0] if self.nodes and not self.complete else None
        show_answer = self.mode == "guided"
        show_hint = self.mode == "practice" and self.hint_level > 0
        hint = None
        if expected and show_hint:
            move = chess.Move.from_uci(expected.move_uci)
            hint = {
                "level": self.hint_level,
                "text": (
                    "Look at the piece that needs development."
                    if self.hint_level == 1 else
                    f"Consider the move from {chess.square_name(move.from_square).upper()}."
                    if self.hint_level == 2 else
                    f"Move from {chess.square_name(move.from_square).upper()} to {chess.square_name(move.to_square).upper()}."
                ),
            }
        return {
            "opening_id": self.opening.opening_id,
            "opening_name": self.opening.name,
            "mode": self.mode,
            "learner_color": self.learner_color,
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn else "black",
            "legal_moves_uci": sorted(move.uci() for move in self.board.legal_moves),
            "prompt": "Opening line complete." if self.complete else f"Find the next {self.learner_color} repertoire move.",
            "expected_move": expected.move_uci if expected and show_answer else None,
            "hint": hint,
            "hints_available": bool(expected) and self.mode == "practice",
            "complete": self.complete,
            "progress": {
                "correct_moves": self.correct_moves,
                "attempts": self.attempts,
                "accuracy_percent": round(100 * self.correct_moves / self.attempts) if self.attempts else 0,
                "plies_played": len(self.board.move_stack),
            },
        }

    def submit(self, uci: str) -> dict:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci}") from exc
        if self.complete:
            raise RuntimeError("This opening training line is complete.")
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move in current position: {uci}")
        matching = next((node for node in self.nodes if node.move_uci == move.uci()), None)
        self.attempts += 1
        if matching is None:
            return {"applied": False, "correct": False, "message": "Legal move, but not in this opening line. Try another continuation.", "state": self.state()}
        self.history.append((self.board.fen(), self.nodes, self.hint_level))
        san = self.board.san(move)
        self.board.push(move)
        self.nodes = matching.children
        self.correct_moves += 1
        self.hint_level = 0
        self._advance_opponent()
        return {"applied": True, "correct": True, "san": san, "message": "Correct repertoire move.", "state": self.state()}

    def reveal_hint(self, level: int) -> dict:
        if self.mode != "practice":
            raise PermissionError("Hints are available only in Practice mode.")
        if not 1 <= level <= 3:
            raise ValueError("Hint level must be between 1 and 3.")
        if self.complete or not self.nodes:
            raise RuntimeError("No training move is available.")
        if level != self.hint_level + 1:
            raise ValueError("Reveal hints one level at a time.")
        self.hint_level = level
        return self.state()

    def undo(self) -> dict:
        if not self.history:
            raise ValueError("There is no training move to undo.")
        fen, nodes, hint = self.history.pop()
        self.board = chess.Board(fen)
        self.nodes = nodes
        self.hint_level = hint
        self.complete = False
        return self.state()

    def restart(self) -> dict:
        self.board = chess.Board(self.opening.starting_fen)
        self.nodes = self.opening.roots
        self.history.clear()
        self.correct_moves = 0
        self.attempts = 0
        self.hint_level = 0
        self.complete = False
        self._advance_opponent()
        return self.state()
