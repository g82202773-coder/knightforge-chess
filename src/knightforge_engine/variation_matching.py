"""Match reached positions against every reviewed opening-tree variation."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from .opening_recognition import OpeningRecognition
from .opening_repository import OpeningRepository
from .opening_tree import OpeningTree, VariationNode


@dataclass(frozen=True, slots=True)
class VariationPositionMatch:
    """A validated opening-tree path matching the supplied position."""

    opening_id: str
    name: str
    eco: str | None
    matched_ply: int
    matched_line_uci: tuple[str, ...]
    matched_line_san: tuple[str, ...]
    variation_labels: tuple[str, ...]
    matched_via_transposition: bool | None
    source_name: str
    source_url: str | None
    license_name: str


@dataclass(frozen=True, slots=True)
class VariationMatchResult:
    """All deepest variation paths matching a validated game position."""

    fen: str
    ply: int
    matches: tuple[VariationPositionMatch, ...]
    ambiguous: bool
    input_kind: str


class PositionBasedVariationMatcher:
    """Match positions to reviewed move-tree branches, not just opening anchors.

    For move histories, the deepest reached node in each opening tree is used.
    If different tree paths reach the same deepest position, all are returned.
    FEN input can identify a position and line, but cannot prove its move order.
    """

    def __init__(self, repository: OpeningRepository) -> None:
        self.repository = repository

    def match(self, recognition: OpeningRecognition) -> VariationMatchResult:
        """Match an already validated OpeningRecognition against stored trees."""
        if not isinstance(recognition, OpeningRecognition):
            raise TypeError("recognition must be an OpeningRecognition.")

        positions: dict[str, list[tuple[int, tuple[str, ...] | None]]] = {}
        actual_moves = recognition.moves_uci
        if recognition.input_kind == "fen":
            board = chess.Board(recognition.fen)
            positions[OpeningTree._position_key(board)] = [
                (recognition.ply, None)
            ]
        else:
            board = chess.Board()
            positions[OpeningTree._position_key(board)] = [(0, ())]
            for ply, uci in enumerate(actual_moves, start=1):
                move = chess.Move.from_uci(uci)
                if move not in board.legal_moves:
                    raise ValueError(f"Recognition contains illegal stored move at ply {ply}.")
                board.push(move)
                positions.setdefault(OpeningTree._position_key(board), []).append(
                    (ply, actual_moves[:ply])
                )

        matches: list[VariationPositionMatch] = []
        for opening in self.repository.all():
            if not (
                opening.review_status in {"reviewed", "published"}
                and opening.source_name.strip()
                and opening.license_name.strip()
                and opening.anchor_uci
            ):
                continue
            opening.validate()
            candidates = self._tree_positions(opening)
            reached: list[VariationPositionMatch] = []
            for key, line_uci, labels, line_san in candidates:
                for ply, actual_prefix in positions.get(key, ()):
                    transposed = (
                        None if actual_prefix is None else actual_prefix != line_uci
                    )
                    reached.append(
                        VariationPositionMatch(
                            opening_id=opening.opening_id,
                            name=opening.name,
                            eco=opening.eco,
                            matched_ply=ply,
                            matched_line_uci=line_uci,
                            matched_line_san=line_san,
                            variation_labels=labels,
                            matched_via_transposition=transposed,
                            source_name=opening.source_name,
                            source_url=opening.source_url,
                            license_name=opening.license_name,
                        )
                    )
            if reached:
                deepest = max(item.matched_ply for item in reached)
                matches.extend(item for item in reached if item.matched_ply == deepest)

        matches.sort(
            key=lambda item: (
                item.opening_id,
                item.matched_ply,
                item.matched_line_uci,
                item.variation_labels,
            )
        )
        return VariationMatchResult(
            fen=recognition.fen,
            ply=recognition.ply,
            matches=tuple(matches),
            ambiguous=len(matches) > 1,
            input_kind=recognition.input_kind,
        )

    @classmethod
    def _tree_positions(
        cls, opening: OpeningTree
    ) -> tuple[
        tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...
    ]:
        """Return every reached node position with its path, labels, and SAN."""
        results: list[
            tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]
        ] = []
        start = chess.Board(opening.starting_fen)

        def visit(
            board: chess.Board,
            nodes: tuple[VariationNode, ...],
            path: tuple[str, ...],
            labels: tuple[str, ...],
            san_path: tuple[str, ...],
        ) -> None:
            for node in nodes:
                move = chess.Move.from_uci(node.move_uci)
                san = board.san(move)
                next_board = board.copy()
                next_board.push(move)
                next_path = (*path, node.move_uci)
                next_labels = (
                    (*labels, node.label.strip()) if node.label.strip() else labels
                )
                next_san = (*san_path, san)
                # Do not classify a position as this opening until the exact
                # curated anchor path has been reached. Other legal branches
                # in the same tree may be transpositions or unrelated systems.
                if next_path[: len(opening.anchor_uci)] == opening.anchor_uci:
                    results.append(
                        (
                            OpeningTree._position_key(next_board),
                            next_path,
                            next_labels,
                            next_san,
                        )
                    )
                visit(next_board, node.children, next_path, next_labels, next_san)

        visit(start, opening.roots, (), (), ())
        return tuple(results)
