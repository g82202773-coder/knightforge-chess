"""FastAPI + WebSocket platform server for KnightForge Chess."""
from __future__ import annotations

import os
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import chess
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .adaptive_coach import AdaptiveOpeningCoach
from .ai_opponent import AIDifficulty, ChessAIOpponent
from .analysis import StockfishAnalyzer
from .coach_presentation import coach_state_payload, submission_payload
from .curriculum import CurriculumCatalog
from .game_analyzer import ChessCoachAssistant, analyze_pgn_game
from .game_manager import CLOCK_PRESETS, ColorName, FullChessMatch, MatchMode
from .guided_learning import GuidedLesson
from .opening_catalog import OpeningCatalog
from .opening_coverage import analyze_opening_coverage
from .opening_recognition import OpeningRecognizer
from .opening_repository import OpeningRepository
from .opening_trainer import build_opening_lesson, list_opening_variations
from .puzzles import PuzzleCatalog, PuzzleSession, compute_elo_delta
from .storage import ProgressStore
from .variation_matching import PositionBasedVariationMatcher

Mode = Literal["guided", "practice", "mastery"]

DEFAULT_LESSON_ID = "open-game-first-five"
DEFAULT_TTL_SECONDS = int(os.environ.get("KNIGHTFORGE_SESSION_TTL_SECONDS", "7200"))


def demo_lesson() -> GuidedLesson:
    """Return the default Open Game introductory lesson."""
    entry = CurriculumCatalog().get(DEFAULT_LESSON_ID)
    assert entry is not None
    return entry.lesson


@dataclass
class SessionRecord:
    coach: AdaptiveOpeningCoach
    mode: Mode
    lock: threading.RLock
    lesson_id: str = DEFAULT_LESSON_ID
    hint_level: int = 0
    completion_recorded: bool = False
    auto_reply: bool = False
    last_accessed: float = field(default_factory=time.monotonic)


@dataclass
class PuzzleSessionRecord:
    session: PuzzleSession
    lock: threading.RLock
    recorded: bool = False
    last_accessed: float = field(default_factory=time.monotonic)


@dataclass
class MatchRecord:
    match: FullChessMatch
    lock: threading.RLock
    recorded: bool = False
    last_accessed: float = field(default_factory=time.monotonic)


class ConnectionManager:
    """Manage live WebSocket rooms for online multiplayer matches."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms.setdefault(game_id, set()).add(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        room = self._rooms.get(game_id)
        if room is not None:
            room.discard(websocket)
            if not room:
                del self._rooms[game_id]

    async def broadcast(self, game_id: str, payload: dict[str, Any]) -> None:
        room = list(self._rooms.get(game_id, ()))
        for ws in room:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(game_id, ws)


class SessionStore:
    """Thread-safe platform store with TTL expiry and SQLite persistence."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._puzzle_sessions: dict[str, PuzzleSessionRecord] = {}
        self._matches: dict[str, MatchRecord] = {}
        self._invite_index: dict[str, str] = {}
        self._matchmaking_queue: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self.ttl_seconds = max(120, DEFAULT_TTL_SECONDS)

        repo_root = Path(__file__).resolve().parents[2]
        default_openings = repo_root / "data/openings/repository.json"
        default_taxonomy = repo_root / "data/openings/opening_taxonomy.json"
        default_db = repo_root / "data/knightforge.db"

        self.repository = OpeningRepository.load(
            Path(os.environ.get("KNIGHTFORGE_OPENINGS_PATH", str(default_openings)))
        )
        taxonomy_path = Path(
            os.environ.get("KNIGHTFORGE_TAXONOMY_PATH", str(default_taxonomy))
        )
        self.catalog = OpeningCatalog.load(taxonomy_path) if taxonomy_path.exists() else None
        self.curriculum = CurriculumCatalog()
        self.puzzles = PuzzleCatalog()
        self.progress = ProgressStore(
            os.environ.get("KNIGHTFORGE_DB_PATH", str(default_db))
        )

        self.analyzer: StockfishAnalyzer | None = None
        executable = os.environ.get("STOCKFISH_PATH")
        if executable:
            try:
                self.analyzer = StockfishAnalyzer(executable)
            except (OSError, RuntimeError):
                self.analyzer = None

        self.ai = ChessAIOpponent(executable)
        self.coach_assistant = ChessCoachAssistant(self.repository, self.ai)

    def _prune_expired(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        with self._lock:
            for sid in [k for k, v in self._sessions.items() if v.last_accessed < cutoff]:
                del self._sessions[sid]
            for sid in [
                k for k, v in self._puzzle_sessions.items() if v.last_accessed < cutoff
            ]:
                del self._puzzle_sessions[sid]
            for gid in [k for k, v in self._matches.items() if v.last_accessed < cutoff]:
                code = self._matches[gid].match.invite_code
                if code:
                    self._invite_index.pop(code, None)
                del self._matches[gid]

    def create(
        self, mode: Mode, lesson_id: str = DEFAULT_LESSON_ID
    ) -> tuple[str, SessionRecord]:
        self._prune_expired()
        entry = self.curriculum.get(lesson_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Lesson not found: {lesson_id}")
        coach = AdaptiveOpeningCoach(
            entry.lesson,
            self.repository,
            analyzer=self.analyzer,
            analysis_time_limit=0.75,
            analysis_multipv=2,
        )
        session_id = secrets.token_urlsafe(18)
        record = SessionRecord(coach, mode, threading.RLock(), lesson_id=lesson_id)
        with self._lock:
            self._sessions[session_id] = record
        return session_id, record

    def create_from_lesson(
        self, lesson: GuidedLesson, mode: Mode, *, auto_reply: bool = False
    ) -> tuple[str, SessionRecord]:
        self._prune_expired()
        coach = AdaptiveOpeningCoach(
            lesson,
            self.repository,
            analyzer=self.analyzer,
            analysis_time_limit=0.75,
            analysis_multipv=2,
        )
        # If learner plays Black and auto_reply is enabled, play White's opening move automatically
        if auto_reply:
            prompt = coach.prompt().prompt
            if prompt.expected_uci and prompt.turn != lesson.learner_color:
                coach.submit_uci(prompt.expected_uci)
        session_id = secrets.token_urlsafe(18)
        record = SessionRecord(
            coach,
            mode,
            threading.RLock(),
            lesson_id=lesson.lesson_id,
            auto_reply=auto_reply,
        )
        with self._lock:
            self._sessions[session_id] = record
        return session_id, record

    def get(self, session_id: str) -> SessionRecord:
        self._prune_expired()
        with self._lock:
            record = self._sessions.get(session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Chess session not found or expired.")
        record.last_accessed = time.monotonic()
        return record

    def create_puzzle_session(self, puzzle_id: str) -> tuple[str, PuzzleSessionRecord]:
        self._prune_expired()
        puzzle = self.puzzles.get(puzzle_id)
        if puzzle is None:
            raise HTTPException(status_code=404, detail=f"Puzzle not found: {puzzle_id}")
        sid = secrets.token_urlsafe(18)
        record = PuzzleSessionRecord(PuzzleSession(puzzle), threading.RLock())
        with self._lock:
            self._puzzle_sessions[sid] = record
        return sid, record

    def get_puzzle_session(self, session_id: str) -> PuzzleSessionRecord:
        self._prune_expired()
        with self._lock:
            record = self._puzzle_sessions.get(session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Puzzle session not found or expired.")
        record.last_accessed = time.monotonic()
        return record

    def register_match(self, match: FullChessMatch) -> tuple[str, MatchRecord]:
        self._prune_expired()
        game_id = secrets.token_urlsafe(16)
        record = MatchRecord(match, threading.RLock())
        with self._lock:
            self._matches[game_id] = record
            if match.invite_code:
                self._invite_index[match.invite_code] = game_id
        return game_id, record

    def get_match(self, game_id: str) -> MatchRecord:
        self._prune_expired()
        with self._lock:
            record = self._matches.get(game_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Chess game not found or expired.")
        record.last_accessed = time.monotonic()
        return record

    def resolve_invite(self, invite_code: str) -> tuple[str, MatchRecord]:
        clean = invite_code.strip().upper()
        with self._lock:
            gid = self._invite_index.get(clean)
        if gid is None:
            raise HTTPException(status_code=404, detail="Invite code not found or expired.")
        return gid, self.get_match(gid)


store = SessionStore()
ws_manager = ConnectionManager()
app = FastAPI(title="KnightForge Chess Platform", version="4.0.0")


def _user_id_from_header(authorization: str | None) -> int:
    if not authorization:
        return 0
    token = authorization.replace("Bearer ", "").strip()
    return store.progress.resolve_user_id(token)


def apply_mode_policy(payload: dict[str, Any], record: SessionRecord) -> dict[str, Any]:
    """Enforce hint disclosure on every lesson session response."""
    state = payload.get("state", payload)
    state["mode"] = record.mode
    state["lesson_id"] = record.lesson_id
    state["lesson_title"] = record.coach.session.lesson.title
    state["learner_color"] = record.coach.session.lesson.learner_color
    coach = state["coach"]
    engine = state["engine"]
    coach_state = record.coach.prompt()
    expected = coach_state.prompt.expected_uci
    coach["hints_available"] = expected is not None and record.mode != "mastery"

    matched_opening = (
        coach_state.variation_match.matches[0].name
        if coach_state.variation_match.matches
        else (
            coach_state.recognition.matches[0].name
            if coach_state.recognition.matches
            else None
        )
    )
    matched_variations = (
        list(coach_state.variation_match.matches[0].variation_labels)
        if coach_state.variation_match.matches
        else []
    )
    state["opening"] = {
        "name": matched_opening,
        "variations": matched_variations,
        "status": coach_state.knowledge_status,
    }

    if record.mode in {"practice", "mastery"}:
        instruction = (
            "Find the strongest move for this position. Request a hint if you need help."
            if record.mode == "practice"
            else "Mastery test: choose your move without hints."
        )
        coach["text"] = instruction
        coach["voice_script"] = instruction
        coach["explanation"] = ""
        coach["expected_move"] = None
        state["board"]["highlighted_squares"] = []
        engine["recommendation"] = None
        engine["recommendation_arrow"] = None
        feedback = state.get("feedback")
        if feedback is not None:
            feedback["best_uci"] = None
            feedback["best_san"] = None
            feedback["engine_top_choice"] = None

    if record.mode == "mastery":
        coach["active_hint"] = None
        coach["hints_available"] = False
    elif record.mode == "practice" and record.hint_level == 0:
        coach["active_hint"] = None
    return payload


def state_for(record: SessionRecord) -> dict[str, Any]:
    return apply_mode_policy(coach_state_payload(record.coach.prompt()), record)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class NotesRequest(BaseModel):
    notes: str = Field(max_length=4000)


class RecoveryRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)


class RecoveryConfirmRequest(BaseModel):
    recovery_token: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class MatchmakingRequest(BaseModel):
    time_control: str = "rapid_10_0"


class CreateSessionRequest(BaseModel):
    mode: Mode = "guided"
    lesson_id: str = DEFAULT_LESSON_ID


class TrainOpeningRequest(BaseModel):
    variation_id: str | None = None
    mode: Mode = "guided"
    learner_color: ColorName | None = None
    auto_reply: bool = True


class MoveRequest(BaseModel):
    uci: str = Field(min_length=4, max_length=5, pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")
    player_token: str | None = None


class HintRequest(BaseModel):
    level: int = Field(ge=1, le=4)


class PuzzleHintRequest(BaseModel):
    level: int = Field(ge=1, le=3)


class CreateGameRequest(BaseModel):
    mode: MatchMode = "human_vs_ai"
    player_color: ColorName = "white"
    difficulty: AIDifficulty = "intermediate"
    time_control: str = "rapid_10_0"
    custom_base_seconds: int | None = Field(default=None, ge=0, le=7200)
    custom_increment_seconds: int = Field(default=0, ge=0, le=120)
    custom_delay_seconds: int = Field(default=0, ge=0, le=60)
    starting_fen: str | None = None


class ImportPgnRequest(BaseModel):
    pgn: str = Field(min_length=2, max_length=40000)
    mode: MatchMode = "local_pvp"


class DrawActionRequest(BaseModel):
    action: Literal["offer", "accept", "decline", "claim"]
    actor: ColorName | None = None


class RecognizeRequest(BaseModel):
    moves: str | None = None
    fen: str | None = None
    notation: Literal["auto", "san", "uci", "pgn"] = "auto"


class AnalyzeGameRequest(BaseModel):
    pgn: str = Field(min_length=2, max_length=40000)


class CoachAskRequest(BaseModel):
    fen: str
    question: str = ""
    player_level: str = "intermediate"


# ---------------------------------------------------------------------------
# Health & User Accounts
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "stockfish_available": store.ai.stockfish_available,
        "reviewed_openings": len(store.repository.all()),
        "lessons_available": len(store.curriculum.all()),
        "puzzles_available": len(store.puzzles.all()),
        "clock_presets": list(CLOCK_PRESETS.keys()),
    }


@app.post("/api/auth/register")
def register(request: AuthRequest) -> dict[str, Any]:
    try:
        return store.progress.register_user(request.username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login")
def login(request: AuthRequest) -> dict[str, Any]:
    try:
        return store.progress.login_user(request.username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/auth/recover/request")
def request_recovery(request: RecoveryRequest) -> dict[str, Any]:
    try:
        token = store.progress.create_recovery_token(request.username)
        return {"recovery_token": token, "message": "One-time recovery token issued."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/auth/recover/confirm")
def confirm_recovery(request: RecoveryConfirmRequest) -> dict[str, Any]:
    try:
        username = store.progress.reset_password_with_token(
            request.recovery_token, request.new_password
        )
        return {"status": "password_reset", "username": username}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/matchmaking/enqueue")
async def matchmaking_enqueue(request: MatchmakingRequest) -> dict[str, Any]:
    """Pair waiting players into an online_pvp match for the chosen time control."""
    tc = request.time_control if request.time_control in CLOCK_PRESETS else "rapid_10_0"
    with store._lock:
        queue = store._matchmaking_queue.setdefault(tc, [])
        while queue:
            waiting_gid = queue.pop(0)
            record = store._matches.get(waiting_gid)
            if record is not None and record.match.black_token is None:
                with record.lock:
                    color, token = record.match.join_online()
                    state = record.match.state_dict()
                await ws_manager.broadcast(
                    waiting_gid, {"event": "opponent_joined", "state": state}
                )
                return {
                    "matched": True,
                    "game_id": waiting_gid,
                    "assigned_color": color,
                    "player_token": token,
                    "state": state,
                }
        match = FullChessMatch(
            mode="online_pvp",
            time_control=tc,
            repository=store.repository,
            ai=store.ai,
        )
        gid, rec = store.register_match(match)
        queue.append(gid)
        return {
            "matched": False,
            "game_id": gid,
            "invite_code": match.invite_code,
            "assigned_color": "white",
            "player_token": match.white_token,
            "state": rec.match.state_dict(),
        }


@app.get("/api/auth/me")
def me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    return store.progress.get_profile(uid)


@app.post("/api/auth/notes")
def save_notes(
    request: NotesRequest, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    store.progress.update_notes(uid, request.notes)
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# Full Chess Gameplay, Clocks & Multiplayer (HvAI / Local 2P / Online PvP)
# ---------------------------------------------------------------------------
def _record_game_if_over(record: MatchRecord, user_id: int) -> None:
    m = record.match
    if m.is_over and not record.recorded:
        if m.winner is None:
            result = "draw"
        elif m.mode == "human_vs_ai":
            result = "win" if m.winner == m.player_color else "loss"
        else:
            result = f"{m.winner}_win"
        store.progress.record_saved_game(
            mode=m.mode,
            player_color=m.player_color,
            difficulty=m.difficulty if m.mode == "human_vs_ai" else "pvp",
            result=result,
            termination=m.termination_reason or "finished",
            plies=len(m.moves_uci),
            pgn=m.export_pgn(),
            user_id=user_id,
        )
        record.recorded = True


@app.post("/api/games")
def create_game(request: CreateGameRequest) -> dict[str, Any]:
    try:
        match = FullChessMatch(
            mode=request.mode,
            player_color=request.player_color,
            difficulty=request.difficulty,
            time_control=request.time_control,
            custom_base_seconds=request.custom_base_seconds,
            custom_increment_seconds=request.custom_increment_seconds,
            custom_delay_seconds=request.custom_delay_seconds,
            starting_fen=request.starting_fen,
            repository=store.repository,
            ai=store.ai,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    game_id, record = store.register_match(match)
    with record.lock:
        return {
            "game_id": game_id,
            "invite_code": match.invite_code,
            "player_token": match.white_token,
            "assigned_color": "white" if match.mode == "online_pvp" else match.player_color,
            "state": match.state_dict(),
        }


@app.post("/api/games/join/{invite_code}")
async def join_game(invite_code: str) -> dict[str, Any]:
    game_id, record = store.resolve_invite(invite_code)
    with record.lock:
        try:
            color, token = record.match.join_online()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        state = record.match.state_dict()
    await ws_manager.broadcast(game_id, {"event": "opponent_joined", "state": state})
    return {
        "game_id": game_id,
        "assigned_color": color,
        "player_token": token,
        "state": state,
    }


@app.post("/api/games/import-pgn")
def import_pgn_game(request: ImportPgnRequest) -> dict[str, Any]:
    try:
        match = FullChessMatch.from_pgn(
            request.pgn,
            mode=request.mode,
            repository=store.repository,
            ai=store.ai,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    game_id, record = store.register_match(match)
    with record.lock:
        return {"game_id": game_id, "state": match.state_dict()}


@app.get("/api/games/{game_id}")
def get_game(game_id: str) -> dict[str, Any]:
    record = store.get_match(game_id)
    with record.lock:
        return {"game_id": game_id, "state": record.match.state_dict()}


@app.post("/api/games/{game_id}/moves")
async def play_game_move(
    game_id: str,
    request: MoveRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    record = store.get_match(game_id)
    with record.lock:
        try:
            outcome = record.match.submit_move(request.uci, player_token=request.player_token)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _record_game_if_over(record, uid)
        state = outcome["state"]
    await ws_manager.broadcast(game_id, {"event": "move", "state": state})
    return outcome


@app.post("/api/games/{game_id}/undo")
def undo_game_move(game_id: str) -> dict[str, Any]:
    record = store.get_match(game_id)
    with record.lock:
        try:
            record.match.undo()
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": record.match.state_dict()}


@app.post("/api/games/{game_id}/restart")
def restart_game(game_id: str) -> dict[str, Any]:
    record = store.get_match(game_id)
    with record.lock:
        try:
            record.match.restart()
            record.recorded = False
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": record.match.state_dict()}


@app.post("/api/games/{game_id}/resign")
async def resign_game(
    game_id: str, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    record = store.get_match(game_id)
    with record.lock:
        record.match.resign()
        _record_game_if_over(record, uid)
        state = record.match.state_dict()
    await ws_manager.broadcast(game_id, {"event": "resign", "state": state})
    return {"state": state}


@app.post("/api/games/{game_id}/draw")
async def draw_action(
    game_id: str,
    request: DrawActionRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    record = store.get_match(game_id)
    with record.lock:
        try:
            msg = record.match.handle_draw_action(request.action, request.actor)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _record_game_if_over(record, uid)
        state = record.match.state_dict()
    await ws_manager.broadcast(game_id, {"event": "draw", "message": msg, "state": state})
    return {"message": msg, "state": state}


@app.post("/api/games/{game_id}/pause")
def pause_clock(game_id: str) -> dict[str, Any]:
    record = store.get_match(game_id)
    with record.lock:
        if record.match.mode == "online_pvp":
            raise HTTPException(status_code=409, detail="Clock pause is local-mode only.")
        paused = record.match.clock.toggle_pause()
        return {"paused": paused, "state": record.match.state_dict()}


@app.get("/api/games/{game_id}/pgn")
def export_game_pgn(game_id: str) -> dict[str, Any]:
    record = store.get_match(game_id)
    with record.lock:
        return {"pgn": record.match.export_pgn()}


@app.websocket("/ws/games/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str) -> None:
    await ws_manager.connect(game_id, websocket)
    try:
        record = store.get_match(game_id)
        await websocket.send_json({"event": "sync", "state": record.match.state_dict()})
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, HTTPException):
        ws_manager.disconnect(game_id, websocket)


# ---------------------------------------------------------------------------
# Academy Lessons & Guided Coach Sessions (backward-compatible)
# ---------------------------------------------------------------------------
@app.get("/api/lessons")
def list_lessons(
    category: str | None = None,
    level: int | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    completed = store.progress.completed_lesson_ids(uid)
    items = []
    for entry in store.curriculum.filter(category=category, level=level):
        item = entry.to_summary_dict()
        item["completed"] = entry.lesson.lesson_id in completed
        items.append(item)
    return {"lessons": items}


@app.post("/api/sessions")
def create_session(request: CreateSessionRequest) -> dict[str, Any]:
    session_id, record = store.create(request.mode, request.lesson_id)
    with record.lock:
        return {"session_id": session_id, "state": state_for(record)}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    record = store.get(session_id)
    with record.lock:
        return {"session_id": session_id, "state": state_for(record)}


@app.post("/api/sessions/{session_id}/moves")
def submit_move(
    session_id: str,
    request: MoveRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    record = store.get(session_id)
    with record.lock:
        try:
            result = record.coach.submit_uci(request.uci)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result.submission.applied and record.mode == "practice":
            record.hint_level = 0
        auto_reply_san: str | None = None
        if record.auto_reply and result.submission.applied:
            nxt_prompt = result.state.prompt
            learner_col = record.coach.session.lesson.learner_color
            if (
                nxt_prompt.kind == "move"
                and nxt_prompt.expected_uci
                and nxt_prompt.turn != learner_col
            ):
                reply_res = record.coach.submit_uci(nxt_prompt.expected_uci)
                auto_reply_san = reply_res.submission.actual_san
                result = reply_res
        if (
            result.state.prompt.kind in {"complete", "free_play"}
            and not record.completion_recorded
        ):
            store.progress.record_lesson_completion(record.lesson_id, record.mode, uid)
            record.completion_recorded = True
        payload = apply_mode_policy(submission_payload(result), record)
        payload["auto_reply_san"] = auto_reply_san
        return payload


@app.post("/api/sessions/{session_id}/hints")
def reveal_hint(session_id: str, request: HintRequest) -> dict[str, Any]:
    record = store.get(session_id)
    if record.mode == "mastery":
        raise HTTPException(status_code=403, detail="Hints are disabled in Mastery mode.")
    with record.lock:
        try:
            record.coach.reveal_hint(request.level)
            record.hint_level = request.level
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": state_for(record)}


@app.post("/api/sessions/{session_id}/undo")
def undo(session_id: str) -> dict[str, Any]:
    record = store.get(session_id)
    with record.lock:
        try:
            record.coach.undo()
            record.hint_level = 0
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": state_for(record)}


@app.post("/api/sessions/{session_id}/restart")
def restart(session_id: str) -> dict[str, Any]:
    record = store.get(session_id)
    with record.lock:
        record.coach.restart()
        record.hint_level = 0
        record.completion_recorded = False
        return {"state": state_for(record)}


# ---------------------------------------------------------------------------
# Opening Encyclopedia, Gambits & Recognition
# ---------------------------------------------------------------------------
@app.get("/api/openings/taxonomy")
def openings_taxonomy() -> dict[str, Any]:
    if store.catalog is None:
        return {"families": [], "coverage": None}
    coverage = analyze_opening_coverage(store.catalog, store.repository).to_dict()
    reviewed_ids = {t.opening_id for t in store.repository.all()}
    families = [
        {
            "family_id": fam.family_id,
            "name": fam.name,
            "side": fam.side,
            "systems": [
                {
                    "system_id": sys.system_id,
                    "name": sys.name,
                    "variations": list(sys.variations),
                    "has_reviewed_tree": sys.system_id in reviewed_ids,
                }
                for sys in fam.systems
            ],
        }
        for fam in store.catalog.families()
    ]
    return {"families": families, "coverage": coverage}


@app.get("/api/openings/repository")
def openings_repository(q: str = "") -> dict[str, Any]:
    trees = store.repository.search(q, limit=100) if q.strip() else store.repository.all()
    return {
        "openings": [
            {
                "opening_id": tree.opening_id,
                "name": tree.name,
                "eco": tree.eco,
                "side": tree.side,
                "review_status": tree.review_status,
                "mainline_san": list(tree.mainline_san()),
                "mainline_uci": list(tree.mainline_uci()),
                "branch_count": tree.branch_count(),
                "source_name": tree.source_name,
                "tree": tree.to_dict(),
            }
            for tree in trees
        ]
    }


def _enrich_opening_nodes(
    board: chess.Board, nodes: tuple[Any, ...]
) -> list[dict[str, Any]]:
    """Attach authoritative SAN and resulting FEN to every opening tree node."""
    enriched: list[dict[str, Any]] = []
    for node in nodes:
        mv = chess.Move.from_uci(node.move_uci)
        san = board.san(mv)
        nxt = board.copy(stack=False)
        nxt.push(mv)
        enriched.append({
            "move_uci": node.move_uci,
            "san": san,
            "fen": nxt.fen(),
            "label": node.label,
            "white_plan": node.white_plan,
            "black_plan": node.black_plan,
            "explanation": node.explanation,
            "children": _enrich_opening_nodes(nxt, node.children),
        })
    return enriched


@app.get("/api/openings/{opening_id}/tree")
def opening_interactive_tree(opening_id: str) -> dict[str, Any]:
    tree = store.repository.get(opening_id)
    if tree is None:
        raise HTTPException(status_code=404, detail=f"Opening not found: {opening_id}")
    start_board = chess.Board(tree.starting_fen)
    return {
        "opening_id": tree.opening_id,
        "name": tree.name,
        "eco": tree.eco,
        "side": tree.side,
        "starting_fen": tree.starting_fen,
        "source_name": tree.source_name,
        "transposition_notes": list(tree.transposition_notes),
        "roots": _enrich_opening_nodes(start_board, tree.roots),
    }


@app.get("/api/openings/{opening_id}/variations")
def opening_variations(opening_id: str) -> dict[str, Any]:
    tree = store.repository.get(opening_id)
    if tree is None:
        raise HTTPException(status_code=404, detail=f"Opening not found: {opening_id}")
    variations = list_opening_variations(tree)
    return {
        "opening_id": tree.opening_id,
        "name": tree.name,
        "side": tree.side,
        "variations": [asdict(v) for v in variations],
    }


@app.post("/api/openings/{opening_id}/train")
def train_opening(opening_id: str, request: TrainOpeningRequest) -> dict[str, Any]:
    tree = store.repository.get(opening_id)
    if tree is None:
        raise HTTPException(status_code=404, detail=f"Opening not found: {opening_id}")
    try:
        lesson = build_opening_lesson(
            tree,
            variation_id=request.variation_id,
            learner_color=request.learner_color,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sid, record = store.create_from_lesson(lesson, request.mode, auto_reply=request.auto_reply)
    with record.lock:
        return {"session_id": sid, "state": state_for(record)}


ENDGAME_DRILLS: tuple[dict[str, str], ...] = (
    {
        "id": "drill-kq-vs-k",
        "title": "King & Queen vs King",
        "difficulty": "beginner",
        "fen": "4k3/8/8/8/8/8/3Q4/4K3 w - - 0 1",
        "goal": "Box the enemy king to the edge and deliver checkmate without stalemate.",
    },
    {
        "id": "drill-kr-vs-k",
        "title": "King & Rook vs King",
        "difficulty": "beginner",
        "fen": "4k3/8/8/8/8/8/8/R3K3 w - - 0 1",
        "goal": "Use opposition and rook cut-offs to force checkmate on the edge.",
    },
    {
        "id": "drill-opposition",
        "title": "King & Pawn Opposition",
        "difficulty": "intermediate",
        "fen": "8/4k3/8/8/4K3/4P3/8/8 w - - 0 1",
        "goal": "Take direct opposition in front of your pawn and promote to a queen.",
    },
    {
        "id": "drill-lucena",
        "title": "Lucena Position (Build the Bridge)",
        "difficulty": "advanced",
        "fen": "1K1k4/1P6/8/8/8/8/r7/5R2 w - - 0 1",
        "goal": "Lift the rook to the 4th rank, escort your king out, and promote the b-pawn.",
    },
    {
        "id": "drill-philidor",
        "title": "Philidor Rook Defence (Play Black)",
        "difficulty": "advanced",
        "fen": "4k3/8/8/3PK3/8/8/r7/5R2 b - - 0 1",
        "goal": "Hold the 6th rank, then switch to rear checks once White pushes d6.",
    },
    {
        "id": "drill-two-bishops",
        "title": "Two Bishops Checkmate",
        "difficulty": "advanced",
        "fen": "4k3/8/8/8/8/8/2BB4/4K3 w - - 0 1",
        "goal": "Coordinate both bishops with your king to herd Black's king into a corner.",
    },
)


@app.get("/api/endgames/drills")
def list_endgame_drills() -> dict[str, Any]:
    return {"drills": list(ENDGAME_DRILLS)}


@app.post("/api/openings/recognize")
def recognize_opening(request: RecognizeRequest) -> dict[str, Any]:
    recognizer = OpeningRecognizer(store.repository)
    matcher = PositionBasedVariationMatcher(store.repository)
    try:
        recognition = recognizer.recognize(
            moves=request.moves, fen=request.fen, notation=request.notation
        )
        variation = matcher.match(recognition)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "fen": recognition.fen,
        "ply": recognition.ply,
        "moves_san": list(recognition.moves_san),
        "anchor_matches": [asdict(m) for m in recognition.matches],
        "variation_matches": [asdict(m) for m in variation.matches],
    }


# ---------------------------------------------------------------------------
# Tactics / Puzzle Trainer
# ---------------------------------------------------------------------------
@app.get("/api/puzzles")
def list_puzzles(
    difficulty: str | None = None,
    theme: str | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    mistakes_only: bool = False,
    limit: int = 40,
    offset: int = 0,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    solved_ids = store.progress.solved_puzzle_ids(uid)
    only_ids = store.progress.mistake_puzzle_ids(uid) if mistakes_only else None
    filtered = store.puzzles.filter(
        difficulty=difficulty,
        theme=theme,
        min_rating=min_rating,
        max_rating=max_rating,
        only_ids=only_ids,
    )
    safe_limit = max(1, min(100, limit))
    safe_offset = max(0, offset)
    page = filtered[safe_offset : safe_offset + safe_limit]
    items = []
    for p in page:
        item = p.to_summary_dict()
        item["solved"] = p.puzzle_id in solved_ids
        items.append(item)
    return {
        "puzzles": items,
        "total_matching": len(filtered),
        "total_catalog": len(store.puzzles.all()),
        "offset": safe_offset,
        "limit": safe_limit,
        "daily_puzzle_id": store.puzzles.daily().puzzle_id,
    }


@app.post("/api/puzzles/random/session")
def random_puzzle_session(
    difficulty: str | None = None,
    theme: str | None = None,
) -> dict[str, Any]:
    chosen = store.puzzles.random_puzzle(difficulty=difficulty, theme=theme)
    sid, record = store.create_puzzle_session(chosen.puzzle_id)
    with record.lock:
        return {"session_id": sid, "state": record.session.state_dict()}


@app.post("/api/puzzles/{puzzle_id}/sessions")
def create_puzzle_session(puzzle_id: str) -> dict[str, Any]:
    sid, record = store.create_puzzle_session(puzzle_id)
    with record.lock:
        return {"session_id": sid, "state": record.session.state_dict()}


@app.post("/api/puzzles/sessions/{session_id}/moves")
def submit_puzzle_move(
    session_id: str,
    request: MoveRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    record = store.get_puzzle_session(session_id)
    with record.lock:
        try:
            outcome = record.session.submit_uci(request.uci)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        new_rating = None
        if outcome.solved and not record.recorded:
            profile = store.progress.get_profile(uid)
            clean = outcome.mistakes == 0 and outcome.hints_used == 0
            delta = compute_elo_delta(
                int(profile["puzzle_rating"]), record.session.puzzle.rating, clean
            )
            new_rating = store.progress.record_puzzle_attempt(
                record.session.puzzle.puzzle_id,
                True,
                outcome.hints_used,
                outcome.mistakes,
                rating_delta=delta,
                user_id=uid,
            )
            record.recorded = True
        return {
            "outcome": asdict(outcome),
            "puzzle_rating": new_rating,
            "state": record.session.state_dict(),
        }


@app.post("/api/puzzles/sessions/{session_id}/hint")
def puzzle_hint(session_id: str, request: PuzzleHintRequest) -> dict[str, Any]:
    record = store.get_puzzle_session(session_id)
    with record.lock:
        try:
            hint = record.session.reveal_hint(request.level)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"hint": asdict(hint), "state": record.session.state_dict()}


# ---------------------------------------------------------------------------
# Post-Game Analysis, AI Coach & Progress Dashboard
# ---------------------------------------------------------------------------
@app.post("/api/analysis/game")
def analyze_game(request: AnalyzeGameRequest) -> dict[str, Any]:
    try:
        return analyze_pgn_game(
            request.pgn, ai=store.ai, repository=store.repository
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/coach/ask")
def ask_coach(request: CoachAskRequest) -> dict[str, Any]:
    try:
        return store.coach_assistant.advise(
            request.fen,
            question=request.question,
            player_level=request.player_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/progress")
def progress_summary(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    uid = _user_id_from_header(authorization)
    lesson_ids = tuple(entry.lesson.lesson_id for entry in store.curriculum.all())
    puzzle_ids = tuple(p.puzzle_id for p in store.puzzles.all())
    return store.progress.summary(lesson_ids, puzzle_ids, user_id=uid)


WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(WEB_ROOT / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(WEB_ROOT / "sw.js", media_type="application/javascript")


@app.get("/icon.svg", include_in_schema=False)
def app_icon() -> FileResponse:
    return FileResponse(WEB_ROOT / "icon.svg", media_type="image/svg+xml")


app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")
