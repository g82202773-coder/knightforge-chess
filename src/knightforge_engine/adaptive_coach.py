"""Adaptive opening-coach orchestration over reviewed knowledge and live decisions.

Reviewed lesson/opening data remains authoritative for theory. Optional bounded
engine analysis supplies position-specific move guidance and comparisons.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import chess
import chess.engine

from .analysis import AnalysisResult, StockfishAnalyzer
from .coach_decision import (
    CoachDecisionLayer,
    CoachHint,
    EngineRecommendation,
    MoveComparison,
)
from .guided_learning import CoachPrompt, GuidedLesson, GuidedLessonSession, MoveSubmission
from .opening_recognition import OpeningRecognition, OpeningRecognizer
from .opening_repository import OpeningRepository
from .variation_matching import PositionBasedVariationMatcher, VariationMatchResult


@dataclass(frozen=True, slots=True)
class OpeningCoachState:
    """One synchronized board, lesson, opening, and engine-guidance snapshot."""

    fen: str
    prompt: CoachPrompt
    recognition: OpeningRecognition
    variation_match: VariationMatchResult
    knowledge_status: str
    recommendation: EngineRecommendation | None = None
    active_hint: CoachHint | None = None
    move_comparison: MoveComparison | None = None
    analysis_error: str | None = None

    @property
    def recommendation_arrow(self) -> tuple[str, str] | None:
        """Full recommended arrow for clients that choose to render it."""
        if self.recommendation is None:
            return None
        return (self.recommendation.from_square, self.recommendation.to_square)


@dataclass(frozen=True, slots=True)
class OpeningCoachSubmission:
    """Move result plus the refreshed adaptive coach state."""

    submission: MoveSubmission
    state: OpeningCoachState


class AdaptiveOpeningCoach:
    """Position-aware coach with automatic, bounded engine guidance.

    If an analyzer is configured, the current position is analysed when the
    coach is created and again immediately after each applied move. The cached
    decision for the pre-move position is used to compare that move, avoiding
    the invalid practice of comparing it against a post-move analysis.

    Reviewed lesson/opening knowledge remains separate from engine candidates:
    engine lines are coaching suggestions, never silently promoted to theory.
    """

    def __init__(
        self,
        lesson: GuidedLesson,
        repository: OpeningRepository,
        analyzer: StockfishAnalyzer | None = None,
        *,
        analysis_time_limit: float = 1.0,
        analysis_depth: int | None = None,
        analysis_multipv: int = 3,
    ) -> None:
        if not isinstance(repository, OpeningRepository):
            raise TypeError("repository must be an OpeningRepository.")
        if not 0.05 <= analysis_time_limit <= 30.0:
            raise ValueError("analysis_time_limit must be between 0.05 and 30 seconds.")
        if analysis_depth is not None and not 1 <= analysis_depth <= 40:
            raise ValueError("analysis_depth must be between 1 and 40.")
        if not 1 <= analysis_multipv <= 5:
            raise ValueError("analysis_multipv must be between 1 and 5.")
        self.session = GuidedLessonSession(lesson)
        self.repository = repository
        self.analyzer = analyzer
        self.analysis_time_limit = analysis_time_limit
        self.analysis_depth = analysis_depth
        self.analysis_multipv = analysis_multipv
        self.recognizer = OpeningRecognizer(repository)
        self.matcher = PositionBasedVariationMatcher(repository)
        self._decision: CoachDecisionLayer | None = None
        self._analysis_error: str | None = None
        self._last_comparison: MoveComparison | None = None
        self.state = self._build_state()

    def prompt(self) -> OpeningCoachState:
        """Return the latest snapshot without resetting progressive hint state.

        State is rebuilt only after a position-changing or analysis operation.
        Rebuilding on every read would silently reset a learner's revealed hint
        back to level one whenever an API handler serialized the session.
        """
        return self.state

    def submit_uci(self, uci: str) -> OpeningCoachSubmission:
        """Apply a move, compare it to pre-move analysis, then coach the new position."""
        before_fen = self.session.game.fen
        comparison = None
        if self._decision is not None:
            comparison = self._decision.compare_move(uci, position_fen=before_fen)

        result = self.session.submit_uci(uci)
        self._last_comparison = comparison
        if result.applied:
            # Analyse the new position once; this becomes the cached decision
            # used to compare the next submitted move.
            self._decision = None
            self._analysis_error = None
        state = self._build_state()
        if not result.submission.applied and result.submission.prompt.kind == "correction":
            # Preserve the attempted-move explanation in the public session snapshot.
            state = replace(state, prompt=result.submission.prompt)
        self.state = state
        return OpeningCoachSubmission(result, state)

    def reveal_hint(self, level: int) -> OpeningCoachState:
        """Reveal one of the current recommendation's four progressive hints."""
        if not 1 <= level <= 4:
            raise ValueError("Hint level must be between 1 and 4.")
        if self._decision is not None:
            hint = self._decision.best.hints[level - 1]
        else:
            # A curated lesson already contains a validated next move. Use it
            # for progressive hints when Stockfish is unavailable; do not
            # pretend this lesson-derived hint is an engine recommendation.
            prompt = self.session.prompt()
            if prompt.expected_uci is None:
                raise RuntimeError(
                    "No lesson move or engine recommendation is available for this position."
                )
            board = self.session.game.copy_board()
            move = chess.Move.from_uci(prompt.expected_uci)
            piece = board.piece_at(move.from_square)
            if piece is None:
                raise RuntimeError("The lesson move has no moving piece.")
            piece_name = chess.piece_name(piece.piece_type)
            source = chess.square_name(move.from_square)
            target = chess.square_name(move.to_square)
            san = board.san(move)
            lesson_hints = (
                CoachHint(1, f"Look for a useful move with your {piece_name}."),
                CoachHint(2, f"Find your {piece_name} on {source.upper()}.",
                          arrow_from=source),
                CoachHint(3, f"Move the {piece_name} from {source.upper()} to {target.upper()}.",
                          arrow_from=source, arrow_to=target),
                CoachHint(4, f"Play {san} ({source.upper()} to {target.upper()}).",
                          arrow_from=source, arrow_to=target, reveal_uci=move.uci()),
            )
            hint = lesson_hints[level - 1]
        self.state = replace(self.state, active_hint=hint)
        return self.state

    def analyze_deviation(
        self,
        *,
        time_limit: float = 1.0,
        depth: int | None = None,
        multipv: int = 3,
    ) -> AnalysisResult:
        """Explicitly re-analyse a deviation with caller-selected bounded limits."""
        if self.session.prompt().kind != "opponent_deviation":
            raise RuntimeError("Stockfish analysis is only available after an opponent deviation.")
        if self.analyzer is None:
            raise RuntimeError("No Stockfish analyzer configured for this coach.")
        result = self.analyzer.analyse(
            self.session.game.fen,
            time_limit=time_limit,
            depth=depth,
            multipv=multipv,
        )
        self._set_decision(result)
        self.state = self._build_state(analyse=False)
        return result

    def undo(self) -> OpeningCoachState:
        self.session.undo()
        self._last_comparison = None
        self._decision = None
        self._analysis_error = None
        self.state = self._build_state()
        return self.state

    def restart(self) -> OpeningCoachState:
        self.session.restart()
        self._last_comparison = None
        self._decision = None
        self._analysis_error = None
        self.state = self._build_state()
        return self.state

    def _set_decision(self, analysis: AnalysisResult) -> None:
        decision = CoachDecisionLayer(analysis)
        if decision.analysis.fen != self.session.game.fen:
            raise ValueError("Engine analysis must match the coach's current position.")
        self._decision = decision
        self._analysis_error = None

    def _build_state(self, *, analyse: bool = True) -> OpeningCoachState:
        board = self.session.game.copy_board()
        if analyse and self.analyzer is not None and self._decision is None:
            if not board.is_game_over():
                try:
                    result = self.analyzer.analyse(
                        board.fen(),
                        time_limit=self.analysis_time_limit,
                        depth=self.analysis_depth,
                        multipv=self.analysis_multipv,
                    )
                    self._set_decision(result)
                except (OSError, RuntimeError, ValueError, chess.engine.EngineError) as exc:
                    # Keep lesson play usable if the optional engine is offline
                    # or returns unusable output; surface the failure in state.
                    self._analysis_error = f"{type(exc).__name__}: {exc}"
            else:
                self._analysis_error = "The game is over; no move recommendation is available."

        if self.session.lesson.starting_fen == chess.STARTING_FEN:
            recognition = self.recognizer.recognize(
                [move.uci() for move in board.move_stack], notation="uci"
            )
        else:
            # A custom lesson start has no implied standard-game move history.
            recognition = self.recognizer.recognize(fen=board.fen())
        variation_match = self.matcher.match(recognition)
        if any(
            len(match.matched_line_uci) > len(self.repository.get(match.opening_id).anchor_uci)
            for match in variation_match.matches
            if self.repository.get(match.opening_id) is not None
        ):
            status = "reviewed_variation_match"
        elif recognition.matches:
            status = "reviewed_opening_anchor_only"
        else:
            status = "no_reviewed_match"
        recommendation = self._decision.best if self._decision is not None else None
        return OpeningCoachState(
            fen=board.fen(),
            prompt=self.session.prompt(),
            recognition=recognition,
            variation_match=variation_match,
            knowledge_status=status,
            recommendation=recommendation,
            active_hint=recommendation.hints[0] if recommendation else None,
            move_comparison=self._last_comparison,
            analysis_error=self._analysis_error,
        )
