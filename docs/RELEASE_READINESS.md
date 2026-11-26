# Release Readiness: KnightForge Chess

**Snapshot:** 26 November 2026  
**Status:** Development / pre-release. This repository is not yet approved for public production launch.

## Verified repository inventory

| Area | Current repository evidence | Release status |
|---|---|---|
| Legal chess and gameplay | `python-chess` rules engine; local PvP, human-vs-AI, PGN import/export, clocks and online invite/matchmaking endpoints | Implemented in code; full production hardening remains |
| AI opponent | Seven configured difficulty profiles; optional Stockfish UCI with built-in fallback | Implemented; strength calibration and load tests remain |
| Opening library | Taxonomy seed: 50 systems and 299 named variation labels; repository: 31 branching opening records and 352 legal move nodes | Move legality validated; the taxonomy is explicitly non-exhaustive and 19 named systems do not yet have their own full tree |
| Academy | 28 lesson definitions and guided/practice/mastery session APIs | Implemented; lesson coverage/content review remains |
| Tactics | 15 curated puzzles plus 1,064 bulk records (1,079 total) | Loader now validates positions and every solution move; bulk source/licence metadata is not recorded |
| Accounts/progress | SQLite-backed users, ratings, lesson/puzzle progress, notes and saved PGN history | Implemented; production identity, recovery and database operations remain |
| Multiplayer | Invite codes, seat tokens, draw actions, matchmaking and WebSocket updates | Prototype endpoints; active games and queue state remain process-local |
| Browser client | Responsive web client with Playwright mobile viewport E2E | CI E2E is present; wider device/browser QA remains |
| Voice-enabled Academy coach | In-lesson tactical mistake coach with danger arrows, plus coach speech bubble, selectable device TTS voice, adjustable pace and Listen/Stop controls | Browser regression coverage added; final integrated CI and real-device voice QA still required |
| Android | Capacitor wrapper and a workflow that builds a debug APK | Not a signed release; current config points to a test Render URL |
| Hosting | Render Docker template with one worker | Example configuration only; durable storage and production service configuration required |

## Release blockers

1. **Durable game/session state.** Active matches, lesson sessions, puzzle sessions, invite-code indexes and matchmaking queues are Python process-memory dictionaries with TTL expiry. A restart loses them; multiple application instances will not share them. Move shared state to a transactional persistent store and use a shared pub/sub channel for multiplayer.
2. **Production persistence.** The Render template points SQLite at the container filesystem and does not provision a persistent disk. Configure a supported managed database or a persistent disk, backups, migrations, restore drills and operational monitoring.
3. **Account recovery.** Password recovery deliberately fails closed with HTTP 503 until verified out-of-band delivery is configured. Do not re-enable token-in-response recovery.
4. **Puzzle provenance.** The 1,064 bulk puzzle records have no per-record source/licence fields. The application now labels missing values as “Source not recorded” and “License not recorded.” Verify provenance and licensing before redistribution.
5. **Opening content quality.** The repository includes 31 trees, but 352 nodes do not constitute exhaustive repertoires. Expand practical branches, verify opening names/attributions, editorially review plans and explanations, and retain move legality tests.
6. **Online multiplayer authorization.** Continue security review around every game mutation, WebSocket admission, invite-code entropy/rate limiting, reconnect/resume, clock authority, draw/resignation semantics, matchmaking abuse and per-user game ownership.
7. **Release build and QA.** Run all CI jobs successfully on the final commit; run Android debug and signed release build; test on real Android devices and mobile browsers; test long-running games, network loss/reconnect, persistence restart and multi-instance behavior.
8. **Deployment and secrets.** Replace test backend URLs, configure production domain/TLS, secrets, CORS/rate limits, logging/alerts, database backups and privacy/legal pages before launch.

## Immediate engineering sequence

- Keep PR #2 and PR #3 unmerged until their integration order and final CI are reviewed.
- Make the current CI green, including Ruff, complete pytest suite and browser E2E.
- Complete server-side multiplayer authorization and regression tests.
- Verify the entire bulk puzzle dataset and correct provenance metadata.
- Implement durable match/session persistence and shared multiplayer coordination.
- Configure verified email recovery and production database/storage.
- Build and test Android artifacts; then complete security and deployment sign-off.

## Definition of done

KnightForge is release-ready only when the complete automated test suite passes on the exact release commit; active games and progress survive restarts; multiplayer has authenticated, authorized and reconnect-safe state transitions; all redistributed learning content has reviewed licensing; account recovery is secure and deliverable; Android release artefacts are signed and device-tested; and production deployment, backups, monitoring and rollback have been exercised.
