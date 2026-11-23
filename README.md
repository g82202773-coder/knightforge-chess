# KnightForge

**Chess education · AI coaching · Opening mastery**

KnightForge is a chess-learning platform in development for beginners through advanced players. Its goal is to teach not only which move to play, but *why* it works—and turn each learner's mistakes into focused training.

> Project status: **Early playable web demo; not an MVP or production release.** The repository contains a Python chess engine foundation, a FastAPI session server, and a responsive browser chessboard with one short guided lesson. The demo supports legal move selection, Guided/Practice/Mastery modes, progressive lesson hints, undo, restart, and optional Stockfish integration. It does not yet contain a complete curriculum, a comprehensive opening encyclopedia, a curated puzzle trainer, accounts, saved progress, or a deployed public service.

## Product pillars

- **Chess Academy:** structured lessons in rules, tactics, strategy, openings, calculation, and endgames.
- **Opening Encyclopedia:** organized opening families, legal move trees, named variations, plans, tactical themes, and practice positions.
- **AI Chess Coach:** engine-grounded move analysis and explanations. The engine supplies legal moves and evaluations; explanations must remain grounded in that output.
- **Tactics Trainer:** validated puzzles, progressive hints, solution lines, and spaced repetition.
- **Progress & Personalization:** skill assessment, mistake patterns, accuracy, and adaptive training plans.
- **Practice Arena:** legal chess games, adjustable opponents, and themed positions.

## Current runnable demo

The current browser demo is a narrow vertical slice, not the complete product:

- Responsive 8×8 board with server-authoritative legal moves.
- One curated lesson: Open Game / Ruy Lopez introduction (1.e4 e5 2.Nf3 Nc6 3.Bb5).
- Guided, Practice, and Mastery modes.
- Progressive hints, undo, restart, and optional browser speech synthesis.
- FastAPI JSON endpoints for session creation, state, moves, hints, undo, and restart.
- Optional bounded Stockfish analysis when a separately installed executable is configured.

### Run locally

Requires Python 3.11 or newer.

```bash
python -m pip install -e ".[dev,server]"
uvicorn knightforge_engine.server:app --reload
```

Open http://127.0.0.1:8000.

For Stockfish, install a compatible executable separately and set `STOCKFISH_PATH` before starting the server. Without it, the lesson and legal board still work; engine recommendations are unavailable.

See [docs/WEB_CHESSBOARD.md](docs/WEB_CHESSBOARD.md) for API routes and current operational limitations.

## Proposed technology

| Layer | Initial direction |
|---|---|
| Web client | Responsive browser client (current demo); evaluate Next.js + TypeScript for product-scale frontend |
| Android client | Kotlin + Jetpack Compose (later client) |
| API | Python + FastAPI |
| Data | PostgreSQL (not yet implemented) |
| Chess rules / PGN | python-chess |
| Engine | Stockfish via UCI (adapter implemented; live binary integration not verified in CI) |
| Tests | Unit, API, legal-position, regression, and browser end-to-end tests |

## Repository map

- `docs/PRODUCT_SPEC.md` — product scope and acceptance criteria.
- `docs/ARCHITECTURE.md` — system boundaries, data flow, and technical decisions.
- `docs/ROADMAP.md` — staged build and verification plan.
- `docs/WEB_CHESSBOARD.md` — current browser demo, API, and run instructions.
- `src/knightforge_engine/` — chess rules, opening knowledge, coach, analysis, and API.
- `web/` — current browser client.
- `tests/` — automated engine and API tests.

## Development principles

1. **Chess correctness first:** legal move generation, check, checkmate, stalemate, castling, en passant, promotion, repetition, and draw rules must be tested.
2. **Explainable coaching:** never ask an LLM to invent a move or variation; ground coaching in engine output and curated lesson data.
3. **Content provenance:** use licensed or original lessons, puzzles, games, and opening data. Track source and license.
4. **Progressive delivery:** ship a small, testable vertical slice before expanding the curriculum.
5. **Privacy and cost control:** minimize personal data and put explicit limits around expensive AI analysis.

## Current status

- [x] Public GitHub repository and product/architecture/roadmap documentation.
- [x] Python engine package, linting, and automated CI.
- [x] Standard-chess game-state wrapper using python-chess.
- [x] Opening taxonomy, legal variation-tree model, serialization, and transposition index.
- [x] Persistent versioned JSON opening repository with atomic writes and validation.
- [x] Provenance-aware knowledge records and curated opening import/export workflow.
- [x] Bounded Stockfish UCI adapter; a real Stockfish executable has not yet been verified in CI.
- [x] Rules-backed immediate tactical candidate scanner; not a full tactical search.
- [x] FastAPI session API and early browser chessboard demo.
- [x] Guided, Practice, and Mastery hint-disclosure policies with API regression tests.
- [ ] Browser end-to-end tests on desktop and mobile.
- [ ] Persistent, expiring sessions and production-grade storage.
- [ ] Expand chess-rule edge-case and draw-claim coverage.
- [ ] Complete beginner rules curriculum and knowledge checks.
- [ ] Curated, validated tactics/puzzle trainer.
- [ ] Expand opening coverage with deeply nested, reviewed variations.
- [ ] Middlegame, calculation, endgame, and checkmate-pattern courses.
- [ ] Saved games, learner progress, diagnostic assessment, and adaptive plans.
- [ ] Game analysis and practice against a computer.
- [ ] Production security, accessibility, performance, and deployment review.
- [ ] Android client after the web learning loop is validated.

## Release discipline

A green CI run means the automated checks in that workflow passed; it does not mean the product is complete, deployed, or verified on real phones. Features are only marked complete after implementation and appropriate tests. The current server uses an in-memory, process-local session store and is intended for local development only. Do not expose it as a public multi-user service without session expiry, shared storage, authentication, rate limiting, and a security review.

## License

No project license has been selected yet. Until a license is added, do not assume this repository's code is available for reuse. Third-party engines, libraries, datasets, and content retain their own licenses.
