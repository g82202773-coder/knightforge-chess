"""Post-game move-by-move analysis engine and grounded AI Chess Coach.

Classifies every move using documented centipawn-loss (CPL) thresholds,
generates an evaluation graph, estimates accuracy, and provides board-grounded
coaching answers without ever fabricating engine scores or illegal lines.
"""
from __future__ import annotations

import io
import math
from dataclasses import asdict, dataclass
from typing import Any

import chess
import chess.pgn

from .ai_opponent import ChessAIOpponent
from .core import ChessGame
from .opening_recognition import OpeningRecognizer
from .opening_repository import OpeningRepository
from .positional_analysis import analyze_position
from .tactics import TacticalScanner
from .variation_matching import PositionBasedVariationMatcher


@dataclass(frozen=True, slots=True)
class MoveReview:
    """Analysis record for one half-move in a game."""

    ply: int
    move_number: int
    side: str
    played_san: str
    played_uci: str
    best_san: str | None
    best_uci: str | None
    eval_before_cp_white: int
    eval_after_cp_white: int
    centipawn_loss: int
    classification: str
    phase: str
    comment: str


def _classify_cpl(
    cpl: int,
    *,
    is_best_move: bool,
    missed_winning_swing: bool,
) -> str:
    if is_best_move or cpl <= 10:
        return "best"
    if missed_winning_swing and cpl >= 220:
        return "missed_opportunity"
    if cpl <= 25:
        return "excellent"
    if cpl <= 50:
        return "good"
    if cpl <= 100:
        return "inaccuracy"
    if cpl <= 200:
        return "mistake"
    return "blunder"


def _accuracy_from_cpls(cpls: list[int]) -> float:
    if not cpls:
        return 100.0
    # Documented smooth decay curve mapping mean CPL to [0, 100]
    mean_cpl = sum(min(c, 500) for c in cpls) / len(cpls)
    acc = 103.1668 * math.exp(-0.004354 * mean_cpl) - 3.1668
    return round(max(0.0, min(100.0, acc)), 1)


def _detect_phase(board: chess.Board, ply: int) -> str:
    if ply <= 16:
        return "opening"
    non_pawn_material = sum(
        len(board.pieces(pt, c)) * val
        for c in (chess.WHITE, chess.BLACK)
        for pt, val in ((chess.KNIGHT, 3), (chess.BISHOP, 3), (chess.ROOK, 5), (chess.QUEEN, 9))
    )
    return "endgame" if non_pawn_material <= 24 else "middlegame"


def analyze_pgn_game(
    pgn_text: str,
    *,
    ai: ChessAIOpponent | None = None,
    repository: OpeningRepository | None = None,
    max_plies: int = 80,
) -> dict[str, Any]:
    """Replay a PGN game and produce move classifications, eval graph, and advice."""
    parsed = chess.pgn.read_game(io.StringIO(pgn_text))
    if parsed is None:
        raise ValueError("PGN contains no game.")
    if parsed.errors:
        raise ValueError(f"PGN parse error: {parsed.errors[0]}")

    engine = ai or ChessAIOpponent()
    start_fen = parsed.headers.get("FEN", chess.STARTING_FEN)
    board = chess.Board(start_fen)
    moves = list(parsed.mainline_moves())[:max_plies]
    if not moves:
        raise ValueError("PGN game has no moves to analyze.")

    reviews: list[MoveReview] = []
    eval_graph: list[dict[str, Any]] = [{"ply": 0, "eval_cp_white": 0}]
    white_cpls: list[int] = []
    black_cpls: list[int] = []
    counts = {
        "best": 0,
        "excellent": 0,
        "good": 0,
        "inaccuracy": 0,
        "mistake": 0,
        "blunder": 0,
        "missed_opportunity": 0,
    }
    phase_mistakes = {"opening": 0, "middlegame": 0, "endgame": 0}
    sources_used: set[str] = set()

    for ply, move in enumerate(moves, start=1):
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move at ply {ply}: {move.uci()}")
        side = "white" if board.turn == chess.WHITE else "black"
        sign = 1 if board.turn == chess.WHITE else -1
        phase = _detect_phase(board, ply)
        played_san = board.san(move)

        cands_before, src = engine.analyse_candidates(board, depth=2, time_limit=0.12, multipv=2)
        sources_used.add(src)
        best_cand = cands_before[0] if cands_before else None
        eval_before = (
            best_cand.score_cp_white
            if (best_cand and best_cand.score_cp_white is not None)
            else 0
        )

        board.push(move)
        if board.is_checkmate():
            eval_after = 99000 * sign
        elif board.is_game_over():
            eval_after = 0
        else:
            cands_after, _ = engine.analyse_candidates(board, depth=2, time_limit=0.10, multipv=1)
            eval_after = (
                cands_after[0].score_cp_white
                if (cands_after and cands_after[0].score_cp_white is not None)
                else 0
            )

        # Centipawn loss from mover's POV (clamped to >= 0)
        best_pov = eval_before * sign
        after_pov = eval_after * sign
        is_best = best_cand is not None and best_cand.uci == move.uci()
        cpl = 0 if is_best else max(0, min(1500, best_pov - after_pov))
        missed_win = best_pov >= 250 and after_pov <= 50
        classification = _classify_cpl(cpl, is_best_move=is_best, missed_winning_swing=missed_win)
        counts[classification] += 1
        if classification in {"mistake", "blunder", "missed_opportunity"}:
            phase_mistakes[phase] += 1

        if side == "white":
            white_cpls.append(cpl)
        else:
            black_cpls.append(cpl)

        if classification == "best":
            comment = f"{played_san} matches the engine's top choice."
        elif classification in {"excellent", "good"}:
            comment = f"{played_san} is a solid move ({cpl} cp loss)."
        else:
            alt = f" Consider {best_cand.san} instead." if best_cand else ""
            comment = f"{played_san} is a {classification.replace('_', ' ')} ({cpl} cp loss).{alt}"

        reviews.append(
            MoveReview(
                ply=ply,
                move_number=(ply + 1) // 2,
                side=side,
                played_san=played_san,
                played_uci=move.uci(),
                best_san=best_cand.san if best_cand else None,
                best_uci=best_cand.uci if best_cand else None,
                eval_before_cp_white=max(-1500, min(1500, eval_before)),
                eval_after_cp_white=max(-1500, min(1500, eval_after)),
                centipawn_loss=cpl,
                classification=classification,
                phase=phase,
                comment=comment,
            )
        )
        eval_graph.append({
            "ply": ply,
            "san": played_san,
            "eval_cp_white": max(-1000, min(1000, eval_after)),
        })

    opening_info = None
    if repository is not None and start_fen == chess.STARTING_FEN:
        rec = OpeningRecognizer(repository).recognize(
            [m.uci() for m in moves], notation="uci"
        )
        var = PositionBasedVariationMatcher(repository).match(rec)
        if var.matches:
            opening_info = {
                "name": var.matches[0].name,
                "eco": var.matches[0].eco,
                "variations": list(var.matches[0].variation_labels),
            }

    suggested_lessons: list[str] = []
    if phase_mistakes["opening"] > 0:
        suggested_lessons.append("open-game-first-five")
    if phase_mistakes["middlegame"] > 0:
        suggested_lessons.append("strategy-open-files")
    if phase_mistakes["endgame"] > 0:
        suggested_lessons.append("endgame-opposition-basics")
    if not suggested_lessons:
        suggested_lessons.append("tactics-back-rank-mate")

    critical = [
        asdict(r)
        for r in reviews
        if r.classification in {"mistake", "blunder", "missed_opportunity"}
    ][:6]

    return {
        "evaluation_source": "stockfish" if "stockfish" in sources_used else "knightforge-builtin",
        "disclaimer": (
            "Evaluations come from Stockfish UCI."
            if "stockfish" in sources_used
            else "Stockfish is offline; using KnightForge built-in alpha-beta evaluator."
        ),
        "opening": opening_info,
        "white_accuracy": _accuracy_from_cpls(white_cpls),
        "black_accuracy": _accuracy_from_cpls(black_cpls),
        "classification_counts": counts,
        "phase_mistakes": phase_mistakes,
        "critical_positions": critical,
        "eval_graph": eval_graph,
        "moves": [asdict(r) for r in reviews],
        "suggested_lessons": suggested_lessons,
    }


class ChessCoachAssistant:
    """Interactive AI Chess Coach strictly grounded in rules, tactics, and engine output."""

    def __init__(
        self,
        repository: OpeningRepository,
        ai: ChessAIOpponent | None = None,
    ) -> None:
        self.repository = repository
        self.ai = ai or ChessAIOpponent()

    def advise(
        self,
        fen: str,
        *,
        question: str = "",
        player_level: str = "intermediate",
    ) -> dict[str, Any]:
        """Analyze a real board position and answer the player's question transparently."""
        game = ChessGame(fen)
        board = game.copy_board()
        tactics = TacticalScanner(game).scan()
        positional = (
            analyze_position(game.fen)
            if game.status.value in {"active", "check"}
            else None
        )
        rec = OpeningRecognizer(self.repository).recognize(fen=game.fen)
        var = PositionBasedVariationMatcher(self.repository).match(rec)
        candidates, source = self.ai.analyse_candidates(board, depth=2, time_limit=0.25, multipv=3)

        insights: list[str] = []
        if var.matches:
            m = var.matches[0]
            insights.append(
                f"Opening theory match: {m.name} ({m.eco or 'unclassified'}) — "
                f"variations: {', '.join(m.variation_labels) or 'mainline'}."
            )

        if candidates:
            top = candidates[0]
            score_txt = (
                f"mate in {abs(top.mate_in)}"
                if top.mate_in is not None
                else f"{(top.score_cp_white or 0) / 100:+.2f} (White perspective)"
            )
            insights.append(
                f"Top candidate ({source}): {top.san} [{score_txt}]."
            )

        if tactics.candidates:
            forcing = ", ".join(
                f"{c.san} ({'/'.join(c.motifs)})" for c in tactics.candidates[:3]
            )
            insights.append(f"Immediate forcing moves to calculate: {forcing}.")
        else:
            insights.append("No immediate checks or captures exist; focus on piece improvement.")

        if positional is not None:
            pf = positional["position_features"]
            wp = pf["white_pawns"]["passed"]
            bp = pf["black_pawns"]["passed"]
            if wp or bp:
                insights.append(
                    f"Passed pawns — White: {', '.join(wp) or 'none'} | "
                    f"Black: {', '.join(bp) or 'none'}."
                )
            wo = pf["white_outpost_squares"][:3]
            bo = pf["black_outpost_squares"][:3]
            if wo or bo:
                insights.append(
                    f"Key outpost squares — White: {', '.join(wo) or 'none'} | "
                    f"Black: {', '.join(bo) or 'none'}."
                )

        # Answer specific player question grounded in the facts above
        q = question.strip().lower()
        if "plan" in q or "strategy" in q:
            answer = (
                f"For {game.turn} ({player_level} focus): improve your least active piece, "
                f"contest open files, and consider "
                f"{candidates[0].san if candidates else 'development'}."
            )
        elif "threat" in q or "tactic" in q:
            if tactics.candidates:
                top_t = tactics.candidates[0]
                motifs = ", ".join(top_t.motifs)
                answer = f"Calculate forcing moves first: {top_t.san} ({motifs})."
            else:
                answer = "There are no immediate forcing captures or checks on the board right now."
        elif "endgame" in q:
            answer = (
                "In endgames, activate your king toward the centre, push passed pawns, "
                "and place rooks behind passed pawns."
            )
        else:
            answer = " ".join(insights[:3])

        return {
            "fen": game.fen,
            "turn": game.turn,
            "player_level": player_level,
            "engine_source": source,
            "answer": answer,
            "insights": insights,
            "candidates": [asdict(c) for c in candidates],
            "tactics": [asdict(c) for c in tactics.candidates[:5]],
        }
