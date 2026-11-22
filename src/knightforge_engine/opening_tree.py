"""Branching, legally validated opening trees for KnightForge.

Sibling nodes are alternative moves from the same position. Descendants are
continuations. Position keys intentionally omit move clocks while preserving
piece placement, side to move, castling rights, and legally relevant en-passant.
"""

from __future__ import annotations

import chess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


TREE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class VariationNode:
    """One move and its alternative continuations in an opening tree."""

    move_uci: str
    label: str = ""
    white_plan: str = ""
    black_plan: str = ""
    explanation: str = ""
    children: tuple[VariationNode, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to the versioned JSON-compatible representation."""
        return {
            "move_uci": self.move_uci,
            "label": self.label,
            "white_plan": self.white_plan,
            "black_plan": self.black_plan,
            "explanation": self.explanation,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> VariationNode:
        """Build a node from JSON-compatible data, rejecting malformed fields."""
        if not isinstance(payload, Mapping):
            raise TypeError("Variation node must be an object.")
        move_uci = payload.get("move_uci")
        if not isinstance(move_uci, str) or not move_uci.strip():
            raise ValueError("Variation node move_uci must be a non-empty string.")
        text_fields = ("label", "white_plan", "black_plan", "explanation")
        values: dict[str, str] = {}
        for key in text_fields:
            value = payload.get(key, "")
            if not isinstance(value, str):
                raise TypeError(f"Variation node {key} must be a string.")
            values[key] = value
        children = payload.get("children", [])
        if not isinstance(children, list):
            raise TypeError("Variation node children must be an array.")
        return cls(
            move_uci=move_uci,
            **values,
            children=tuple(cls.from_dict(child) for child in children),
        )


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
        if self.review_status not in {"draft", "in_review", "reviewed", "published"}:
            raise ValueError("review_status must be draft, in_review, reviewed, or published.")
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

    @staticmethod
    def _position_key(board: chess.Board) -> str:
        """Return a FEN-derived transposition key without half/fullmove clocks."""
        return " ".join(board.fen(en_passant="legal").split()[:4])

    def position_index(self) -> dict[str, tuple[tuple[str, ...], ...]]:
        """Map each reached position to all move paths that reach it.

        Multiple paths for one key identify transpositions inside this tree.
        The key is suitable for opening-position equivalence, not repetition
        adjudication, which also depends on the move history.
        """
        self.validate()
        index: dict[str, list[tuple[str, ...]]] = {}

        def visit(
            board: chess.Board, nodes: tuple[VariationNode, ...], path: tuple[str, ...]
        ) -> None:
            index.setdefault(self._position_key(board), []).append(path)
            for node in nodes:
                move = chess.Move.from_uci(node.move_uci)
                next_board = board.copy()
                next_board.push(move)
                visit(next_board, node.children, (*path, node.move_uci))

        visit(chess.Board(self.starting_fen), self.roots, ())
        return {key: tuple(paths) for key, paths in index.items()}

    def transpositions(self) -> dict[str, tuple[tuple[str, ...], ...]]:
        """Return only positions reached by more than one distinct move path."""
        return {
            key: paths
            for key, paths in self.position_index().items()
            if len(set(paths)) > 1
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete opening tree using schema version 1."""
        self.validate()
        return {
            "schema_version": TREE_SCHEMA_VERSION,
            "opening_id": self.opening_id,
            "name": self.name,
            "side": self.side,
            "starting_fen": self.starting_fen,
            "eco": self.eco,
            "aliases": list(self.aliases),
            "source_name": self.source_name,
            "source_url": self.source_url,
            "license_name": self.license_name,
            "review_status": self.review_status,
            "transposition_notes": list(self.transposition_notes),
            "roots": [node.to_dict() for node in self.roots],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OpeningTree:
        """Deserialize and legally validate a versioned opening tree."""
        if not isinstance(payload, Mapping):
            raise TypeError("Opening tree payload must be an object.")
        if payload.get("schema_version") != TREE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported opening tree schema_version: {payload.get('schema_version')!r}")
        required_strings = ("opening_id", "name", "side")
        for key in required_strings:
            if not isinstance(payload.get(key), str):
                raise TypeError(f"Opening tree {key} must be a string.")
        optional_strings = (
            "starting_fen", "source_name", "license_name", "review_status"
        )
        for key in optional_strings:
            if key in payload and not isinstance(payload[key], str):
                raise TypeError(f"Opening tree {key} must be a string.")
        for key in ("eco", "source_url"):
            if payload.get(key) is not None and not isinstance(payload.get(key), str):
                raise TypeError(f"Opening tree {key} must be a string or null.")
        for key in ("aliases", "transposition_notes", "roots"):
            if not isinstance(payload.get(key, []), list):
                raise TypeError(f"Opening tree {key} must be an array.")
        for key in ("aliases", "transposition_notes"):
            if any(not isinstance(item, str) for item in payload.get(key, [])):
                raise TypeError(f"Opening tree {key} entries must be strings.")
        tree = cls(
            opening_id=payload["opening_id"],
            name=payload["name"],
            side=payload["side"],
            starting_fen=payload.get("starting_fen", chess.STARTING_FEN),
            eco=payload.get("eco"),
            aliases=tuple(payload.get("aliases", [])),
            source_name=payload.get("source_name", ""),
            source_url=payload.get("source_url"),
            license_name=payload.get("license_name", ""),
            review_status=payload.get("review_status", "draft"),
            roots=tuple(VariationNode.from_dict(node) for node in payload.get("roots", [])),
            transposition_notes=tuple(payload.get("transposition_notes", [])),
        )
        tree.validate()
        return tree
