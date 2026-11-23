"""Evidence-grounded coaching decisions from engine candidate lines.

Engine rankings and scores are kept explicitly separate from reviewed chess
knowledge. Move comparisons require analysis of the exact pre-move position.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from .analysis import AnalysisResult, EngineLine

_PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


@dataclass(frozen=True, slots=True)
class CoachHint:
    """One progressively more explicit hint."""

    level: int
    text: str
    arrow_from: str | None = None
    arrow_to: str | None = None
    reveal_uci: str | None = None


@dataclass(frozen=True, slots=True)
class EngineRecommendation:
    """A legal first move plus facts derived from its position and PV."""

    uci: str
    san: str
    piece: str
    from_square: str
    to_square: str
    captured_piece: str | None
    gives_check: bool
    is_checkmate: bool
    promotion: str | None
    principal_variation_uci: tuple[str, ...]
    principal_variation_san: tuple[str, ...]
    engine_rank: int
    engine_score_cp: int | None
    engine_score_mate: int | None
    score_perspective: str
    evaluation_disclaimer: str
    hints: tuple[CoachHint, ...]


@dataclass(frozen=True, slots=True)
class MoveComparison:
    """Compare a learner move to candidates searched from the same position."""

    played_uci: str
    played_san: str
    best_uci: str
    best_san: str
    matched_candidate_rank: int | None
    is_engine_top_choice: bool
    engine_top_choice: str
    explanation: str
    analysis_fen: str
    comparison_scope: str


class CoachDecisionLayer:
    """Turn bounded engine output into cautious, beginner-readable guidance.

    This class does not infer strategic principles from centipawn scores. It
    reports concrete board facts and labels engine evaluations as search output.
    """

    EVALUATION_DISCLAIMER = (
        "This is the engine's evaluation of this position, not a win probability "
        "or a proven chess principle."
    )

    def __init__(self, analysis: AnalysisResult) -> None:
        try:
            board = chess.Board(analysis.fen)
        except ValueError as exc:
            raise ValueError(f"Analysis contains an invalid FEN: {exc}") from exc
        if not board.is_valid():
            raise ValueError("Analysis FEN describes an invalid chess position.")
        if not analysis.lines:
            raise ValueError("Analysis must contain at least one candidate line.")
        if board.is_game_over():
            raise ValueError("Cannot create a move recommendation for a finished position.")
        self.analysis = analysis
        self._board = board
        self._recommendations = self._build_recommendations()

    @property
    def recommendations(self) -> tuple[EngineRecommendation, ...]:
        """All validated engine candidates, in engine-provided rank order."""
        return self._recommendations

    @property
    def best(self) -> EngineRecommendation:
        """The highest-ranked legal engine candidate."""
        return self._recommendations[0]

    def compare_move(self, played_uci: str, *, position_fen: str) -> MoveComparison:
        """Compare a move made from the exact position that was analysed.

        The caller must provide the pre-move FEN. Comparing against a later
        position would be invalid and is rejected.
        """
        try:
            before = chess.Board(position_fen)
        except ValueError as exc:
            raise ValueError(f"Invalid pre-move FEN: {exc}") from exc
        if not before.is_valid():
            raise ValueError("Pre-move FEN describes an invalid chess position.")
        if before.fen() != self._board.fen():
            raise ValueError(
                "Move comparison requires analysis and learner move from the same position."
            )
        try:
            move = chess.Move.from_uci(played_uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {played_uci}") from exc
        if move not in before.legal_moves:
            raise ValueError(f"Learner move is not legal in the analysed position: {played_uci}")

        played_san = before.san(move)
        matched = next(
            (item for item in self._recommendations if item.uci == move.uci()),
            None,
        )
        if matched is not None:
            rank = matched.engine_rank
            if rank == 1:
                explanation = (
                    f"{played_san} matches the engine's top-ranked candidate "
                    "in this analysed position."
                )
            else:
                explanation = (
                    f"{played_san} appears at engine rank {rank} among the returned "
                    "candidates; it is not the top-ranked candidate."
                )
        else:
            rank = None
            explanation = (
                f"{played_san} is legal, but it is not among the returned engine "
                "candidates. This analysis alone does not prove the move is a blunder."
            )
        return MoveComparison(
            played_uci=move.uci(),
            played_san=played_san,
            best_uci=self.best.uci,
            best_san=self.best.san,
            matched_candidate_rank=rank,
            is_engine_top_choice=rank == 1,
            engine_top_choice=self.best.san,
            explanation=explanation,
            analysis_fen=self._board.fen(),
            comparison_scope="candidate-list membership only; no move-loss estimate",
        )

    def _build_recommendations(self) -> tuple[EngineRecommendation, ...]:
        output: list[EngineRecommendation] = []
        seen: set[str] = set()
        for line in sorted(self.analysis.lines, key=lambda item: item.multipv):
            recommendation = self._recommendation(line)
            if recommendation is None or recommendation.uci in seen:
                continue
            seen.add(recommendation.uci)
            output.append(recommendation)
        if not output:
            raise ValueError("Analysis contains no legal first move candidates.")
        return tuple(output)

    def _recommendation(self, line: EngineLine) -> EngineRecommendation | None:
        if not line.moves_uci:
            return None
        try:
            moves = [chess.Move.from_uci(value) for value in line.moves_uci]
        except ValueError as exc:
            raise ValueError("Engine line contains malformed UCI notation.") from exc
        board = self._board.copy()
        san_moves: list[str] = []
        for move in moves:
            if move not in board.legal_moves:
                raise ValueError("Engine line contains an illegal move sequence.")
            san_moves.append(board.san(move))
            board.push(move)

        first = moves[0]
        moving = self._board.piece_at(first.from_square)
        if moving is None:
            raise ValueError("Engine candidate has no moving piece.")
        captured = self._board.piece_at(first.to_square)
        if self._board.is_en_passant(first):
            captured = chess.Piece(chess.PAWN, not moving.color)
        after = self._board.copy()
        after.push(first)
        piece = _PIECE_NAMES[moving.piece_type]
        source = chess.square_name(first.from_square)
        target = chess.square_name(first.to_square)
        hints = (
            CoachHint(
                1,
                f"Look for a useful move with your {piece}.",
            ),
            CoachHint(
                2,
                f"Find your {piece} on {source.upper()}.",
                arrow_from=source,
            ),
            CoachHint(
                3,
                f"Move the {piece} from {source.upper()} to {target.upper()}.",
                arrow_from=source,
                arrow_to=target,
            ),
            CoachHint(
                4,
                f"Play {san_moves[0]} ({source.upper()} to {target.upper()}).",
                arrow_from=source,
                arrow_to=target,
                reveal_uci=first.uci(),
            ),
        )
        return EngineRecommendation(
            uci=first.uci(),
            san=self._board.san(first),
            piece=piece,
            from_square=source,
            to_square=target,
            captured_piece=_PIECE_NAMES[captured.piece_type] if captured else None,
            gives_check=after.is_check(),
            is_checkmate=after.is_checkmate(),
            promotion=(
                _PIECE_NAMES[first.promotion] if first.promotion is not None else None
            ),
            principal_variation_uci=tuple(move.uci() for move in moves),
            principal_variation_san=tuple(san_moves),
            engine_rank=line.multipv,
            engine_score_cp=line.score_cp,
            engine_score_mate=line.score_mate,
            score_perspective="side to move in the analysed position",
            evaluation_disclaimer=self.EVALUATION_DISCLAIMER,
            hints=hints,
        )
