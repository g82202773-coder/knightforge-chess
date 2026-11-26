# KnightForge Chess

**Chess Play & Learning Platform · Rules Engine · 7-Tier AI · Openings · Academy · Tactics · Analysis · Multiplayer**

KnightForge is a unified, server-authoritative chess platform built with Python, FastAPI, `python-chess`, WebSockets, SQLite, optional Stockfish UCI, and a responsive web client.

---

## Core Capabilities

- **Complete Legal Chess (`core.py`, `game_manager.py`):** All 20 standard FIDE/chess rules (castling, en passant, Q/R/B/N promotion, check, checkmate, stalemate, claimable threefold repetition and 50-move rule, fivefold/75-move auto-draws, insufficient material, draw offers, resignation, PGN import/export).
- **Interactive Chessboard (`web/`):** Tap-to-move and drag-and-drop, legal & capture indicators, last-move and check highlighting, move arrows, board flipping, 4 board themes, 3 piece styles, dark/light UI modes, and mobile-first layout without horizontal overflow.
- **7-Tier AI Opponent (`ai_opponent.py`):** Beginner, Easy, Intermediate, Advanced, Expert, Master, and Maximum strength. Uses Stockfish UCI (`Skill Level`, depth, time) when `STOCKFISH_PATH` is set, with a deterministic alpha-beta + quiescence fallback when Stockfish is not installed.
- **Opening & Gambit Encyclopedia (`data/openings/repository.json`, `opening_*.py`, `variation_matching.py`):** Taxonomy seed: 50 named systems and 299 named variation labels; 31 currently have legally validated branching trees (352 validated move nodes). The taxonomy explicitly remains non-exhaustive. with SAN/UCI/PGN/FEN recognition and transposition detection.
- **5-Level Structured Academy (`curriculum.py`, `guided_learning.py`, `adaptive_coach.py`):** 28 interactive lessons spanning Rules (Level 1), Openings, Gambit Academy, Strategy, Middlegame, and Endgame Academy (K+Q mate, Opposition, Lucena, Philidor, Pawn Breakthrough), with Guided, Practice, and Mastery modes plus "Continue Full Game". The in-lesson tactical mistake coach explains rules-verified hanging-piece captures, highlights attacker and target squares, speaks through browser text-to-speech, and offers Retry or Continue with the reviewed move; answer-revealing Continue is disabled in Mastery mode.
- **Tactics Trainer (`puzzles.py`):** 1,079 rules-validated single- and multi-move puzzles (15 curated puzzles plus 1,064 bulk records; the bulk records currently lack per-record source and licence metadata and must not be redistributed until provenance is reviewed) with Daily/Random selection, progressive hints, timer, and Elo tracking.
- **Post-Game Analysis & Grounded AI Coach (`game_analyzer.py`, `coach_decision.py`, `tactics.py`, `positional_analysis.py`):** PGN move-by-move classification (`best`, `excellent`, `good`, `inaccuracy`, `mistake`, `blunder`, `missed_opportunity`), accuracy estimate, SVG evaluation graph, and position-grounded coaching.
- **Multiplayer & Clocks (`game_manager.py`, `server.py`):** Local 2-Player, Online Private Invite Codes, Online Quick Match queue, WebSocket live sync (`/ws/games/{game_id}`), and Bullet/Blitz/Rapid/Classical/Correspondence/Custom clocks with increment, delay, pause, and timeout detection.
- **Accounts & Persistent Progress (`storage.py`):** PBKDF2-HMAC-SHA256 registration/login, Chess & Puzzle Elo ratings, daily streaks, achievements, saved PGN history, and personal study notes backed by SQLite. Password recovery is deliberately disabled until a verified email-delivery provider is configured; the API must never return reset tokens directly to anonymous callers.

---

## Local Installation & Quick Start

Requires **Python 3.11+**.

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev,server]"
uvicorn knightforge_engine.server:app --reload
```

Open **http://127.0.0.1:8000**.

### Enabling Stockfish UCI (Optional locally, Pre-Installed in Docker/Render)

Install Stockfish for your OS and point `STOCKFISH_PATH` to the executable before starting the server:

```bash
# Linux / macOS:
export STOCKFISH_PATH=/usr/games/stockfish
uvicorn knightforge_engine.server:app --reload

# Windows PowerShell:
$env:STOCKFISH_PATH="C:\path\to\stockfish.exe"
uvicorn knightforge_engine.server:app --reload
```

---

## Running Automated Tests & Linting

```bash
ruff check src tests
pytest --cov=knightforge_engine --cov-report=term-missing
```

For browser end-to-end tests:

```bash
python -m pip install playwright
python -m playwright install chromium
pytest tests/e2e/test_browser_app.py -v
```

---

## Docker & Render Deployment

The included `Dockerfile` automatically installs the Debian `stockfish` package and configures `STOCKFISH_PATH=/usr/games/stockfish`.

```bash
docker build -t knightforge-chess .
docker run -p 8000:8000 knightforge-chess
```

For **Render**, push this repository to GitHub and create a Web Service from `render.yaml` (Docker runtime, `--workers 1`). **Production note:** active games, lesson sessions, puzzle sessions, invite indexes, and matchmaking queues are currently in process memory and expire on restart/TTL. The included Render configuration is a free-plan single-worker template and does not provision durable storage. Before a public launch, move active-game/session persistence to a shared durable store, configure a persistent database and verified email recovery provider, and run the release build/security checks.
