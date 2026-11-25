"""Seven-tier legal chess AI opponent with Stockfish UCI and built-in fallback.

Supports Beginner, Easy, Intermediate, Advanced, Expert, Master, and Maximum
strength levels. Uses Stockfish UCI options (Skill Level, depth, time) when
STOCKFISH_PATH is configured; otherwise uses a deterministic alpha-beta +
quiescence searcher over python-chess calibrated by depth and evaluation
fidelity (never random or hardcoded moves).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import chess
import chess.engine

logger = logging.getLogger(__name__)

AIDifficulty = Literal[
    "beginner",
    "easy",
    "intermediate",
    "advanced",
    "expert",
    "master",
    "maximum",
]

DIFFICULTY_PROFILES: dict[AIDifficulty, dict[str, float | int | bool]] = {
    "beginner": {
        "sf_skill": 0, "sf_depth": 1, "sf_time": 0.08,
        "ab_depth": 1, "use_pst": False, "use_quiesce": False,
    },
    "easy": {
        "sf_skill": 4, "sf_depth": 3, "sf_time": 0.12,
        "ab_depth": 1, "use_pst": True, "use_quiesce": False,
    },
    "intermediate": {
        "sf_skill": 8, "sf_depth": 6, "sf_time": 0.20,
        "ab_depth": 2, "use_pst": True, "use_quiesce": False,
    },
    "advanced": {
        "sf_skill": 12, "sf_depth": 9, "sf_time": 0.35,
        "ab_depth": 2, "use_pst": True, "use_quiesce": True,
    },
    "expert": {
        "sf_skill": 15, "sf_depth": 12, "sf_time": 0.55,
        "ab_depth": 3, "use_pst": True, "use_quiesce": False,
    },
    "master": {
        "sf_skill": 18, "sf_depth": 15, "sf_time": 0.85,
        "ab_depth": 3, "use_pst": True, "use_quiesce": True,
    },
    "maximum": {
        "sf_skill": 20, "sf_depth": 18, "sf_time": 1.25,
        "ab_depth": 3, "use_pst": True, "use_quiesce": True,
    },
}

_PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

_CENTER_PST = (
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 5, 5, 5, 5, 5, 5, 0,
    0, 5, 12, 16, 16, 12, 5, 0,
    0, 5, 16, 26, 26, 16, 5, 0,
    0, 5, 16, 26, 26, 16, 5, 0,
    0, 5, 12, 16, 16, 12, 5, 0,
    0, 5, 5, 5, 5, 5, 5, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
)


@dataclass(frozen=True, slots=True)
class CandidateEval:
    """One legal candidate move with engine/evaluator score."""

    uci: str
    san: str
    score_cp_white: int | None
    mate_in: int | None
    pv_san: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AIMoveDecision:
    """Structured result returned when the AI selects a move."""

    uci: str
    san: str
    score_cp_white: int | None
    mate_in: int | None
    engine_source: str
    difficulty: AIDifficulty
    pv_san: tuple[str, ...]
    candidates: tuple[CandidateEval, ...]


def evaluate_static_white(board: chess.Board, *, use_pst: bool = True) -> int:
    """Deterministic static evaluation in centipawns from White's perspective."""
    if board.is_checkmate():
        return -99000 if board.turn == chess.WHITE else 99000
    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
    ):
        return 0

    score = 0
    for sq, piece in board.piece_map().items():
        val = _PIECE_VALUES[piece.piece_type]
        bonus = 0
        if use_pst:
            if piece.piece_type == chess.PAWN:
                rank = chess.square_rank(sq)
                bonus = (rank * 7) if piece.color == chess.WHITE else ((7 - rank) * 7)
                bonus += _CENTER_PST[sq] // 2
            elif piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
                bonus = _CENTER_PST[sq]
            elif piece.piece_type == chess.ROOK:
                rank = chess.square_rank(sq)
                if (piece.color == chess.WHITE and rank == 6) or (
                    piece.color == chess.BLACK and rank == 1
                ):
                    bonus = 20
            elif piece.piece_type == chess.QUEEN:
                bonus = _CENTER_PST[sq] // 3
        total = val + bonus
        score += total if piece.color == chess.WHITE else -total

    if use_pst:
        if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
            score += 25
        if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
            score -= 25
    return score


def _move_order_score(board: chess.Board, move: chess.Move) -> int:
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        v_val = _PIECE_VALUES[victim.piece_type] if victim else 100
        a_val = _PIECE_VALUES[attacker.piece_type] if attacker else 100
        score += 1000 + v_val * 10 - a_val
    if move.promotion:
        score += 800 + _PIECE_VALUES.get(move.promotion, 0)
    if board.gives_check(move):
        score += 250
    return score


def _quiesce(
    board: chess.Board, alpha: int, beta: int, qdepth: int, use_pst: bool
) -> int:
    sign = 1 if board.turn == chess.WHITE else -1
    stand_pat = sign * evaluate_static_white(board, use_pst=use_pst)
    if stand_pat >= beta:
        return beta
    alpha = max(alpha, stand_pat)
    if qdepth <= 0 or board.is_game_over():
        return alpha

    captures = [mv for mv in board.legal_moves if board.is_capture(mv)]
    captures.sort(key=lambda mv: _move_order_score(board, mv), reverse=True)
    for move in captures[:10]:
        board.push(move)
        score = -_quiesce(board, -beta, -alpha, qdepth - 1, use_pst)
        board.pop()
        if score >= beta:
            return beta
        alpha = max(alpha, score)
    return alpha


def _negamax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    *,
    use_pst: bool,
    use_quiesce: bool,
) -> int:
    if board.is_game_over():
        sign = 1 if board.turn == chess.WHITE else -1
        return sign * evaluate_static_white(board, use_pst=use_pst)
    if depth <= 0:
        if use_quiesce:
            return _quiesce(board, alpha, beta, 2, use_pst)
        sign = 1 if board.turn == chess.WHITE else -1
        return sign * evaluate_static_white(board, use_pst=use_pst)

    moves = sorted(
        board.legal_moves,
        key=lambda mv: _move_order_score(board, mv),
        reverse=True,
    )
    best = -100000
    for move in moves:
        board.push(move)
        val = -_negamax(
            board, depth - 1, -beta, -alpha, use_pst=use_pst, use_quiesce=use_quiesce
        )
        board.pop()
        best = max(best, val)
        alpha = max(alpha, best)
        if alpha >= beta:
            break
    return best


def evaluate_position_builtin(
    board: chess.Board,
    depth: int = 2,
    multipv: int = 3,
    *,
    use_pst: bool = True,
    use_quiesce: bool = True,
) -> tuple[CandidateEval, ...]:
    """Return top legal moves and White-centric centipawn scores deterministically."""
    legal = list(board.legal_moves)
    if not legal:
        return ()

    sign = 1 if board.turn == chess.WHITE else -1
    ordered = sorted(legal, key=lambda mv: _move_order_score(board, mv), reverse=True)
    scored: list[tuple[int, chess.Move, str]] = []
    for move in ordered:
        san = board.san(move)
        board.push(move)
        if board.is_checkmate():
            val = 99000
        else:
            val = -_negamax(
                board,
                max(0, depth - 1),
                -100000,
                100000,
                use_pst=use_pst,
                use_quiesce=use_quiesce,
            )
        board.pop()
        scored.append((val, move, san))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[CandidateEval] = []
    for val, move, san in scored[: max(1, multipv)]:
        white_cp = sign * val
        mate_in = None
        if abs(val) >= 90000:
            mate_in = 1 if white_cp > 0 else -1
        results.append(
            CandidateEval(
                uci=move.uci(),
                san=san,
                score_cp_white=white_cp,
                mate_in=mate_in,
                pv_san=(san,),
            )
        )
    return tuple(results)


class ChessAIOpponent:
    """Unified 7-level chess opponent backed by Stockfish UCI or built-in search."""

    def __init__(self, stockfish_path: str | None = None) -> None:
        configured = stockfish_path or os.environ.get("STOCKFISH_PATH")
        self.stockfish_path: str | None = None
        if configured:
            path = Path(configured).expanduser()
            if path.is_file():
                self.stockfish_path = str(path)

    @property
    def stockfish_available(self) -> bool:
        return self.stockfish_path is not None

    def analyse_candidates(
        self,
        board: chess.Board,
        *,
        depth: int = 2,
        time_limit: float = 0.25,
        multipv: int = 3,
    ) -> tuple[tuple[CandidateEval, ...], str]:
        """Return (candidates, engine_source) for any valid non-terminal position."""
        if board.is_game_over():
            return (), "terminal"
        if self.stockfish_path is not None:
            try:
                sf_candidates = self._stockfish_candidates(
                    board,
                    depth=min(20, max(1, depth)),
                    time_limit=time_limit,
                    multipv=multipv,
                )
                if sf_candidates:
                    return sf_candidates, "stockfish"
            except (chess.engine.EngineError, OSError, TimeoutError) as exc:
                logger.warning(
                    "Stockfish candidate analysis failed; using built-in evaluator: %s", exc
                )
        return (
            evaluate_position_builtin(board, depth=min(3, max(1, depth)), multipv=multipv),
            "knightforge-builtin",
        )

    def choose_move(
        self,
        board: chess.Board,
        difficulty: AIDifficulty = "intermediate",
        *,
        thinking_time: float | None = None,
        seed: int | None = None,
    ) -> AIMoveDecision:
        """Choose one legal move calibrated to the requested difficulty level."""
        del seed  # kept for backward-compatible signature; search is 100% deterministic
        if difficulty not in DIFFICULTY_PROFILES:
            raise ValueError(f"Unknown AI difficulty: {difficulty}")
        if board.is_game_over():
            raise RuntimeError("Cannot select an AI move in a finished game.")

        profile = DIFFICULTY_PROFILES[difficulty]
        sf_time = float(thinking_time) if thinking_time is not None else float(profile["sf_time"])
        sf_time = max(0.05, min(5.0, sf_time))

        if self.stockfish_path is not None:
            try:
                return self._choose_stockfish(
                    board,
                    difficulty=difficulty,
                    skill=int(profile["sf_skill"]),
                    depth=int(profile["sf_depth"]),
                    time_limit=sf_time,
                )
            except (chess.engine.EngineError, OSError, TimeoutError) as exc:
                logger.warning(
                    "Stockfish move selection failed; using built-in search: %s", exc
                )

        return self._choose_builtin(
            board,
            difficulty=difficulty,
            depth=int(profile["ab_depth"]),
            use_pst=bool(profile["use_pst"]),
            use_quiesce=bool(profile["use_quiesce"]),
        )

    def _stockfish_candidates(
        self, board: chess.Board, *, depth: int, time_limit: float, multipv: int
    ) -> tuple[CandidateEval, ...]:
        assert self.stockfish_path is not None
        with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
            raw = engine.analyse(
                board,
                chess.engine.Limit(time=time_limit, depth=depth),
                multipv=max(1, min(5, multipv)),
            )
            if isinstance(raw, dict):
                raw = [raw]
        items: list[CandidateEval] = []
        for info in raw:
            pv = info.get("pv", [])
            if not pv:
                continue
            replay = board.copy()
            san_list: list[str] = []
            for mv in pv[:6]:
                if mv not in replay.legal_moves:
                    break
                san_list.append(replay.san(mv))
                replay.push(mv)
            if not san_list:
                continue
            score = info.get("score")
            white_pov = score.white() if score is not None else None
            cp = white_pov.score(mate_score=100000) if white_pov else None
            mate = white_pov.mate() if white_pov else None
            items.append(
                CandidateEval(
                    uci=pv[0].uci(),
                    san=san_list[0],
                    score_cp_white=cp,
                    mate_in=mate,
                    pv_san=tuple(san_list),
                )
            )
        return tuple(items)

    def _choose_stockfish(
        self,
        board: chess.Board,
        *,
        difficulty: AIDifficulty,
        skill: int,
        depth: int,
        time_limit: float,
    ) -> AIMoveDecision:
        assert self.stockfish_path is not None
        with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
            if "Skill Level" in engine.options:
                engine.configure({"Skill Level": skill})
            limit = chess.engine.Limit(time=time_limit, depth=depth)
            play_res = engine.play(board, limit)
            move = play_res.move
            if move is None or move not in board.legal_moves:
                raise RuntimeError("Stockfish returned no legal move.")
            san = board.san(move)
            info = engine.analyse(
                board, chess.engine.Limit(time=min(0.2, time_limit), depth=depth)
            )
        score = info.get("score")
        white_pov = score.white() if score is not None else None
        cp = white_pov.score(mate_score=100000) if white_pov else None
        mate = white_pov.mate() if white_pov else None
        return AIMoveDecision(
            uci=move.uci(),
            san=san,
            score_cp_white=cp,
            mate_in=mate,
            engine_source="stockfish",
            difficulty=difficulty,
            pv_san=(san,),
            candidates=(CandidateEval(move.uci(), san, cp, mate, (san,)),),
        )

    def _choose_builtin(
        self,
        board: chess.Board,
        *,
        difficulty: AIDifficulty,
        depth: int,
        use_pst: bool,
        use_quiesce: bool,
    ) -> AIMoveDecision:
        candidates = evaluate_position_builtin(
            board, depth=depth, multipv=3, use_pst=use_pst, use_quiesce=use_quiesce
        )
        if not candidates:
            raise RuntimeError("No legal moves available.")
        selected = candidates[0]
        return AIMoveDecision(
            uci=selected.uci,
            san=selected.san,
            score_cp_white=selected.score_cp_white,
            mate_in=selected.mate_in,
            engine_source="knightforge-builtin",
            difficulty=difficulty,
            pv_san=selected.pv_san,
            candidates=candidates,
        )
