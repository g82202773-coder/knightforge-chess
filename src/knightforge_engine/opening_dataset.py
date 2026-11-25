"""Import legally validated launch opening trees from the pinned Lichess CC0 dataset.

The source dataset supplies ECO names and PGN move sequences, not coaching prose.
KnightForge preserves its provenance and marks imported courses in review until
strategic explanations and repertoire recommendations receive editorial review.
"""
from __future__ import annotations

import io
import json
import re
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chess
import chess.pgn

from .opening_catalog import OpeningCatalog
from .opening_tree import OpeningTree, VariationNode

SOURCE_NAME = "Lichess chess-openings dataset"
SOURCE_LICENSE = "CC0 1.0 Universal"
LAUNCH_SYSTEM_IDS: tuple[str, ...] = (
    "ruy-lopez", "italian-game", "scotch-game", "kings-gambit", "vienna-game",
    "four-knights", "petrov", "open-sicilian", "anti-sicilians", "french",
    "caro-kann", "pirc", "scandinavian", "alekhine", "queens-gambit", "slav",
    "semi-slav", "london", "colle", "trompowsky", "catalan", "kings-indian",
    "grunfeld", "nimzo-indian", "benoni", "benko", "english", "reti",
    "dutch-stonewall", "dutch-leningrad",
)

_ANTI_SICILIAN = re.compile(
    r"Alapin|Rossolimo|Moscow|Grand Prix|Closed Sicilian|Smith.?Morra|"
    r"Wing Gambit|Bowdler|McDonnell",
    re.IGNORECASE,
)


def _matches(opening_id: str, name: str) -> bool:
    """Map an upstream ECO name to exactly one KnightForge launch system."""
    rules: dict[str, Callable[[str], bool]] = {
        "ruy-lopez": lambda n: n.startswith("Ruy Lopez"),
        "italian-game": lambda n: n.startswith("Italian Game"),
        "scotch-game": lambda n: n.startswith("Scotch Game"),
        "kings-gambit": lambda n: n.startswith("King's Gambit"),
        "vienna-game": lambda n: n.startswith("Vienna Game"),
        "four-knights": lambda n: n.startswith("Four Knights Game"),
        "petrov": lambda n: bool(re.match(r"Petrov'?s? (?:Defense|Defence)", n, re.IGNORECASE)),
        "open-sicilian": lambda n: n.startswith("Sicilian Defense") and not _ANTI_SICILIAN.search(n),
        "anti-sicilians": lambda n: n.startswith("Sicilian Defense") and bool(_ANTI_SICILIAN.search(n)),
        "french": lambda n: n.startswith("French Defense"),
        "caro-kann": lambda n: n.startswith("Caro-Kann Defense"),
        "pirc": lambda n: n.startswith("Pirc Defense"),
        "scandinavian": lambda n: n.startswith("Scandinavian Defense"),
        "alekhine": lambda n: n.startswith("Alekhine Defense"),
        "queens-gambit": lambda n: n.startswith("Queen's Gambit"),
        "slav": lambda n: n.startswith("Slav Defense"),
        "semi-slav": lambda n: n.startswith("Semi-Slav Defense"),
        "london": lambda n: bool(re.match(
            r"(?:London System(?:[:,]|$)|Indian Defense: .*London System|"
            r"Queen's Pawn Game: .*London System|Rapport-Jobava System)", n, re.IGNORECASE
        )),
        "colle": lambda n: "Colle System" in n,
        "trompowsky": lambda n: "Trompowsky Attack" in n,
        "catalan": lambda n: n.startswith("Catalan Opening"),
        "kings-indian": lambda n: n.startswith("King's Indian Defense"),
        "grunfeld": lambda n: n.startswith("Grünfeld Defense"),
        "nimzo-indian": lambda n: n.startswith("Nimzo-Indian Defense"),
        "benoni": lambda n: n.startswith("Benoni Defense"),
        "benko": lambda n: n.startswith("Benko Gambit"),
        "english": lambda n: n.startswith("English Opening"),
        "reti": lambda n: n.startswith("Réti Opening"),
        "dutch-stonewall": lambda n: n.startswith("Dutch Defense: Stonewall"),
        "dutch-leningrad": lambda n: n.startswith("Dutch Defense: Leningrad"),
    }
    matcher = rules.get(opening_id)
    return bool(matcher and matcher(name))


@dataclass(slots=True)
class _MutableNode:
    move_uci: str
    labels: list[str] = field(default_factory=list)
    children: OrderedDict[str, _MutableNode] = field(default_factory=OrderedDict)


@dataclass(frozen=True, slots=True)
class OpeningDatasetReport:
    source_line_count: int
    imported_line_count: int
    skipped_line_count: int
    tree_count: int
    per_system_lines: dict[str, int]
    per_system_move_nodes: dict[str, int]
    skipped_examples: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": SOURCE_NAME,
            "license": SOURCE_LICENSE,
            "source_line_count": self.source_line_count,
            "imported_line_count": self.imported_line_count,
            "skipped_line_count": self.skipped_line_count,
            "tree_count": self.tree_count,
            "per_system_lines": dict(self.per_system_lines),
            "per_system_move_nodes": dict(self.per_system_move_nodes),
            "skipped_examples": list(self.skipped_examples),
            "review_status": "in_review",
        }


def _variation_label(name: str) -> str:
    if ":" in name:
        return name.split(":", 1)[1].strip() or "Main line"
    if name.startswith("London System,"):
        return name.split(",", 1)[1].strip() or "Main line"
    return name


def _freeze(nodes: OrderedDict[str, _MutableNode]) -> tuple[VariationNode, ...]:
    result: list[VariationNode] = []
    for node in nodes.values():
        labels = list(dict.fromkeys(node.labels))
        result.append(
            VariationNode(
                move_uci=node.move_uci,
                label=" / ".join(labels),
                children=_freeze(node.children),
            )
        )
    return tuple(result)


def merge_variation_nodes(
    *groups: tuple[VariationNode, ...],
) -> tuple[VariationNode, ...]:
    """Merge trees on UCI move prefixes, preserving every distinct label and note."""
    merged: OrderedDict[str, _MutableNode] = OrderedDict()

    def absorb(target: OrderedDict[str, _MutableNode], nodes: tuple[VariationNode, ...]) -> None:
        for source in nodes:
            item = target.setdefault(source.move_uci, _MutableNode(source.move_uci))
            if source.label:
                for label in source.label.split(" / "):
                    if label not in item.labels:
                        item.labels.append(label)
            if source.explanation:
                marker = f"explanation:{source.explanation}"
                if marker not in item.labels:
                    item.labels.append(marker)
            absorb(item.children, source.children)

    for group in groups:
        absorb(merged, group)

    def freeze_clean(nodes: OrderedDict[str, _MutableNode]) -> tuple[VariationNode, ...]:
        output: list[VariationNode] = []
        for item in nodes.values():
            labels = [label for label in item.labels if not label.startswith("explanation:")]
            explanations = [
                label.removeprefix("explanation:")
                for label in item.labels if label.startswith("explanation:")
            ]
            output.append(
                VariationNode(
                    move_uci=item.move_uci,
                    label=" / ".join(labels),
                    explanation=" ".join(dict.fromkeys(explanations)),
                    children=freeze_clean(item.children),
                )
            )
        return tuple(output)

    return freeze_clean(merged)


def load_lichess_opening_trees(
    dataset_path: str | Path,
    catalog: OpeningCatalog,
) -> tuple[dict[str, OpeningTree], OpeningDatasetReport]:
    """Read the pinned CC0 subset, parse its PGNs, and validate every tree branch."""
    path = Path(dataset_path)
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load Lichess opening dataset: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported Lichess opening dataset schema.")
    if payload.get("license") != "CC0-1.0" or not isinstance(payload.get("source_revision"), str):
        raise ValueError("Opening dataset must declare its CC0 license and pinned source revision.")
    records = payload.get("openings")
    if not isinstance(records, list):
        raise TypeError("Lichess opening dataset 'openings' must be an array.")

    grouped: dict[str, OrderedDict[str, _MutableNode]] = {
        opening_id: OrderedDict() for opening_id in LAUNCH_SYSTEM_IDS
    }
    line_counts = {opening_id: 0 for opening_id in LAUNCH_SYSTEM_IDS}
    skipped: list[str] = []
    imported_count = 0

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            skipped.append(f"row {index}: record is not an object")
            continue
        opening_id = record.get("opening_id")
        name, pgn = record.get("name"), record.get("pgn")
        if opening_id not in grouped or not isinstance(name, str) or not isinstance(pgn, str):
            skipped.append(f"row {index}: malformed or unsupported record")
            continue
        if not _matches(opening_id, name):
            skipped.append(f"row {index}: name '{name}' does not belong to '{opening_id}'")
            continue
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None or game.errors:
            reason = "; ".join(str(error) for error in (game.errors if game else []))
            skipped.append(f"{opening_id}/{name}: PGN parse error {reason}".strip())
            continue
        moves = list(game.mainline_moves())
        if not moves:
            skipped.append(f"{opening_id}/{name}: empty move line")
            continue
        board = game.board()
        if board.fen() != chess.STARTING_FEN:
            skipped.append(f"{opening_id}/{name}: non-standard start position is unsupported")
            continue
        cursor = grouped[opening_id]
        for move in moves:
            if move not in board.legal_moves:
                skipped.append(f"{opening_id}/{name}: illegal move {move.uci()}")
                cursor = OrderedDict()
                break
            uci = move.uci()
            node = cursor.setdefault(uci, _MutableNode(uci))
            cursor = node.children
            board.push(move)
        else:
            label = _variation_label(name)
            leaf = grouped[opening_id]
            for move in moves:
                leaf = leaf[move.uci()].children
            leaf_node = _find_parent_node(grouped[opening_id], [move.uci() for move in moves])
            if label and label not in leaf_node.labels:
                leaf_node.labels.append(label)
            line_counts[opening_id] += 1
            imported_count += 1

    source_url = payload.get("source_url") or "https://github.com/lichess-org/chess-openings"
    trees: dict[str, OpeningTree] = {}
    move_nodes: dict[str, int] = {}

    def count_nodes(nodes: tuple[VariationNode, ...]) -> int:
        return sum(1 + count_nodes(node.children) for node in nodes)

    for opening_id in LAUNCH_SYSTEM_IDS:
        system = catalog.get_system_detail(opening_id)
        if system is None:
            raise ValueError(f"Launch system '{opening_id}' is missing from the taxonomy.")
        roots = _freeze(grouped[opening_id])
        if not roots:
            raise ValueError(f"No legal opening lines imported for launch system '{opening_id}'.")
        eco_codes = {
            item.get("eco")
            for item in records
            if isinstance(item, dict) and item.get("opening_id") == opening_id and isinstance(item.get("eco"), str)
        }
        tree = OpeningTree(
            opening_id=opening_id,
            name=system.name,
            side=system.side,
            eco=next(iter(eco_codes)) if len(eco_codes) == 1 else None,
            aliases=(),
            source_name=SOURCE_NAME,
            source_url=str(source_url),
            license_name=SOURCE_LICENSE,
            review_status="in_review",
            roots=roots,
            transposition_notes=(
                ("Identical UCI prefixes are merged. The source may list multiple named "
                "positions and distinct move orders; each imported PGN remains a separate leaf label."),
            ),
        )
        tree.validate()
        trees[opening_id] = tree
        move_nodes[opening_id] = count_nodes(roots)

    report = OpeningDatasetReport(
        source_line_count=len(records),
        imported_line_count=imported_count,
        skipped_line_count=len(skipped),
        tree_count=len(trees),
        per_system_lines=line_counts,
        per_system_move_nodes=move_nodes,
        skipped_examples=tuple(skipped[:20]),
    )
    return trees, report


def _find_parent_node(
    roots: OrderedDict[str, _MutableNode], path: list[str]
) -> _MutableNode:
    if not path:
        raise ValueError("Opening line must contain at least one move.")
    cursor = roots
    node: _MutableNode | None = None
    for uci in path:
        node = cursor[uci]
        cursor = node.children
    if node is None:
        raise ValueError("Cannot label an empty opening path.")
    return node
