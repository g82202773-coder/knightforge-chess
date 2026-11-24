"""Import rated, tagged chess puzzles from Lichess's official CC0 database.

Download https://database.lichess.org/lichess_db_puzzle.csv.zst (CC0 license),
decompress it to CSV, and run:
    python scripts/import_lichess_puzzles.py lichess_db_puzzle.csv --limit 5000
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import chess


def _difficulty(rating: int) -> str:
    if rating < 1100:
        return "beginner"
    if rating < 1600:
        return "intermediate"
    return "advanced"


def import_lichess_csv(csv_path: Path, out_path: Path, limit: int = 5000) -> int:
    puzzles: list[dict[str, object]] = []
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if len(puzzles) >= limit:
                break
            fen = row["FEN"]
            moves = row["Moves"].split()
            if len(moves) < 2:
                continue
            board = chess.Board(fen)
            # In Lichess CSV, moves[0] is the opponent's setup move before the puzzle starts.
            setup_mv = chess.Move.from_uci(moves[0])
            if setup_mv not in board.legal_moves:
                continue
            board.push(setup_mv)
            start_fen = board.fen()
            solution = moves[1:]
            valid = True
            for uci in solution:
                mv = chess.Move.from_uci(uci)
                if mv not in board.legal_moves:
                    valid = False
                    break
                board.push(mv)
            if not valid:
                continue
            rating = int(row["Rating"])
            themes = [t for t in row["Themes"].split() if t][:4] or ["tactic"]
            puzzles.append({
                "puzzle_id": f"lichess-{row['PuzzleId']}",
                "title": f"Lichess Tactical Puzzle #{row['PuzzleId']}",
                "fen": start_fen,
                "solution_uci": solution,
                "themes": themes,
                "difficulty": _difficulty(rating),
                "rating": rating,
                "explanation": f"Lichess rated {rating} ({', '.join(themes)}).",
                "source_name": "Lichess Open Puzzle Database",
                "license_name": "CC0 1.0 Universal",
            })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schema_version": 1, "puzzles": puzzles}, separators=(",", ":")),
        encoding="utf-8",
    )
    return len(puzzles)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/puzzles/puzzles_1000.json"))
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()
    count = import_lichess_csv(args.csv_file, args.out, limit=args.limit)
    print(f"Imported {count} verified Lichess CC0 puzzles into {args.out}")
