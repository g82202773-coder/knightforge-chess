"""Stable JSON-ready presentation payloads for web and mobile chess clients.

This module contains no UI framework or transport dependency. API handlers can
return these dictionaries directly as JSON responses.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .adaptive_coach import OpeningCoachState, OpeningCoachSubmission


def coach_state_payload(state: OpeningCoachState) -> dict[str, Any]:
    """Serialize one atomic coach snapshot for a board client."""
    prompt = state.prompt
    recommendation = state.recommendation
    hint = state.active_hint
    comparison = state.move_comparison

    return {
        "board": {
            "fen": state.fen,
            "turn": prompt.turn,
            "game_status": prompt.game_status,
            "legal_moves_uci": list(prompt.legal_moves_uci),
            "highlighted_squares": list(prompt.highlighted_squares),
        },
        "coach": {
            "kind": prompt.kind,
            "text": prompt.text,
            "voice_script": prompt.voice_script,
            "explanation": prompt.explanation,
            "knowledge_status": state.knowledge_status,
            "expected_move": {
                "uci": prompt.expected_uci,
                "san": prompt.expected_san,
                "arrow": (
                    {"from": prompt.arrow_from, "to": prompt.arrow_to}
                    if prompt.arrow_from and prompt.arrow_to
                    else None
                ),
            },
            "active_hint": asdict(hint) if hint is not None else None,
            "mistake_feedback": (
                asdict(prompt.mistake_feedback)
                if prompt.mistake_feedback is not None
                else None
            ),
        },
        "engine": {
            "recommendation": asdict(recommendation) if recommendation is not None else None,
            "recommendation_arrow": (
                {"from": state.recommendation_arrow[0], "to": state.recommendation_arrow[1]}
                if state.recommendation_arrow is not None
                else None
            ),
            "analysis_error": state.analysis_error,
        },
        "feedback": asdict(comparison) if comparison is not None else None,
    }


def submission_payload(submission: OpeningCoachSubmission) -> dict[str, Any]:
    """Serialize the move outcome and its immediately refreshed coach snapshot."""
    move = submission.submission
    return {
        "move": {
            "accepted": move.accepted,
            "correct": move.correct,
            "applied": move.applied,
            "actual_san": move.actual_san,
            "message": move.message,
        },
        "state": coach_state_payload(submission.state),
    }
