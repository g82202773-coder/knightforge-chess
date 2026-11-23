# KnightForge

**Chess education · AI coaching · Opening mastery**

KnightForge is a chess-learning platform for beginners through advanced players. Its goal is to teach not only which move to play, but *why* it works—then turn each learner's mistakes into a focused training plan.

> Project status: **Engine foundation in progress**. The Python package now contains a standard-chess rules wrapper, opening taxonomy and variation-tree validation, provenance-aware knowledge records, and a bounded Stockfish UCI adapter. There is still no playable app, deployed API, bundled Stockfish executable, persistent opening repository, or complete opening/puzzle library.

## Product pillars

- **Chess Academy:** structured lessons in rules, tactics, strategy, openings, calculation, and endgames.
- **Opening Encyclopedia:** organized opening families, move trees, named variations, plans, tactical themes, and practice positions.
- **AI Chess Coach:** engine-grounded move analysis and explanations. The engine supplies legal moves and evaluations; the language model explains them.
- **Tactics Trainer:** validated puzzles, hints, solution lines, and spaced repetition.
- **Progress & Personalization:** skill assessment, mistake patterns, accuracy, and adaptive daily plans.
- **Practice Arena:** legal chess games, adjustable opponents, and themed positions.

## Initial product scope (MVP)

1. Responsive interactive chessboard with complete legal move handling.
2. Beginner learning path and core chess-rules lessons.
3. Tactics trainer with a curated, validated puzzle set.
4. Lesson and puzzle progress tracking.
5. Stockfish-backed position analysis.
6. Explanations grounded in engine output—not invented variations.
7. Responsive web app, designed so an Android client can share the same backend.

The opening encyclopedia will grow in verified, reviewable batches. We will not claim to contain every possible opening branch until coverage is measured and validated.

## Proposed technology

| Layer | Initial direction |
|---|---|
| Web client | Next.js + TypeScript |
| Android client | Kotlin + Jetpack Compose (later client) |
| API | Python + FastAPI |
| Data | PostgreSQL |
| Chess rules / PGN | python-chess on the API; a tested client rules library where needed |
| Engine | Stockfish via UCI |
| AI explanations | LLM grounded in structured engine analysis |
| Tests | Unit, integration, legal-position, and regression tests |

These are proposed defaults, not implemented dependencies yet. We will confirm the first runnable client before generating application code.

## Repository map

- `docs/PRODUCT_SPEC.md` — product scope, modules, MVP acceptance criteria.
- `docs/ARCHITECTURE.md` — system boundaries, data flow, and technical decisions.
- `docs/ROADMAP.md` — staged build and verification plan.

## Development principles

1. **Chess correctness first:** legal move generation, check, checkmate, stalemate, castling, en passant, promotion, repetition, and draw rules must be tested.
2. **Explainable coaching:** never ask an LLM to invent a move or variation; ground coaching in engine output and curated lesson data.
3. **Content provenance:** use licensed or original lessons, puzzles, games, and opening data. Track source and license.
4. **Progressive delivery:** ship a small, testable vertical slice before expanding the curriculum.
5. **Privacy and cost control:** minimize personal data and put explicit limits around expensive AI analysis.

## Current status

- [x] Public GitHub repository created.
- [x] Product, architecture, and roadmap documented.
- [x] Python engine package scaffolded with CI, linting, and automated tests.
- [x] Standard-chess game-state wrapper implemented on python-chess.
- [x] Opening taxonomy reader and legal variation-tree model implemented.
- [x] Versioned opening-tree serialization and position/transposition index implemented.
- [x] Persistent versioned JSON opening repository with atomic writes, validated load, duplicate protection, and ID/name/ECO/alias search.
- [x] Provenance-aware knowledge record model implemented.
- [x] Bounded Stockfish UCI adapter implemented; executable setup and live integration tests remain outstanding.\n- [x] Rules-backed tactical candidate scanner for immediate checks, captures, promotions, and mate-in-one; full tactical search remains a Stockfish responsibility.
- [ ] Add PostgreSQL-backed opening storage when the API/database layer is introduced.
- [x] Add a curated opening import/export workflow with provenance and review checks.
- [ ] Expand rule-edge-case, draw-claim, and Stockfish adapter tests.
- [ ] Select and scaffold the first runnable client and API.
- [ ] Build the first beginner lesson and validated puzzle flow.
- [ ] Add accounts, synchronization, and subscriptions after the core learning loop works.

## License

No project license has been selected yet. Until a license is added, do not assume this repository's code is available for reuse. Third-party engines, libraries, datasets, and content retain their own licenses.
