"""Complete legal chess game sessions, independent of the short lesson curriculum."""
from __future__ import annotations

import chess


class FullGame:
    """A standard chess game with full python-chess legality and move history."""

    def __init__(self) -> None:
        self.board = chess.Board()
        self._history: list[chess.Move] = []

    def state(self) -> dict:
        outcome = self.board.outcome(claim_draw=True)
        return {
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn else "black",
            "move_number": self.board.fullmove_number,
            "halfmove_clock": self.board.halfmove_clock,
            "check": self.board.is_check(),
            "checkmate": self.board.is_checkmate(),
            "stalemate": self.board.is_stalemate(),
            "game_over": outcome is not None,
            "result": self.board.result(claim_draw=True) if outcome else None,
            "termination": outcome.termination.name.lower() if outcome else None,
            "legal_moves_uci": [move.uci() for move in self.board.legal_moves],
            "legal_moves_san": [self.board.san(move) for move in self.board.legal_moves],
            "last_move_uci": self._history[-1].uci() if self._history else None,
            "move_history": self._san_history(),
            "can_undo": bool(self._history),
        }

    def _san_history(self) -> list[dict[str, str | int]]:
        board = chess.Board()
        rows: list[dict[str, str | int]] = []
        for index, move in enumerate(self._history):
            san = board.san(move)
            rows.append({
                "ply": index + 1,
                "move_number": board.fullmove_number,
                "color": "white" if board.turn else "black",
                "san": san,
                "uci": move.uci(),
            })
            board.push(move)
        return rows

    def play(self, uci: str) -> dict:
        if self.board.is_game_over(claim_draw=True):
            raise ValueError("The game is over. Start a new game to continue.")
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError("Invalid move notation.") from exc
        if move not in self.board.legal_moves:
            raise ValueError("That move is not legal in this position.")
        san = self.board.san(move)
        self.board.push(move)
        self._history.append(move)
        return {"played": san, "state": self.state()}

    def undo(self) -> dict:
        if not self._history:
            raise ValueError("There are no moves to undo.")
        self.board.pop()
        self._history.pop()
        return self.state()

    def restart(self) -> dict:
        self.board.reset()
        self._history.clear()
        return self.state()
