# Build Roadmap

## Phase 0 — Foundation
- [x] Create repository and document product direction.
- [x] Define system boundaries and chess-correctness principles.
- [ ] Confirm web-first or Android-first implementation.
- [ ] Select licensed opening and puzzle data sources.

## Phase 1 — First playable vertical slice
- Scaffold the chosen client and API.
- Render a responsive chessboard.
- Integrate a proven chess-rules library.
- Support legal moves, promotion, castling, en passant, check, and terminal states.
- Add move list, undo, restart, FEN, and PGN.
- Add automated rules tests.

**Exit gate:** a user can play a complete legal game locally, and the rules regression suite passes.

## Phase 2 — First learning loop
- Build beginner lessons with objectives and knowledge checks.
- Add a small, manually reviewed tactics set.
- Add hints, validated solutions, and feedback.
- Persist lesson and puzzle progress.

**Exit gate:** a learner can complete a lesson, solve puzzles, and see accurate progress.

## Phase 3 — Engine-grounded coaching
- Integrate Stockfish through UCI.
- Add bounded position analysis and candidate lines.
- Generate explanations grounded in engine output.
- Record mistakes and map them to training themes.

**Exit gate:** engine results are reproducible, and coach explanations never override legal chess state.

## Phase 4 — Personalization and content expansion
- Add diagnostic assessment and adaptive plans.
- Add spaced repetition.
- Expand opening families and variations in reviewed batches.
- Add deeper endgame and positional courses.

## Phase 5 — Accounts, Android, and launch readiness
- Stabilize API contracts and authentication.
- Add Android client and cross-device sync.
- Add subscription entitlements and transparent usage limits.
- Complete privacy, security, accessibility, performance, and licensing reviews.
- Run a closed beta and fix measured issues.

Dates are intentionally not promised until implementation scope, contributors, and hosting constraints are known.
