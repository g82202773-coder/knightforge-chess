"""Adaptive opening-coach orchestration over reviewed KnightForge knowledge.

This layer joins legal lesson execution, opening recognition, and deepest
position-based variation matching. It deliberately does not invent theory.
"""
from __future__ import annotations

from dataclasses import dataclass

import chess

from .guided_learning import CoachPrompt, GuidedLesson, GuidedLessonSession, MoveSubmission
from .opening_recognition import OpeningRecognition, OpeningRecognizer
from .opening_repository import OpeningRepository
from .variation_matching import PositionBasedVariationMatcher, VariationMatchResult


@dataclass(frozen=True, slots=True)
class OpeningCoachState:
    """One synchronized snapshot for a board, lesson prompt, and knowledge match."""

    fen: str
    prompt: CoachPrompt
    recognition: OpeningRecognition
    variation_match: VariationMatchResult
    knowledge_status: str


@dataclass(frozen=True, slots=True)
class OpeningCoachSubmission:
    """Move result plus the refreshed adaptive coach state."""

    submission: MoveSubmission
    state: OpeningCoachState


class AdaptiveOpeningCoach:
    """Position-aware coach that only teaches lines supported by reviewed trees.

    The lesson tree remains the source of expected learner moves. The opening
    repository independently identifies the current opening/variation. When a
    position is outside reviewed content, the state says so instead of
    manufacturing an explanation or continuation.
    """

    def __init__(self, lesson: GuidedLesson, repository: OpeningRepository) -> None:
        if not isinstance(repository, OpeningRepository):
            raise TypeError("repository must be an OpeningRepository.")
        self.session = GuidedLessonSession(lesson)
        self.repository = repository
        self.recognizer = OpeningRecognizer(repository)
        self.matcher = PositionBasedVariationMatcher(repository)
        self.state = self._build_state()

    def prompt(self) -> OpeningCoachState:
        """Return the latest board-aware coach and knowledge snapshot."""
        self.state = self._build_state()
        return self.state

    def submit_uci(self, uci: str) -> OpeningCoachSubmission:
        """Submit a legal move and refresh recognition/variation context."""
        result = self.session.submit_uci(uci)
        state = self._build_state()
        self.state = state
        return OpeningCoachSubmission(result, state)

    def undo(self) -> OpeningCoachState:
        self.session.undo()
        self.state = self._build_state()
        return self.state

    def restart(self) -> OpeningCoachState:
        self.session.restart()
        self.state = self._build_state()
        return self.state

    def _build_state(self) -> OpeningCoachState:
        board = self.session.game.copy_board()
        if self.session.lesson.starting_fen == chess.STARTING_FEN:
            recognition = self.recognizer.recognize(
                [move.uci() for move in board.move_stack], notation="uci"
            )
        else:
            # A custom lesson start has no implied standard-game move history.
            recognition = self.recognizer.recognize(fen=board.fen())
        variation_match = self.matcher.match(recognition)
        if variation_match.matches:
            status = "reviewed_variation_match"
        elif recognition.matches:
            status = "reviewed_opening_anchor_only"
        else:
            status = "no_reviewed_match"
        return OpeningCoachState(
            fen=board.fen(),
            prompt=self.session.prompt(),
            recognition=recognition,
            variation_match=variation_match,
            knowledge_status=status,
        )
