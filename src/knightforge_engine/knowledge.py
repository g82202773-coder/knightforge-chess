"""Structured, provenance-aware records for chess knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import chess


class KnowledgeType(str, Enum):
    OPENING = "opening"
    TACTIC = "tactic"
    STRATEGY = "strategy"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"
    CHECKMATE_PATTERN = "checkmate_pattern"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REVIEWED = "reviewed"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class KnowledgeLine:
    """A legal move sequence with optional explanatory metadata."""

    moves_uci: tuple[str, ...]
    label: str = ""
    white_plan: str = ""
    black_plan: str = ""
    notes: str = ""

    def validate(self, starting_fen: str = chess.STARTING_FEN) -> None:
        """Raise ValueError if the line contains an illegal move."""
        try:
            board = chess.Board(starting_fen)
        except ValueError as exc:
            raise ValueError(f"Invalid starting FEN: {exc}") from exc
        if not board.is_valid():
            raise ValueError("Starting FEN is not a valid chess position.")

        for ply, uci in enumerate(self.moves_uci, start=1):
            try:
                move = chess.Move.from_uci(uci)
            except ValueError as exc:
                raise ValueError(f"Malformed UCI move at ply {ply}: {uci}") from exc
            if move not in board.legal_moves:
                raise ValueError(f"Illegal move at ply {ply}: {uci}")
            board.push(move)


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    """A chess concept or opening entry with traceable provenance."""

    record_id: str
    title: str
    knowledge_type: KnowledgeType
    summary: str
    tags: tuple[str, ...]
    source_name: str
    source_url: str | None
    license_name: str
    review_status: ReviewStatus
    lines: tuple[KnowledgeLine, ...] = ()

    def validate(self) -> None:
        """Validate required metadata and all attached move lines."""
        if not self.record_id.strip():
            raise ValueError("record_id is required.")
        if not self.title.strip():
            raise ValueError("title is required.")
        if not self.source_name.strip():
            raise ValueError("source_name is required.")
        if not self.license_name.strip():
            raise ValueError("license_name is required.")
        if self.review_status in {ReviewStatus.REVIEWED, ReviewStatus.PUBLISHED}:
            if not self.lines and self.knowledge_type == KnowledgeType.OPENING:
                raise ValueError("Reviewed opening records must contain a move line.")
            for line in self.lines:
                line.validate()
