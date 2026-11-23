"""Structured inspection of chess positions, squares, and legal move options."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from .core import ChessGame


@dataclass(frozen=True, slots=True)
class MoveOption:
    """One legal move with human- and machine-readable details."""

    san: str
    uci: str
    from_square: str
    to_square: str
    moving_piece: str
    captured_piece: str | None
    promotion: str | None
    gives_check: bool
    is_capture: bool


@dataclass(frozen=True, slots=True)
class SquareState:
    """The contents and attack state of one board square."""

    square: str
    piece: str | None
    piece_name: str | None
    color: str | None
    is_attacked_by_white: bool
    is_attacked_by_black: bool


_PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


class PositionInspector:
    """Read-only, rules-backed view of the current position in a ChessGame."""

    def __init__(self, game: ChessGame) -> None:
        self._board = game.copy_board()

    @property
    def turn(self) -> str:
        """Side to move."""
        return "white" if self._board.turn == chess.WHITE else "black"

    @property
    def fen(self) -> str:
        """Current position in FEN notation."""
        return self._board.fen()

    def square(self, name: str) -> SquareState:
        """Describe a square such as e4, including attacks by both sides."""
        try:
            square = chess.parse_square(name.lower())
        except ValueError as exc:
            raise ValueError(f"Invalid chess square: {name}") from exc
        piece = self._board.piece_at(square)
        return SquareState(
            square=chess.square_name(square),
            piece=piece.symbol() if piece else None,
            piece_name=_PIECE_NAMES[piece.piece_type] if piece else None,
            color=("white" if piece.color else "black") if piece else None,
            is_attacked_by_white=self._board.is_attacked_by(chess.WHITE, square),
            is_attacked_by_black=self._board.is_attacked_by(chess.BLACK, square),
        )

    def legal_moves(self) -> tuple[MoveOption, ...]:
        """Return every legal move from the current position."""
        return tuple(self._describe_move(move) for move in self._board.legal_moves)

    def legal_moves_from(self, square_name: str) -> tuple[MoveOption, ...]:
        """Return legal destinations for the piece on a square."""
        try:
            square = chess.parse_square(square_name.lower())
        except ValueError as exc:
            raise ValueError(f"Invalid chess square: {square_name}") from exc
        return tuple(
            self._describe_move(move)
            for move in self._board.legal_moves
            if move.from_square == square
        )

    def _describe_move(self, move: chess.Move) -> MoveOption:
        piece = self._board.piece_at(move.from_square)
        if piece is None:
            raise RuntimeError("Legal move unexpectedly has no moving piece.")
        captured = self._board.piece_at(move.to_square)
        if self._board.is_en_passant(move):
            captured = chess.Piece(chess.PAWN, not piece.color)
        next_board = self._board.copy()
        next_board.push(move)
        return MoveOption(
            san=self._board.san(move),
            uci=move.uci(),
            from_square=chess.square_name(move.from_square),
            to_square=chess.square_name(move.to_square),
            moving_piece=_PIECE_NAMES[piece.piece_type],
            captured_piece=_PIECE_NAMES[captured.piece_type] if captured else None,
            promotion=_PIECE_NAMES[move.promotion] if move.promotion else None,
            gives_check=next_board.is_check(),
            is_capture=self._board.is_capture(move),
        )
