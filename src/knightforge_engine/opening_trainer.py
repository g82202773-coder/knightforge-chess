"""Convert any reviewed OpeningTree or named variation into an interactive
GuidedLesson so learners can train any opening/gambit move-by-move.
"""
from __future__ import annotations

from dataclasses import dataclass

import chess

from .guided_learning import GuidedLesson, LessonNode
from .opening_tree import OpeningTree, VariationNode


@dataclass(frozen=True, slots=True)
class VariationLine:
    """One named playable variation path inside an OpeningTree."""

    variation_id: str
    label: str
    moves_uci: tuple[str, ...]
    moves_san: tuple[str, ...]
    ply_count: int


def list_opening_variations(tree: OpeningTree) -> tuple[VariationLine, ...]:
    """Extract every named variation and leaf line from an OpeningTree."""
    tree.validate()
    board = chess.Board(tree.starting_fen)
    lines: list[VariationLine] = []
    seen_paths: set[tuple[str, ...]] = set()

    def walk(
        pos: chess.Board,
        nodes: tuple[VariationNode, ...],
        uci_path: tuple[str, ...],
        san_path: tuple[str, ...],
        last_label: str,
    ) -> None:
        for node in nodes:
            mv = chess.Move.from_uci(node.move_uci)
            san = pos.san(mv)
            nxt = pos.copy(stack=False)
            nxt.push(mv)
            next_uci = (*uci_path, node.move_uci)
            next_san = (*san_path, san)
            lbl = node.label.strip() or last_label
            if not node.children:
                if next_uci not in seen_paths:
                    seen_paths.add(next_uci)
                    var_id = f"{tree.opening_id}::{len(lines) + 1}"
                    lines.append(
                        VariationLine(
                            variation_id=var_id,
                            label=lbl or tree.name,
                            moves_uci=next_uci,
                            moves_san=next_san,
                            ply_count=len(next_uci),
                        )
                    )
            else:
                walk(nxt, node.children, next_uci, next_san, lbl)

    walk(board, tree.roots, (), (), tree.name)
    return tuple(lines)


def _node_explanation(
    board: chess.Board,
    node: VariationNode,
    opening_name: str,
) -> str:
    if node.explanation.strip():
        return node.explanation.strip()
    mv = chess.Move.from_uci(node.move_uci)
    san = board.san(mv)
    if node.label.strip():
        return f"Play {san} to enter {node.label.strip()}."
    return f"Continue the {opening_name} with {san}."


def _convert_tree_nodes(
    board: chess.Board,
    nodes: tuple[VariationNode, ...],
    opening_name: str,
) -> tuple[LessonNode, ...]:
    converted: list[LessonNode] = []
    for node in nodes:
        mv = chess.Move.from_uci(node.move_uci)
        expl = _node_explanation(board, node, opening_name)
        nxt = board.copy(stack=False)
        nxt.push(mv)
        converted.append(
            LessonNode(
                move_uci=node.move_uci,
                explanation=expl,
                children=_convert_tree_nodes(nxt, node.children, opening_name),
                hint=node.label.strip(),
            )
        )
    return tuple(converted)


def _convert_specific_path(
    board: chess.Board,
    nodes: tuple[VariationNode, ...],
    target_path: tuple[str, ...],
    opening_name: str,
) -> tuple[LessonNode, ...]:
    if not target_path:
        return ()
    first_uci = target_path[0]
    match = next((n for n in nodes if n.move_uci == first_uci), None)
    if match is None:
        raise ValueError(f"Move {first_uci} not found in opening tree {opening_name}.")
    mv = chess.Move.from_uci(match.move_uci)
    expl = _node_explanation(board, match, opening_name)
    nxt = board.copy(stack=False)
    nxt.push(mv)
    return (
        LessonNode(
            move_uci=match.move_uci,
            explanation=expl,
            children=_convert_specific_path(nxt, match.children, target_path[1:], opening_name),
            hint=match.label.strip(),
        ),
    )


def build_opening_lesson(
    tree: OpeningTree,
    *,
    variation_id: str | None = None,
    learner_color: str | None = None,
) -> GuidedLesson:
    """Build a legally validated GuidedLesson for an entire opening or one variation."""
    tree.validate()
    color = learner_color or ("black" if tree.side == "black" else "white")
    if color not in {"white", "black"}:
        color = "white"
    board = chess.Board(tree.starting_fen)

    if variation_id:
        variations = list_opening_variations(tree)
        selected = next((v for v in variations if v.variation_id == variation_id), None)
        if selected is None:
            raise ValueError(f"Unknown variation_id {variation_id} for {tree.opening_id}.")
        roots = _convert_specific_path(board, tree.roots, selected.moves_uci, tree.name)
        title = f"{tree.name} · {selected.label}"
        lid = f"train-{tree.opening_id}-{variation_id.split('::')[-1]}"
    else:
        roots = _convert_tree_nodes(board, tree.roots, tree.name)
        title = f"{tree.name} · Full Repertoire Tree"
        lid = f"train-{tree.opening_id}-all"

    lesson = GuidedLesson(
        lesson_id=lid,
        title=title,
        learner_color=color,  # type: ignore[arg-type]
        roots=roots,
        starting_fen=tree.starting_fen,
    )
    lesson.validate()
    return lesson
