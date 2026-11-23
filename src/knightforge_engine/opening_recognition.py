"""Move- and position-based recognition of reviewed KnightForge openings.

Recognition is deliberately conservative: only reviewed/published records with
provenance and an explicit legal anchor can produce a named result.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterable
from dataclasses import dataclass

import chess
import chess.pgn

from .opening_repository import OpeningRepository
from .opening_tree import OpeningTree


@dataclass(frozen=True, slots=True)
class OpeningMatch:
    """One opening recognized from a validated move history or position."""

    opening_id: str
    name: str
    eco: str | None
    matched_ply: int
    anchor_uci: tuple[str, ...]
    matched_via_transposition: bool
    variation_labels: tuple[str, ...]
    source_name: str
    source_url: str | None
    license_name: str


@dataclass(frozen=True, slots=True)
class OpeningRecognition:
    """Validated input state and any unambiguous opening classifications."""

    fen: str
    ply: int
    moves_uci: tuple[str, ...]
    moves_san: tuple[str, ...]
    matches: tuple[OpeningMatch, ...]
    ambiguous: bool
    input_kind: str


class OpeningRecognizer:
    """Recognize curated opening anchors without guessing from names alone."""

    def __init__(self, repository: OpeningRepository) -> None:
        self.repository = repository

    def recognize(
        self,
        moves: str | Iterable[str] | None = None,
        *,
        fen: str | None = None,
        notation: str = "auto",
    ) -> OpeningRecognition:
        """Validate SAN/UCI/PGN moves or a FEN and match reviewed anchor positions.

        With a FEN, recognition is position-based; the original move order cannot
        be recovered. With move history, transpositions are recognized by position.
        """
        if notation not in {"auto", "san", "uci", "pgn"}:
            raise ValueError("notation must be auto, san, uci, or pgn.")
        if moves is None and fen is None:
            raise ValueError("Provide move history or a FEN.")
        if moves is not None and fen is not None:
            raise ValueError("Provide move history or a FEN, not both.")

        if fen is not None:
            board = chess.Board(fen)
            if not board.is_valid():
                raise ValueError("FEN does not describe a valid chess position.")
            return self._recognize_position(board)

        tokens, selected_kind = self._parse_moves(moves, notation)
        board = chess.Board()
        positions: dict[str, int] = {OpeningTree._position_key(board): 0}
        san_moves: list[str] = []
        uci_moves: list[str] = []
        for index, token in enumerate(tokens, start=1):
            try:
                if selected_kind == "uci":
                    move = chess.Move.from_uci(token)
                    if move not in board.legal_moves:
                        raise ValueError(f"Illegal UCI move at ply {index}: {token}")
                else:
                    move = board.parse_san(token)
            except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError,
                    chess.AmbiguousMoveError) as exc:
                raise ValueError(f"Invalid {selected_kind.upper()} move at ply {index}: {token}") from exc
            san_moves.append(board.san(move))
            uci_moves.append(move.uci())
            board.push(move)
            positions[OpeningTree._position_key(board)] = index

        return self._build_result(
            board, tuple(uci_moves), tuple(san_moves), positions, selected_kind
        )

    def _recognize_position(self, board: chess.Board) -> OpeningRecognition:
        key = OpeningTree._position_key(board)
        matches: list[OpeningMatch] = []
        for opening in self._eligible_openings():
            anchor_board = self._anchor_board(opening)
            if OpeningTree._position_key(anchor_board) == key:
                matches.append(self._make_match(opening, len(opening.anchor_uci), False))
        return OpeningRecognition(
            fen=board.fen(),
            ply=board.ply(),
            moves_uci=(),
            moves_san=(),
            matches=tuple(matches),
            ambiguous=len(matches) > 1,
            input_kind="fen",
        )

    def _build_result(
        self,
        board: chess.Board,
        moves_uci: tuple[str, ...],
        moves_san: tuple[str, ...],
        positions: dict[str, int],
        input_kind: str,
    ) -> OpeningRecognition:
        matches: list[OpeningMatch] = []
        for opening in self._eligible_openings():
            anchor_board = self._anchor_board(opening)
            anchor_key = OpeningTree._position_key(anchor_board)
            if anchor_key not in positions:
                continue
            matched_ply = positions[anchor_key]
            direct = moves_uci[:matched_ply] == opening.anchor_uci
            labels = self._labels_for_path(opening, opening.anchor_uci)
            matches.append(
                self._make_match(opening, matched_ply, not direct, labels)
            )
        matches.sort(key=lambda item: (item.matched_ply, item.opening_id))
        return OpeningRecognition(
            fen=board.fen(),
            ply=len(moves_uci),
            moves_uci=moves_uci,
            moves_san=moves_san,
            matches=tuple(matches),
            ambiguous=len(matches) > 1,
            input_kind=input_kind,
        )

    def _eligible_openings(self) -> tuple[OpeningTree, ...]:
        return tuple(
            opening for opening in self.repository.all()
            if opening.review_status in {"reviewed", "published"}
            and opening.source_name.strip()
            and opening.license_name.strip()
            and opening.anchor_uci
        )

    @staticmethod
    def _anchor_board(opening: OpeningTree) -> chess.Board:
        board = chess.Board(opening.starting_fen)
        for uci in opening.anchor_uci:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise ValueError(f"Invalid stored anchor in {opening.opening_id}: {uci}")
            board.push(move)
        return board

    @staticmethod
    def _labels_for_path(
        opening: OpeningTree, path: tuple[str, ...]
    ) -> tuple[str, ...]:
        labels: list[str] = []
        nodes = opening.roots
        for uci in path:
            node = next((item for item in nodes if item.move_uci == uci), None)
            if node is None:
                break
            if node.label.strip():
                labels.append(node.label.strip())
            nodes = node.children
        return tuple(labels)

    @staticmethod
    def _make_match(
        opening: OpeningTree,
        matched_ply: int,
        transposition: bool,
        labels: tuple[str, ...] | None = None,
    ) -> OpeningMatch:
        return OpeningMatch(
            opening_id=opening.opening_id,
            name=opening.name,
            eco=opening.eco,
            matched_ply=matched_ply,
            anchor_uci=opening.anchor_uci,
            matched_via_transposition=transposition,
            variation_labels=labels if labels is not None else
                OpeningRecognizer._labels_for_path(opening, opening.anchor_uci),
            source_name=opening.source_name,
            source_url=opening.source_url,
            license_name=opening.license_name,
        )

    @staticmethod
    def _parse_moves(
        moves: str | Iterable[str] | None, notation: str
    ) -> tuple[tuple[str, ...], str]:
        if moves is None:
            return (), "san"
        if isinstance(moves, str):
            raw = moves.strip()
            if notation == "pgn" or (notation == "auto" and
                                      ("[" in raw or re.search(r"\d+\.(\.\.)?", raw))):
                game = chess.pgn.read_game(io.StringIO(raw))
                if game is None:
                    raise ValueError("No PGN game found.")
                if game.errors:
                    raise ValueError(f"PGN contains parse errors: {game.errors[0]}")
                return tuple(move.uci() for move in game.mainline_moves()), "uci"
            tokens = raw.split()
        else:
            tokens = list(moves)
        if any(not isinstance(token, str) or not token.strip() for token in tokens):
            raise ValueError("Move tokens must be non-empty strings.")
        tokens = [token.strip() for token in tokens]
        selected = notation
        if selected == "auto":
            selected = "uci" if tokens and all(
                re.fullmatch(r"[a-h][1-8][a-h][1-8][qrbn]?", token.lower())
                for token in tokens
            ) else "san"
        if selected == "pgn":
            raise ValueError("PGN notation requires a PGN string.")
        if selected == "san":
            cleaned: list[str] = []
            for token in tokens:
                token = re.sub(r"^\d+\.(\.\.)?", "", token)
                if token and token not in {"...", "1-0", "0-1", "1/2-1/2", "*"}:
                    cleaned.append(token)
            tokens = cleaned
        return tuple(tokens), selected
