# Architecture Notes

## 1. Proposed system

- **Web:** Next.js + TypeScript responsive client.
- **Android:** Kotlin + Jetpack Compose client, introduced after API contracts stabilize.
- **API:** Python + FastAPI.
- **Database:** PostgreSQL.
- **Chess rules and notation:** python-chess in backend services for move validation, FEN/PGN parsing, and engine communication. Any client-side move preview must be reconciled with authoritative server validation.
- **Engine:** Stockfish using UCI. Keep engine execution behind a service boundary.
- **AI explanation:** LLM receives a bounded, structured analysis payload and lesson context. It does not decide legality or invent principal variations.

This is a proposed architecture. No dependencies or services have been deployed yet.

## 2. Main backend domains

- Identity and profiles
- Course catalogue and lesson content
- Openings and variation trees (implemented foundation: validated move trees, position/transposition index, and local versioned JSON persistence)
- Puzzle catalogue and attempts
- Games, positions, FEN, and PGN
- Engine analysis jobs
- Coach explanations
- Learning plans and spaced repetition
- Subscription entitlements and usage limits

## 3. Trust boundaries

1. The chess-rules library is authoritative for legal moves and game state.
2. Stockfish is authoritative for the engine evaluation it actually returns, subject to depth/time settings.
3. Curated content is versioned and reviewed before publication.
4. The LLM is an explanation layer only; validate its references against the supplied position and engine lines.
5. Client input is untrusted. Validate FEN, PGN, move requests, identity, and entitlements on the server.

## 4. Initial data entities

- User(id, created_at, locale)
- LearnerProfile(user_id, rating_band, goals, preferences)
- Course(id, title, level, version, status)
- Lesson(id, course_id, sequence, content, objectives)
- Opening(id, name, eco, family, side, source_id, review_status)
- OpeningLine(id, opening_id, parent_line_id, uci_move, san, explanation)
- Puzzle(id, fen, solution, themes, difficulty, source_id, review_status)
- PuzzleAttempt(id, user_id, puzzle_id, result, elapsed_ms, hints_used, created_at)
- Game(id, user_id, initial_fen, pgn, result, created_at)
- AnalysisJob(id, position_fen, engine_version, limits, result_json, status)
- LearningEvent(id, user_id, event_type, reference_id, outcome, created_at)

Schema details will be refined before migrations are written.

### Current opening persistence boundary

The engine currently persists validated opening trees in a versioned JSON document using atomic file replacement. It supports stable-ID lookup, case-insensitive search by ID/name/ECO/alias, duplicate rejection, and re-validation on load. This adapter is deliberately single-process/single-writer; it is suitable for local development and early content authoring, not concurrent multi-worker production. PostgreSQL remains the intended transactional store when the API/database phase begins. The move-order tree remains the canonical authored variation structure; the position index connects transpositions without discarding opening identity or move-order context.

## 5. Key API concepts

- GET /courses
- GET /courses/{course_id}
- GET /lessons/{lesson_id}
- GET /openings and GET /openings/{opening_id}
- POST /positions/validate
- POST /puzzles/{puzzle_id}/attempts
- POST /games and POST /games/{game_id}/moves
- POST /analysis
- GET /learners/me/progress
- GET /learners/me/daily-plan

These are conceptual routes, not implemented endpoints.

## 6. Engine-analysis flow

1. Validate and normalize the incoming FEN.
2. Check request quotas and enqueue an analysis job.
3. Run Stockfish with explicit time/depth and MultiPV limits.
4. Store engine version, options, depth, nodes, score, principal variations, and completion status.
5. Pass only this structured result and relevant lesson context to the explanation layer.
6. Validate returned move references against the supplied analysis before showing them.
7. Return analysis and explanation with clear limits and provenance.

## 7. Non-functional requirements

- Chess correctness and regression tests are release blockers.
- Add request limits, job timeouts, and queue back-pressure for engine/LLM workloads.
- Avoid storing unnecessary personal data.
- Use secure authentication, authorization, secret management, and verified billing entitlements.
- Support graceful offline lesson access as a later feature.
- Monitor API latency, engine cost, LLM cost, errors, and learning outcomes.

## 8. Decisions still open

- First client to scaffold: web-first is recommended for fastest iteration; Android follows using the same API.
- Authentication provider and deployment target.
- Puzzle and opening data sources and licenses.
- Engine execution environment and concurrency limits.
- AI provider, budget, and per-user quotas.
