"""Bounded Stockfish UCI analysis adapter."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import chess
import chess.engine


@dataclass(frozen=True, slots=True)
class EngineLine:
    """One principal variation returned by the analysis engine."""

    multipv: int
    depth: int | None
    score_cp: int | None
    score_mate: int | None
    moves_uci: tuple[str, ...]
    moves_san: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Analysis metadata and candidate lines."""

    engine_name: str
    engine_version: str
    fen: str
    depth: int | None
    nodes: int | None
    lines: tuple[EngineLine, ...]


class StockfishAnalyzer:
    """Run Stockfish with explicit time/depth and MultiPV limits.

    The executable path is supplied by trusted server configuration, not
    directly by an end-user request.
    """

    def __init__(self, executable: str | None = None) -> None:
        configured = executable or os.environ.get("STOCKFISH_PATH")
        if not configured:
            raise RuntimeError("Set STOCKFISH_PATH to the Stockfish executable.")
        path = Path(configured).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Stockfish executable not found: {path}")
        self.executable = str(path)

    def analyse(
        self,
        fen: str,
        *,
        time_limit: float = 1.0,
        depth: int | None = None,
        multipv: int = 3,
    ) -> AnalysisResult:
        """Analyse a valid position under conservative resource limits."""
        if not 0.05 <= time_limit <= 30.0:
            raise ValueError("time_limit must be between 0.05 and 30 seconds.")
        if depth is not None and not 1 <= depth <= 40:
            raise ValueError("depth must be between 1 and 40.")
        if not 1 <= multipv <= 5:
            raise ValueError("multipv must be between 1 and 5.")

        try:
            board = chess.Board(fen)
        except ValueError as exc:
            raise ValueError(f"Invalid FEN: {exc}") from exc
        if not board.is_valid():
            raise ValueError("FEN describes an invalid chess position.")

        limit = chess.engine.Limit(time=time_limit, depth=depth)
        with chess.engine.SimpleEngine.popen_uci(self.executable) as engine:
            engine.configure({"MultiPV": multipv})
            raw: list[dict[str, Any]] = engine.analyse(
                board, limit, multipv=multipv
            )
            if isinstance(raw, dict):
                raw = [raw]
            engine_name = str(engine.id.get("name", "Stockfish"))
            engine_version = str(engine.id.get("version", "unknown"))

        lines: list[EngineLine] = []
        for index, info in enumerate(raw, start=1):
            pv = info.get("pv", [])
            replay = board.copy()
            san_moves: list[str] = []
            legal_uci: list[str] = []
            for move in pv:
                if move not in replay.legal_moves:
                    break
                san_moves.append(replay.san(move))
                legal_uci.append(move.uci())
                replay.push(move)

            score = info.get("score")
            pov_score = score.pov(board.turn) if score is not None else None
            score_cp = pov_score.score(mate_score=100000) if pov_score else None
            score_mate = pov_score.mate() if pov_score else None
            lines.append(
                EngineLine(
                    multipv=int(info.get("multipv", index)),
                    depth=info.get("depth"),
                    score_cp=score_cp,
                    score_mate=score_mate,
                    moves_uci=tuple(legal_uci),
                    moves_san=tuple(san_moves),
                )
            )

        return AnalysisResult(
            engine_name=engine_name,
            engine_version=engine_version,
            fen=board.fen(),
            depth=max((line.depth or 0 for line in lines), default=0) or None,
            nodes=sum(int(item.get("nodes", 0)) for item in raw) or None,
            lines=tuple(lines),
        )
