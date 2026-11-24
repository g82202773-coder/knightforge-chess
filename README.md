# KnightForge Chess

**Complete Chess Platform · Rules Engine · 7-Tier AI · Opening Encyclopedia · 5-Level Academy · Tactics · Analysis · Multiplayer**

KnightForge is a unified, server-authoritative chess platform built with Python, FastAPI, `python-chess`, WebSockets, SQLite, optional Stockfish UCI, and a responsive web client.

---

## Core Capabilities

- **Complete Legal Chess (`core.py`, `game_manager.py`):** All 20 standard FIDE/chess rules (castling, en passant, Q/R/B/N promotion, check, checkmate, stalemate, claimable threefold repetition and 50-move rule, fivefold/75-move auto-draws, insufficient material, draw offers, resignation, PGN import/export).
- **Interactive Chessboard (`web/`):** Tap-to-move and drag-and-drop, legal & capture indicators, last-move and check highlighting, move arrows, board flipping, 4 board themes, 3 piece styles, dark/light UI modes, and mobile-first layout without horizontal overflow.
- **7-Tier AI Opponent (`ai_opponent.py`):** Beginner, Easy, Intermediate, Advanced, Expert, Master, and Maximum strength. Uses Stockfish UCI (`Skill Level`, depth, time) when `STOCKFISH_PATH` is set, with a deterministic alpha-beta + quiescence fallback when Stockfish is not installed.
- **Opening & Gambit Encyclopedia (`data/openings/repository.json`, `opening_*.py`, `variation_matching.py`):** 29 legally validated, reviewed branching opening and gambit trees (317 validated move nodes across all 7 taxonomy families) with SAN/UCI/PGN/FEN recognition and transposition detection.
- **5-Level Structured Academy (`curriculum.py`, `guided_learning.py`, `adaptive_coach.py`):** 21 legally validated interactive lessons spanning Rules (Level 1), Openings, Gambit Academy, Strategy, Middlegame, and Endgame Academy (K+Q mate, Opposition, Lucena, Philidor, Pawn Breakthrough), with Guided, Practice, and Mastery modes plus "Continue Full Game".
- **Tactics Trainer (`puzzles.py`):** 15 validated single- and multi-move puzzles (including Mate-in-1, Mate-in-2, Anastasia's Mate, Knight Underpromotion Fork, and Philidor's Legacy Mate-in-3) with Daily/Random selection, progressive hints, timer, and Elo tracking.
- **Post-Game Analysis & Grounded AI Coach (`game_analyzer.py`, `coach_decision.py`, `tactics.py`, `positional_analysis.py`):** PGN move-by-move classification (`best`, `excellent`, `good`, `inaccuracy`, `mistake`, `blunder`, `missed_opportunity`), accuracy estimate, SVG evaluation graph, and position-grounded coaching.
- **Multiplayer & Clocks (`game_manager.py`, `server.py`):** Local 2-Player, Online Private Invite Codes, Online Quick Match queue, WebSocket live sync (`/ws/games/{game_id}`), and Bullet/Blitz/Rapid/Classical/Correspondence/Custom clocks with increment, delay, pause, and timeout detection.
- **Accounts & Persistent Progress (`storage.py`):** PBKDF2-HMAC-SHA256 registration/login, one-time token password recovery, Chess & Puzzle Elo ratings, daily streaks, achievements, saved PGN history, and personal study notes backed by SQLite.

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

For **Render**, push this repository to GitHub and create a Web Service from `render.yaml` (Docker runtime, `--workers 1`). For horizontal multi-worker cloud scaling later, migrate `ProgressStore` from SQLite to PostgreSQL and active match rooms to Redis Pub/Sub.
