"""Rules-backed tactical candidate scanning (heuristic, not position evaluation)."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from .core import ChessGame

_PIECE_VALUES_CP = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

_PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


@dataclass(frozen=True, slots=True)
class TacticalCandidate:
    """A legal forcing move and the motifs it creates immediately.

    capture_priority_cp is a simple victim-minus-attacker ordering heuristic.
    It is not a static exchange evaluation and does not predict the final
    material result after replies.
    """

    san: str
    uci: str
    motifs: tuple[str, ...]
    moving_piece: str
    captured_piece: str | None
    capture_priority_cp: int | None
    gives_check: bool
    is_checkmate: bool


@dataclass(frozen=True, slots=True)
class TacticalScan:
    """Tactical candidates found in one immutable position snapshot."""

    fen: str
    side_to_move: str
    candidates: tuple[TacticalCandidate, ...]


class TacticalScanner:
    """Find legal checks, captures, promotions, and mate-in-one candidates.

    This scanner deliberately reports forcing-move candidates only. It does
    not claim to find every tactic, prove combinations, or replace Stockfish.
    """

    def __init__(self, game: ChessGame) -> None:
        self._board = game.copy_board()

    def scan(self) -> TacticalScan:
        """Return forcing legal moves ordered by mate, check, then heuristic."""
        side = "white" if self._board.turn == chess.WHITE else "black"
        candidates: list[TacticalCandidate] = []

        for move in self._board.legal_moves:
            moving = self._board.piece_at(move.from_square)
            if moving is None:
                continue

            captured = self._board.piece_at(move.to_square)
            if self._board.is_en_passant(move):
                captured = chess.Piece(chess.PAWN, not moving.color)

            next_board = self._board.copy()
            next_board.push(move)
            gives_check = next_board.is_check()
            is_checkmate = next_board.is_checkmate()
            is_capture = self._board.is_capture(move)
            is_promotion = move.promotion is not None

            if not (gives_check or is_capture or is_promotion):
                continue

            motifs: list[str] = []
            if is_checkmate:
                motifs.append("checkmate")
            if gives_check:
                motifs.append("check")
            if is_capture:
                motifs.append("capture")
            if is_promotion:
                motifs.append("promotion")

            capture_priority = None
            if captured is not None:
                capture_priority = (
                    _PIECE_VALUES_CP[captured.piece_type]
                    - _PIECE_VALUES_CP[moving.piece_type]
                )

            candidates.append(
                TacticalCandidate(
                    san=self._board.san(move),
                    uci=move.uci(),
                    motifs=tuple(motifs),
                    moving_piece=_PIECE_NAMES[moving.piece_type],
                    captured_piece=(
                        _PIECE_NAMES[captured.piece_type] if captured else None
                    ),
                    capture_priority_cp=capture_priority,
                    gives_check=gives_check,
                    is_checkmate=is_checkmate,
                )
            )

        candidates.sort(
            key=lambda item: (
                not item.is_checkmate,
                not item.gives_check,
                -(item.capture_priority_cp or 0),
                item.uci,
            )
        )
        return TacticalScan(
            fen=self._board.fen(),
            side_to_move=side,
            candidates=tuple(candidates),
        )
