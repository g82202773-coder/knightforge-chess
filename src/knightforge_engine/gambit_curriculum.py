"""Validated 40-repertoire KnightForge Gambit Academy.

The move list is supplied by the learner and is treated as repertoire material,
not as an engine claim that every line is best or forced. Each SAN sequence is
replayed from the initial position with python-chess. Invalid lines are rejected
from the playable tree and included in a validation report.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chess

from .opening_tree import OpeningTree, VariationNode

DEFAULT_GAMBIT_PATH = Path(__file__).resolve().parents[2] / "data/openings/gambit_curriculum.json"
GAMBIT_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class GambitValidationIssue:
    gambit_id: str
    line_label: str
    ply: int
    token: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gambit_id": self.gambit_id,
            "line_label": self.line_label,
            "ply": self.ply,
            "token": self.token,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class GambitLibrary:
    entries: tuple[dict[str, Any], ...]
    trees: tuple[OpeningTree, ...]
    issues: tuple[GambitValidationIssue, ...]

    def guide(self, gambit_id: str) -> dict[str, Any] | None:
        entry = next((item for item in self.entries if item["id"] == gambit_id), None)
        if entry is None:
            return None
        tree = next((item for item in self.trees if item.opening_id == gambit_id), None)
        valid_labels = {
            label for label in _line_labels(entry)
            if not any(issue.gambit_id == gambit_id and issue.line_label == label for issue in self.issues)
        }
        return {
            "id": entry["id"],
            "name": entry["name"],
            "side": entry["side"],
            "kind": entry["kind"],
            "summary": entry["summary"],
            "white_plan": entry["white_plan"],
            "black_plan": entry["black_plan"],
            "finish_plan": entry["finish_plan"],
            "key_ideas": list(entry.get("key_ideas", [])),
            "common_traps": list(entry.get("common_traps", [])),
            "line_count": len(entry.get("lines", [])),
            "validated_line_count": len(valid_labels),
            "branch_count": tree.branch_count() if tree else 0,
            "review_status": tree.review_status if tree else "in_review",
            "lines": [
                {"label": line["label"], "moves": line["moves"]}
                for line in entry.get("lines", [])
            ],
        }

    def list_guides(self, side: str = "all", query: str = "") -> list[dict[str, Any]]:
        term = query.strip().casefold()
        results: list[dict[str, Any]] = []
        for entry in self.entries:
            if side in {"white", "black"} and entry["side"] != side:
                continue
            if term and term not in " ".join(
                [entry["id"], entry["name"], entry["summary"], *entry.get("aliases", [])]
            ).casefold():
                continue
            guide = self.guide(entry["id"])
            if guide is not None:
                results.append(guide)
        return results

    def report(self) -> dict[str, Any]:
        return {
            "gambit_count": len(self.entries),
            "white_count": sum(1 for item in self.entries if item["side"] == "white"),
            "black_count": sum(1 for item in self.entries if item["side"] == "black"),
            "source_line_count": sum(len(item.get("lines", [])) for item in self.entries),
            "validated_line_count": sum(
                len(item.get("lines", []))
                - sum(1 for issue in self.issues if issue.gambit_id == item["id"])
                for item in self.entries
            ),
            "rejected_line_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
            "note": (
                "A legal move sequence is not an engine evaluation or a forced win. "
                "Lines stop at their supplied opening endpoint; training then enters "
                "free play for middlegame, endgame and checkmate practice."
            ),
        }


def _line_labels(entry: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(line.get("label", "")) for line in entry.get("lines", []))


def _clean_san_token(token: str) -> str:
    value = token.strip()
    value = re.sub(r"^\d+\.(?:\.\.)?", "", value)
    value = value.rstrip("!?")
    if value in {"", "..."}:
        return ""
    if value in {"e.p.", "ep"}:
        return ""
    return value


def parse_san_sequence(moves: str) -> tuple[str, ...]:
    """Parse a SAN sequence with strict legal-move checks from the initial board."""
    board = chess.Board()
    result: list[str] = []
    for raw in moves.split():
        token = _clean_san_token(raw)
        if not token:
            continue
        move = board.parse_san(token)
        result.append(board.uci(move))
        board.push(move)
    if not result:
        raise ValueError("line has no moves")
    return tuple(result)


def _move_explanation(
    board: chess.Board, move: chess.Move, entry: dict[str, Any], san: str
) -> str:
    piece = board.piece_at(move.from_square)
    side_name = "White" if board.turn == chess.WHITE else "Black"
    if board.is_castling(move):
        action = "Castle to improve king safety and connect the rooks."
    elif board.is_capture(move):
        action = "Capture: calculate the recapture, material balance and king safety before continuing."
    elif board.gives_check(move):
        action = "Check: identify every legal king response and the next forcing move."
    elif piece and piece.piece_type == chess.KNIGHT:
        action = "Develop the knight toward central squares and useful attacking or defensive posts."
    elif piece and piece.piece_type == chess.BISHOP:
        action = "Develop the bishop onto an active diagonal; check whether it is needed to defend the king."
    elif piece and piece.piece_type == chess.PAWN:
        action = "This pawn move changes the centre or opens a file; note the squares it leaves weak."
    elif piece and piece.piece_type == chess.QUEEN:
        action = "Use the queen actively only while checking that it cannot be chased with tempo."
    elif piece and piece.piece_type == chess.ROOK:
        action = "Activate the rook on an open or semi-open file and connect it with the other rook."
    else:
        action = "Improve the piece while keeping the king safe and the central squares controlled."
    context = entry["summary"]
    return f"{side_name} plays {san}. {action} Gambit idea: {context}"


def _build_mutable_line(
    root_nodes: list[dict[str, Any]],
    entry: dict[str, Any],
    line: dict[str, Any],
) -> tuple[str, ...]:
    board = chess.Board()
    siblings = root_nodes
    path: list[str] = []
    for raw in line["moves"].split():
        token = _clean_san_token(raw)
        if not token:
            continue
        move = board.parse_san(token)
        san = board.san(move)
        uci = board.uci(move)
        path.append(uci)
        node = next((item for item in siblings if item["move_uci"] == uci), None)
        if node is None:
            node = {
                "move_uci": uci,
                "label": "",
                "white_plan": entry["white_plan"],
                "black_plan": entry["black_plan"],
                "explanation": _move_explanation(board, move, entry, san),
                "children": [],
            }
            siblings.append(node)
        siblings = node["children"]
        board.push(move)

    if not path:
        raise ValueError("line has no moves")
    final_node = _find_node(root_nodes, path)
    if final_node is None:
        raise ValueError("internal tree construction error")
    label = str(line["label"]).strip()
    old_label = final_node["label"]
    if label and label not in old_label.split(" / "):
        final_node["label"] = f"{old_label} / {label}" if old_label else label
    line_coach = str(line.get("coach", "")).strip()
    final_node["explanation"] = (
        f"Variation focus — {label}. {line_coach or entry['summary']} "
        f"Endgame and conversion plan: {entry['finish_plan']}"
    )
    return tuple(path)


def _find_node(nodes: list[dict[str, Any]], path: tuple[str, ...]) -> dict[str, Any] | None:
    siblings = nodes
    found: dict[str, Any] | None = None
    for uci in path:
        found = next((item for item in siblings if item["move_uci"] == uci), None)
        if found is None:
            return None
        siblings = found["children"]
    return found


def build_gambit_library(path: str | Path | None = None) -> GambitLibrary:
    """Load all repertoire records, reject illegal lines, and create validated trees."""
    source = Path(path) if path else DEFAULT_GAMBIT_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != GAMBIT_SCHEMA_VERSION:
        raise ValueError("Unsupported or malformed gambit curriculum schema.")
    records = payload.get("sets")
    if not isinstance(records, list):
        raise TypeError("Gambit curriculum sets must be an array.")

    entries: list[dict[str, Any]] = []
    trees: list[OpeningTree] = []
    issues: list[GambitValidationIssue] = []
    seen_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("Each gambit record must be an object.")
        for key in ("id", "name", "side", "kind", "summary", "white_plan", "black_plan", "finish_plan"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"Gambit field {key} is required.")
        gambit_id = record["id"]
        if gambit_id in seen_ids:
            raise ValueError(f"Duplicate gambit ID: {gambit_id}")
        seen_ids.add(gambit_id)
        if record["side"] not in {"white", "black"}:
            raise ValueError(f"Invalid side for gambit {gambit_id}.")
        lines = record.get("lines")
        if not isinstance(lines, list) or not lines:
            raise ValueError(f"Gambit {gambit_id} requires at least one line.")

        roots: list[dict[str, Any]] = []
        valid_line_count = 0
        seen_labels: set[str] = set()
        for line in lines:
            if not isinstance(line, dict) or not isinstance(line.get("label"), str) or not isinstance(line.get("moves"), str):
                raise TypeError(f"Each line in {gambit_id} needs label and moves strings.")
            label = line["label"].strip()
            if not label or label.casefold() in seen_labels:
                raise ValueError(f"Missing or duplicate line label in {gambit_id}: {label!r}")
            seen_labels.add(label.casefold())
            try:
                _build_mutable_line(roots, record, line)
            except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError) as exc:
                issues.append(
                    GambitValidationIssue(
                        gambit_id=gambit_id,
                        line_label=label,
                        ply=0,
                        token="",
                        message=str(exc),
                    )
                )
            else:
                valid_line_count += 1

        if valid_line_count == 0:
            continue
        root_nodes = tuple(_freeze_node(node) for node in roots)
        first_line = next(
            line for line in lines
            if not any(issue.gambit_id == gambit_id and issue.line_label == line["label"] for issue in issues)
        )
        anchor = parse_san_sequence(first_line["moves"])
        aliases = tuple(str(item) for item in record.get("aliases", []))
        tree = OpeningTree(
            opening_id=gambit_id,
            name=record["name"],
            side=record["side"],
            aliases=aliases,
            source_name="User-provided KnightForge 40-gambit curriculum",
            source_url=None,
            license_name="User-supplied move notation; original KnightForge coaching text",
            review_status="in_review",
            roots=root_nodes,
            transposition_notes=(
                "User-supplied repertoire material replayed with python-chess; legal validation does not prove best play.",
                "The selected line ends at its supplied move endpoint. Continue in free play for middlegame, endgame and checkmate practice.",
            ),
            anchor_uci=anchor,
        )
        tree.validate()
        trees.append(tree)
        entries.append(record)

    if len(trees) != len(entries):
        raise ValueError("Gambit library tree construction count mismatch.")
    return GambitLibrary(tuple(entries), tuple(trees), tuple(issues))


def _freeze_node(payload: dict[str, Any]) -> VariationNode:
    return VariationNode(
        move_uci=payload["move_uci"],
        label=payload["label"],
        white_plan=payload["white_plan"],
        black_plan=payload["black_plan"],
        explanation=payload["explanation"],
        children=tuple(_freeze_node(child) for child in payload["children"]),
    )
