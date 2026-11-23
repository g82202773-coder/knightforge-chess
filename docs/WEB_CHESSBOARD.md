# KnightForge Browser Chessboard and FastAPI Session Server

## Run locally

```bash
python -m pip install -e ".[dev,server]"
uvicorn knightforge_engine.server:app --reload
```

Open http://127.0.0.1:8000. The server serves the responsive browser board and JSON API from one origin.

## Implemented browser features

- Responsive 8×8 chessboard with Unicode pieces, coordinates, click-to-select and click-to-move.
- Legal move targets come from the server's python-chess game state; the server validates every submitted UCI move again.
- Live board state, SAN move history, selection/highlight, lesson arrows and coach feedback.
- Guided, Practice, and Mastery modes. Mastery hides hints and recommendation arrows; the API rejects hint requests.
- Progressive hint requests, undo, restart, and optional browser speech synthesis.
- A short demonstration lesson: 1.e4 e5 2.Nf3 Nc6 3.Bb5. This is not a complete opening course.

## API

- `GET /api/health`
- `POST /api/sessions` with `{"mode":"guided|practice|mastery"}`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/moves` with `{"uci":"e2e4"}`
- `POST /api/sessions/{session_id}/hints` with `{"level":2}`
- `POST /api/sessions/{session_id}/undo`
- `POST /api/sessions/{session_id}/restart`

The server returns the board and coach snapshot together after a move. The client never submits FEN as authoritative state.

## Optional Stockfish

Install Stockfish separately and set `STOCKFISH_PATH` to its executable before starting the server. Analysis is bounded (0.75 seconds, MultiPV 2) and optional. Without a usable binary, the board and lesson still work; the UI reports that engine recommendations are unavailable. The browser cannot choose an executable path or engine limits.

## Operational limits

The session registry is in-memory, process-local, and lost when the server restarts. Run a single Uvicorn worker for this demo. Do not deploy multiple workers or expose it as a public multi-user service without shared transactional session storage, session expiry, authentication, rate limiting, and production security review. The opening repository is read-only for these sessions.
