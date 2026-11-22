"""Authoritative standard-chess game state and notation operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import io

import chess
import chess.pgn


class GameStatus(str, Enum):
    """Current game outcome/status."""

    ACTIVE = "active"
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    INSUFFICIENT_MATERIAL = "insufficient_material"
    SEVENTYFIVE_MOVES = "seventyfive_moves"
    FIVEFOLD_REPETITION = "fivefold_repetition"
    VARIANT_DRAW = "variant_draw"
    VARIANT_WIN = "variant_win"
    VARIANT_LOSS = "variant_loss"


@dataclass(frozen=True, slots=True)
class MoveResult:
    """Result of applying one legal move."""

    uci: str
    san: str
    fen: str
    turn: str
    status: GameStatus


class ChessGame:
    """A standard chess game backed by python-chess.

    This class intentionally exposes legal operations rather than allowing
    callers to mutate the underlying board directly.
    """

    def __init__(self, fen: str | None = None) -> None:
        try:
            self._board = chess.Board(fen) if fen else chess.Board()
        except ValueError as exc:
            raise ValueError(f"Invalid FEN: {exc}") from exc
        if not self._board.is_valid():
            raise ValueError("FEN describes an invalid chess position.")

    @property
    def fen(self) -> str:
        """Return the current position in FEN notation."""
        return self._board.fen()

    @property
    def turn(self) -> str:
        """Return the side to move."""
        return "white" if self._board.turn == chess.WHITE else "black"

    @property
    def is_check(self) -> bool:
        return self._board.is_check()

    @property
    def legal_moves(self) -> tuple[str, ...]:
        """Return all legal moves in UCI notation."""
        return tuple(sorted(move.uci() for move in self._board.legal_moves))

    @property
    def status(self) -> GameStatus:
        """Return the current terminal or check status."""
        outcome = self._board.outcome(claim_draw=False)
        if outcome is None:
            return GameStatus.CHECK if self._board.is_check() else GameStatus.ACTIVE

        termination = outcome.termination
        mapping = {
            chess.Termination.CHECKMATE: GameStatus.CHECKMATE,
            chess.Termination.STALEMATE: GameStatus.STALEMATE,
            chess.Termination.INSUFFICIENT_MATERIAL: GameStatus.INSUFFICIENT_MATERIAL,
            chess.Termination.SEVENTYFIVE_MOVES: GameStatus.SEVENTYFIVE_MOVES,
            chess.Termination.FIVEFOLD_REPETITION: GameStatus.FIVEFOLD_REPETITION,
            chess.Termination.VARIANT_DRAW: GameStatus.VARIANT_DRAW,
            chess.Termination.VARIANT_WIN: GameStatus.VARIANT_WIN,
            chess.Termination.VARIANT_LOSS: GameStatus.VARIANT_LOSS,
        }
        return mapping[termination]

    def push_uci(self, uci: str) -> MoveResult:
        """Validate and apply a UCI move; reject illegal or malformed moves."""
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci}") from exc

        if move not in self._board.legal_moves:
            raise ValueError(f"Illegal move in current position: {uci}")

        san = self._board.san(move)
        self._board.push(move)
        return MoveResult(
            uci=move.uci(),
            san=san,
            fen=self.fen,
            turn=self.turn,
            status=self.status,
        )

    def push_san(self, san: str) -> MoveResult:
        """Validate and apply a SAN move."""
        try:
            move = self._board.parse_san(san)
        except ValueError as exc:
            raise ValueError(f"Invalid or illegal SAN move: {san}") from exc
        return self.push_uci(move.uci())

    def undo(self) -> str:
        """Undo the previous move and return its UCI notation."""
        if not self._board.move_stack:
            raise ValueError("There is no move to undo.")
        return self._board.pop().uci()

    def reset(self) -> None:
        """Reset to the standard initial position."""
        self._board.reset()

    def export_pgn(self) -> str:
        """Export the current game as PGN."""
        game = chess.pgn.Game.from_board(self._board)
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        return game.accept(exporter)

    def copy_board(self) -> chess.Board:
        """Return an independent board copy for trusted internal integrations."""
        return self._board.copy(stack=True)

    @classmethod
    def from_pgn(cls, pgn_text: str) -> "ChessGame":
        """Load the mainline of a PGN, rejecting parse errors and illegal moves."""
        stream = io.StringIO(pgn_text)
        game = chess.pgn.read_game(stream)
        if game is None:
            raise ValueError("PGN contains no game.")
        if game.errors:
            raise ValueError(f"PGN contains errors: {game.errors!r}")
        board = game.board()
        for move in game.mainline_moves():
            if move not in board.legal_moves:
                raise ValueError(f"PGN contains an illegal move: {move.uci()}")
            board.push(move)
        return cls(board.fen())
