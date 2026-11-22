# KnightForge — Complete Product Roadmap

**Product direction:** a full chess academy, practice environment, opening encyclopedia, and engine-grounded personal coach for Android and the web.

**Planning status:** this document defines the intended product and build order. A checked item means completed and verified in the repository; planned features are not implemented merely because they appear here.

---

## 1. Product decisions

| Decision | Direction |
|---|---|
| Product | KnightForge — chess learning and improvement platform |
| Audience | Absolute beginners through advanced and tournament players |
| Platforms | Responsive web first; Android app second; shared backend and account |
| Core promise | Teach the reasoning behind moves and turn mistakes into better training |
| Chess correctness | A tested chess-rules library is authoritative for legal moves and game state |
| Engine | Stockfish through UCI for evaluation and candidate lines |
| AI coach | Explains validated engine output; never invents legal moves or variations |
| Content | Original, licensed, or permissioned material with provenance and review |
| Delivery | Small tested releases; expand only after each milestone passes its exit gate |
| Business model | Useful free tier plus optional Premium; pricing and AI allowances decided after cost and user testing |

### What we will not promise

- We will not claim to include literally every possible opening branch. Opening trees are vast and constantly expanded. We will build a broad, clearly scoped, reviewed encyclopedia and publish coverage transparently.
- We will not call an AI-generated chess line correct unless it has been checked against the rules engine and, where relevant, engine analysis.
- We will not promise unlimited AI analysis before measuring infrastructure and inference costs.
- We will not copy paid courses, proprietary puzzle sets, or annotated games without permission.

---

## 2. Complete feature map

### A. Home and learner dashboard
- Today’s training plan and continue-learning action.
- Quick access to Play, Learn, Puzzles, Openings, Analysis, and Profile.
- Current level, progress, streak, recent games, and recommended next lesson.
- Clear free/Premium usage balance where applicable.

### B. Chess play and board
- Responsive board with coordinates, legal-move highlights, last-move highlight, check indicator, and accessible piece controls.
- Complete standard chess rules: legal moves, check, checkmate, stalemate, castling, en passant, promotion, repetition, 50/75-move rules, and insufficient material.
- Move list in SAN, FEN and PGN import/export.
- Undo/review for practice games, restart, board flip, sound and display settings.
- Local two-player play first; computer opponent and online play later.
- Game clocks and time controls when game modes are introduced.
- Resign, offer/claim draw, and clear game-result handling.

### C. Chess Academy — structured curriculum
1. **Absolute basics:** board, coordinates, pieces, legal moves, captures, check, checkmate, stalemate, castling, en passant, promotion, notation and draw rules.
2. **Opening principles:** center, development, king safety, tempo, opening traps and common beginner errors.
3. **Tactics:** forks, pins, skewers, discovered attacks, double checks, discovered checks, deflection, decoy, clearance, interference, zwischenzug, attraction, overloading, removing the defender, mating nets and defensive resources.
4. **Strategy and positional play:** pawn structure, weak squares, outposts, open files, good/bad bishops, knights versus bishops, space, initiative, piece activity, exchanges and plans.
5. **Calculation and visualization:** candidate moves, forcing moves, checks/captures/threats, variations, move ordering, blunder-checking and visualization.
6. **Middlegame:** attack, defence, king safety, open/closed positions, transitions and planning.
7. **Endgames:** king-and-pawn, opposition, triangulation, passed pawns, rook endings, minor-piece endings, queen endings, fortresses and theoretical draws.
8. **Checkmate patterns:** back-rank, smothered, Arabian, Anastasia, Boden, Greek gift patterns, corridor mates and common mating nets.
9. **Gambits and traps:** soundness, compensation, common traps, refutations and practical decision-making.
10. **Tournament preparation:** time management, notation, touch-move, formats, preparation routines and post-game review.
11. **Advanced study:** positional exchange sacrifices, prophylaxis, defensive resources, advanced calculation and preparation with engines.

Every course should have level, prerequisites, objectives, lessons, examples, exercises, review questions, and a completion test.

### D. Opening Encyclopedia and repertoire builder
- Browse by White openings, Black defences, opening family, ECO code, first move, name, and difficulty.
- Include open games, semi-open games, closed games, Indian defences, flank openings, gambits, sidelines and anti-systems.
- Representative families to cover include:
  - **1.e4 e5:** Italian Game, Ruy Lopez, Scotch, King's Gambit, Vienna, Four Knights, Petrov, Philidor and related systems.
  - **Sicilian Defence:** Open Sicilian, Najdorf, Dragon (Classical, Yugoslav, Soltis and other recognized branches), Accelerated Dragon, Scheveningen, Sveshnikov, Kalashnikov, Taimanov, Kan, Classical, Alapin, Rossolimo, Moscow, Closed Sicilian and Smith-Morra.
  - **Other semi-open defences:** French (Winawer, Classical, Tarrasch, Advance), Caro-Kann (Advance, Classical, Exchange, Panov-Botvinnik), Pirc, Modern, Scandinavian, Alekhine, Nimzowitsch and Owen's Defence.
  - **Queen's pawn and Indian systems:** Queen's Gambit Accepted/Declined/Exchange, Slav, Semi-Slav, King's Indian, Grünfeld, Nimzo-Indian, Queen's Indian, Bogo-Indian, Benoni, Benko, Dutch, Budapest, London, Torre, Trompowsky, Colle and Blackmar-Diemer.
  - **Flank systems:** English, Réti, King's Indian Attack, Bird, Larsen, Polish and fianchetto systems.
- Each opening page: identity, move tree, main line, important named variations, transpositions, plans for both sides, typical pawn structures, tactical motifs, common mistakes, traps and refutations, model positions, and training drills.
- Repertoire builder: save a White and Black repertoire, mark lines as learned, add personal notes, and test recall.
- Opening explorer: navigate legal continuations and compare lines. Engine evaluation is labelled with engine/version and search settings.
- Coverage is expanded in curated batches; every published line is legal, sourced, and reviewed.

### E. Tactics and calculation trainer
- Puzzle themes, rating/difficulty bands, daily puzzle, themed sets and mixed practice.
- Hints that reveal graduated guidance rather than the full answer immediately.
- Multi-move solutions, alternative accepted lines, and explicit fail states.
- Track accuracy, time, hints, retries and recurring error themes.
- Adaptive puzzle selection and spaced repetition.
- Puzzle provenance, validation status and review workflow.

### F. AI Chess Coach and game analysis
- Analyse a position or completed PGN.
- Best-move candidates, principal variations, evaluation, evaluation swing and blunder/mistake/inaccuracy classification.
- Explain *why* a move works or fails in learner-appropriate language.
- Compare the played move with candidate moves and identify tactical/strategic ideas.
- Ask follow-up questions about the current position.
- Convert recurring errors into lessons and puzzle assignments.
- Show engine depth, engine version, time budget and limitations.
- Coach output must cite the actual position and supplied engine line; validate every referenced move. If analysis is inconclusive, say so.
- Apply usage quotas, queue limits and cost controls.

### G. Practice Arena
- Local two-player board.
- Computer opponents at measured strength levels, with honest labels rather than misleading Elo claims.
- Themed practice positions: defend, convert an advantage, find a tactic, or play an endgame.
- Opening practice from a selected repertoire line.
- Game review and PGN export.
- Online friend games, matchmaking, tournaments and spectating are later features requiring anti-cheat, moderation and reliable real-time infrastructure.

### H. Endgame and opening practice labs
- Set up positions by FEN or curated scenario.
- Play both sides or one side against a computer.
- Objective-based tasks, move limits where appropriate, hints and engine-checked feedback.
- Save difficult positions for revision.

### I. Learning profile and analytics
- Optional starting assessment; no rating assumed without evidence.
- Skill map by tactics, openings, strategy, calculation, endgames and game discipline.
- Track accuracy, repeat mistakes, puzzle response time, lesson mastery and activity.
- Personalized weekly and daily plan.
- Review queue using spaced repetition.
- Progress comparisons over time without claiming a precise playing rating from puzzle scores alone.

### J. Accounts, sync and social
- Sign-up/sign-in, profile, preferences and account recovery.
- Cross-device sync for lessons, repertoire, games and progress.
- Privacy controls, export and account deletion.
- Friends, groups, challenges and leaderboards after core learning quality is stable.
- Community features need reporting, blocking, moderation and child-safety/privacy review before release.

### K. Subscription and monetization
- Free tier: complete beginner path, selected intermediate content, a daily puzzle allowance, basic progress, limited analysis/coaching.
- Premium hypothesis: full academy and opening library, expanded puzzles, deeper analysis, personalized training, and offline course access.
- Premium price, usage limits and entitlements are not final until user research and cost tests.
- Verify purchases server-side; never trust a client-side Premium flag.
- Display remaining usage and renewal terms clearly. No dark patterns.

### L. Accessibility, localization and quality
- Responsive layouts for phones, tablets and desktop.
- Keyboard and screen-reader support where feasible; high contrast and board themes.
- Clear notation and optional beginner-friendly explanations.
- English first; localization such as Hindi and Telugu can follow once lesson terminology is reviewed.
- Performance, crash, accessibility, privacy, security and chess-correctness testing in every release.

---

## 3. Phased implementation plan

## Phase 0 — Product and technical foundation
**Goal:** settle scope and remove major unknowns before implementation.

- [x] Create public GitHub repository.
- [x] Write initial product specification and architecture notes.
- [x] Write this full roadmap.
- [ ] Confirm web-first delivery (recommended) and Android second.
- [ ] Choose the first UI framework and supported browsers/devices.
- [ ] Select chess rules library and define the single authoritative game-state service.
- [ ] Verify Stockfish integration and distribution obligations.
- [ ] Research opening/puzzle data sources and record licenses.
- [ ] Define visual identity, navigation map, and MVP acceptance tests.

**Exit gate:** approved scope, architecture decisions, data provenance plan and test plan.

## Phase 1 — Runnable web foundation
**Goal:** get a real application running, not just documentation.

- Scaffold web client, API service, local development instructions and environment configuration.
- Establish linting, formatting, type checking, automated tests and CI.
- Create app shell, responsive navigation, home/dashboard placeholder and design tokens.
- Add health endpoint, structured logging and safe error handling.
- Add development seed data.

**Exit gate:** a new developer can follow the README, run the app locally, and pass CI from a clean checkout.

## Phase 2 — Chessboard and rules engine
**Goal:** make chess correctness dependable before adding lessons.

- Responsive 8×8 board and piece interaction.
- Legal move generation and validation through a proven rules library.
- Castling, en passant, all promotion choices, check and terminal states.
- Move history, SAN, undo, restart, board flip, FEN and PGN.
- Repetition and draw-rule handling.
- Automated unit, integration and regression tests using edge-case positions and known games.
- No home-grown partial movement rules as the production authority.

**Exit gate:** complete legal games work and all rules regression tests pass.

## Phase 3 — First learning experience
**Goal:** deliver a complete beginner learning loop.

- Course and lesson data model.
- Beginner course: board and pieces, legal moves, check, checkmate, stalemate, castling, en passant, promotion, notation and opening principles.
- Lesson viewer with examples, interactive positions and knowledge checks.
- First curated tactics set with validated solutions and hints.
- Lesson completion and puzzle attempt history.
- Basic learner dashboard.

**Exit gate:** a new learner can complete the beginner path, solve puzzles and see progress persist locally or in their account.

## Phase 4 — Accounts and persistence
**Goal:** safely save each learner's work.

- Authentication, profile and session management.
- Database migrations and API authorization.
- Persist courses, attempts, games, PGNs, repertoire and preferences.
- Sync and conflict handling.
- Account export/deletion and privacy controls.

**Exit gate:** users can sign in on a second device and retrieve consistent progress.

## Phase 5 — Stockfish analysis foundation
**Goal:** provide trustworthy chess analysis.

- Run Stockfish through UCI in an isolated analysis service.
- Configure depth/time limits, MultiPV, cancellation, queueing and concurrency.
- Store engine version, options, FEN, depth, nodes, score and principal variations.
- Build analysis UI with best lines and clear limitations.
- Test repeatability and validate every displayed move against the position.

**Exit gate:** analysis results are legal, traceable to engine settings and stable under load tests.

## Phase 6 — AI Chess Coach
**Goal:** translate engine analysis into useful teaching.

- Explain blunders, mistakes, inaccuracies, strong moves and candidate moves.
- Beginner/intermediate/advanced explanation levels.
- Position Q&A grounded in the current board and engine output.
- Explain tactical and positional themes.
- Link mistakes to relevant lessons and puzzles.
- Guard against hallucinated moves, unsupported evaluations and misleading certainty.
- Per-user usage quotas, cost monitoring and abuse controls.

**Exit gate:** a reviewed test suite shows explanations match the engine data and do not recommend illegal moves.

## Phase 7 — Full academy and content operations
**Goal:** build the actual chess knowledge product.

- Expand tactics, strategy, calculation, middlegame, endgame and checkmate curricula.
- Add opening encyclopedia in curated families and variations.
- Add content authoring/import pipeline with source, license, version and reviewer fields.
- Validate move trees automatically; review explanations and training positions manually.
- Add content versioning, search, filters and coverage reporting.
- Add model games only where distribution and annotation rights are clear.

**Exit gate:** each published content unit has a defined learning objective, legal validation, provenance and review status.

## Phase 8 — Adaptive learning and repertoire
**Goal:** make the product respond to the learner.

- Initial diagnostic assessment and skill profile.
- Spaced repetition and mistake library.
- Adaptive daily/weekly plan.
- White and Black repertoire builder.
- Opening recall drills and transposition awareness.
- Analytics that distinguish puzzle performance from actual game strength.

**Exit gate:** training recommendations are explainable, based on recorded performance and demonstrably useful in user testing.

## Phase 9 — Practice Arena and game review
**Goal:** provide repeated practical application.

- Computer opponent integration with calibrated strength settings.
- Practice scenarios and endgame labs.
- Game review with move-by-move analysis.
- Clocks and time controls.
- PGN import/export and saved games.
- Online games, matchmaking, tournaments and spectating only after real-time reliability and anti-cheat design are ready.

**Exit gate:** practice games are legal, stable, and review results correspond to the actual game record.

## Phase 10 — Android app
**Goal:** bring the same learning experience to Android.

- Kotlin + Jetpack Compose client.
- Shared backend and account.
- Responsive board and touch-first controls.
- Offline access to downloaded lessons and selected puzzles.
- Sync, notifications (opt-in), performance and battery testing.
- Google Play billing and verified entitlements if subscriptions are enabled.

**Exit gate:** Android beta passes device, sync, offline, accessibility and crash testing.

## Phase 11 — Social, subscriptions and launch
**Goal:** release a sustainable public product.

- Free/Premium entitlements and purchase verification.
- Usage quotas and transparent AI allowances.
- Friends, challenges, groups and leaderboards with moderation.
- Privacy policy, terms, support, reporting and account deletion.
- Security review, dependency/license audit, backup/recovery and load testing.
- Closed beta, feedback triage, release candidate and staged rollout.

**Exit gate:** no critical chess correctness, security, privacy, payment or crash blockers; support and rollback processes are ready.

## Phase 12 — Long-term expansion
- More opening families, sidelines and repertoire packs.
- Advanced preparation tools and opening novelty review.
- Coach-led courses and live classes (only with qualified content creators).
- Team/school/club features.
- More languages and regional learning content.
- Optional cloud analysis upgrades, subject to measured demand and operating costs.
- Continuous content review and engine/library upgrades.

---

## 4. Release definitions

### Internal prototype
A running board that supports complete legal games and passes core rules tests. It is not yet a public chess academy.

### MVP / first public beta
- Account and saved progress (or a clearly labelled local-only beta if accounts are deferred).
- Complete board and rules.
- Beginner course.
- Curated tactics trainer.
- Basic dashboard.
- Stockfish-backed analysis.
- Limited, grounded coach explanations.
- Responsive web experience.

### Version 1.0
- Stable web product.
- Core academy content across beginner and improver levels.
- Searchable opening encyclopedia with transparent coverage.
- Personalized daily training and mistake review.
- Practice against a computer.
- Accounts, sync, privacy controls and tested subscription entitlements if monetization is enabled.
- Android app may launch alongside 1.0 only if it passes its own release gates; otherwise it follows as a separate release.

### Later releases
Online multiplayer, tournaments, social systems, advanced repertoire tools, extensive advanced content, and live coaching.

---

## 5. Quality gates that apply to every phase

### Chess correctness
- All moves validated by the rules library.
- FEN/PGN round-trip tests.
- Special-move and draw-rule regression tests.
- No illegal move in lessons, puzzles, opening trees or coach suggestions.

### Content quality
- Source and license recorded.
- Move sequences validated.
- Explanations reviewed.
- Difficulty and learning objective assigned.
- Content corrections are versioned.

### AI safety and reliability
- Engine output is the source of chess evaluations.
- AI cannot modify the board state or bypass move validation.
- Unsupported claims are withheld or qualified.
- Usage and spend are monitored.

### Product quality
- Automated tests and CI pass.
- Responsive and accessible UI.
- Error handling and observability.
- Privacy, security and dependency checks.
- User feedback is collected and acted on.

---

## 6. Success metrics

- Activation: users who complete onboarding and first lesson.
- Learning: lesson completion and knowledge-check improvement.
- Tactics: accuracy by theme, repeat-mistake rate and review retention.
- Engagement: daily/weekly active learners and meaningful training sessions.
- Retention: D1, D7 and D30 retention.
- Coaching: analysis completion, explanation usefulness ratings and cost per active learner.
- Content: number of reviewed openings/lines/puzzles and defect rate.
- Reliability: crash-free sessions, API latency, engine queue time and sync failures.
- Business: free-to-paid conversion, churn, refunds and contribution margin.

We will not optimize streaks or time spent at the expense of actual learning.

---

## 7. Recommended build order and scope control

**Build web first, then Android.** A responsive web app is the fastest way to validate the board, curriculum and learning loop. Android should reuse the same backend and content APIs rather than becoming a separate product.

**Build in vertical slices:** board → one complete beginner lesson → validated puzzle loop → saved progress → Stockfish → grounded coach → broader content. This gives us a working, testable product at every stage.

**Do not start online multiplayer, tournaments, social feeds, or unlimited AI analysis in the first release.** They add moderation, anti-cheat, real-time infrastructure or unpredictable cost before the core learning experience has been proven.

**Current next action:** approve this roadmap, then finalize the web-first technology choices and create the runnable project scaffold. No application features beyond the documented foundation should be considered complete until implemented and tested.
