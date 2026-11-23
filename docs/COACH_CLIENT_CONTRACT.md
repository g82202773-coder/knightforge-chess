# KnightForge Coach Client Contract

The repository currently contains the Python engine package, not a web or
Android application. This document defines the framework-neutral payload that
the future board client should consume. It avoids binding the engine to React,
Next.js, Compose, or a particular API transport.

## One response per move

An API handler should call `AdaptiveOpeningCoach.submit_uci(uci)` and return
`submission_payload(result)` as JSON. The payload contains the move outcome
and the new synchronized board/coach snapshot. The engine analyses the new
position before returning when a `StockfishAnalyzer` is configured.

```python
from knightforge_engine import submission_payload

result = coach.submit_uci("e2e4")
return submission_payload(result)
```

To initialize a board view, return `coach_state_payload(coach.state)`. To
reveal a progressive hint, call `coach.reveal_hint(level)` and return
`coach_state_payload(coach.state)`.

## Payload responsibilities

| Payload path | Client responsibility |
|---|---|
| `board.fen` | Render the authoritative position |
| `board.legal_moves_uci` | Optional legal-move affordances; server remains authoritative |
| `board.highlighted_squares` | Highlight lesson squares |
| `coach.text` | Display the current instruction |
| `coach.voice_script` | Send to a configured text-to-speech service |
| `coach.explanation` | Display the lesson explanation |
| `coach.active_hint` | Display current progressive hint |
| `engine.recommendation_arrow` | Draw the full engine recommendation arrow |
| `coach.active_hint.arrow_from/to` | Draw only the squares disclosed by the current hint |
| `feedback` | Show comparison of the move just submitted |
| `engine.analysis_error` | Show engine-unavailable status without disabling the board |

The client should prefer `coach.active_hint.arrow_from/to` for hint-mode
progressive disclosure. The separate `engine.recommendation_arrow` exposes the
full candidate arrow for analysis or instructor modes; do not display it in a
no-hints mastery test.

## Hint and mode policy

- Guided mode can begin at hint level 1 and reveal levels 2–4 on request.
- Practice mode should reveal hints only after the learner asks.
- Mastery mode should hide `active_hint` and recommendation arrows until the
  attempt is submitted or the configured feedback phase begins.
- The current engine payload is a candidate recommendation, not reviewed
  opening theory and not a centipawn-loss verdict.
- A move not found in the returned candidate list is not automatically a
  blunder. The feedback scope explicitly says candidate-list membership only.

## Suggested API boundary

A future FastAPI layer can expose:
- `POST /sessions` — create a lesson session and return initial state.
- `POST /sessions/{id}/moves` — submit UCI and return
  `submission_payload`.
- `POST /sessions/{id}/hints` — reveal a hint level and return state.
- `POST /sessions/{id}/undo` — undo and return state.
- `POST /sessions/{id}/restart` — restart and return state.

Session storage, authentication, concurrency control, and HTTP endpoints are
not implemented by this engine package. The API must keep each coach session
server-side and serialize access to its mutable state. Never accept a FEN from
the client as proof of session state; the server-owned coach is authoritative.

## Current limits

This is a tested serialization contract, not a rendered chessboard. The
repository still needs a selected client scaffold, a real board component,
API/session lifecycle, and a configured Stockfish executable for live analysis.
