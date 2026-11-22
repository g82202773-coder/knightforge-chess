"""Branching, legally validated opening trees for KnightForge.

The tree stores one move per node. Sibling nodes represent alternative moves
from the same position; descendants represent continuations. Transpositions
are referenced by position hash/FEN metadata rather than duplicated as aliases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import chess


@dataclass(frozen=True, slots=True)
class VariationNode:
    """One move and its alternative continuations in an opening tree."""

    move_uci: str
    label: str = ""
    white_plan: str = ""
    black_plan: str = ""
    explanation: str = ""
    children: tuple["VariationNode", ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class OpeningTree:
    """A named opening/system whose root children are first-move branches."""

    opening_id: str
    name: str
    side: str
    starting_fen: str = chess.STARTING_FEN
    eco: str | None = None
    aliases: tuple[str, ...] = ()
    source_name: str = ""
    source_url: str | None = None
    license_name: str = ""
    review_status: str = "draft"
    roots: tuple[VariationNode, ...] = field(default_factory=tuple)
    transposition_notes: tuple[str, ...] = ()

    def validate(self) -> None:
        """Validate metadata and every branch from the declared starting FEN."""
        if not self.opening_id.strip() or not self.name.strip():
            raise ValueError("opening_id and name are required.")
        if self.side not in {"white", "black", "both"}:
            raise ValueError("side must be white, black, or both.")
        if self.review_status in {"reviewed", "published"}:
            if not self.source_name.strip() or not self.license_name.strip():
                raise ValueError("Reviewed openings require source and license metadata.")
            if not self.roots:
                raise ValueError("Reviewed openings must contain at least one move branch.")

        try:
            board = chess.Board(self.starting_fen)
        except ValueError as exc:
            raise ValueError(f"Invalid starting FEN: {exc}") from exc
        if not board.is_valid():
            raise ValueError("Starting FEN is not a valid chess position.")

        self._validate_siblings(board, self.roots, "root")

    @classmethod
    def _validate_siblings(
        cls, position: chess.Board, nodes: Iterable[VariationNode], path: str
    ) -> None:
        seen: set[chess.Move] = set()
        for index, node in enumerate(nodes, start=1):
            branch = f"{path}.{index}"
            try:
                move = chess.Move.from_uci(node.move_uci)
            except ValueError as exc:
                raise ValueError(
                    f"Malformed UCI move at {branch}: {node.move_uci}"
                ) from exc
            if move in seen:
                raise ValueError(f"Duplicate sibling move at {branch}: {node.move_uci}")
            seen.add(move)
            if move not in position.legal_moves:
                raise ValueError(f"Illegal move at {branch}: {node.move_uci}")
            next_position = position.copy()
            next_position.push(move)
            cls._validate_siblings(next_position, node.children, branch)

    def mainline_uci(self) -> tuple[str, ...]:
        """Return a deterministic first-child path, useful for previews."""
        result: list[str] = []
        nodes = self.roots
        while nodes:
            node = nodes[0]
            result.append(node.move_uci)
            nodes = node.children
        return tuple(result)

    def mainline_san(self) -> tuple[str, ...]:
        """Return SAN for the deterministic first-child path."""
        board = chess.Board(self.starting_fen)
        san: list[str] = []
        for uci in self.mainline_uci():
            move = chess.Move.from_uci(uci)
            san.append(board.san(move))
            board.push(move)
        return tuple(san)

    def branch_count(self) -> int:
        """Count all move nodes, including alternatives and nested branches."""
        def count(nodes: tuple[VariationNode, ...]) -> int:
            return sum(1 + count(node.children) for node in nodes)
        return count(self.roots)
