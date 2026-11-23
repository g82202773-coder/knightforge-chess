"""FastAPI session server for the KnightForge browser board."""
from __future__ import annotations
import os, secrets, threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import chess
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .adaptive_coach import AdaptiveOpeningCoach
from .analysis import StockfishAnalyzer
from .coach_presentation import coach_state_payload, submission_payload
from .guided_learning import GuidedLesson, LessonNode
from .opening_repository import OpeningRepository

Mode = Literal["guided", "practice", "mastery"]

def demo_lesson() -> GuidedLesson:
    return GuidedLesson("open-game-first-five", "Open Game: First Five Moves", "white", (
        LessonNode("e2e4", "Occupy the centre. The e4-pawn controls d5 and f5 and opens lines for your bishop and queen.", children=(
            LessonNode("e7e5", "Black contests the centre with the same central pawn advance.", children=(
                LessonNode("g1f3", "Develop the knight toward the centre and attack the e5-pawn.", children=(
                    LessonNode("b8c6", "Black develops a knight and supports the e5-pawn.", children=(
                        LessonNode("f1b5", "The Ruy Lopez bishop develops with pressure on the c6-knight."),
                    )),
                )),
            )),
        )),
    ))

@dataclass
class SessionRecord:
    coach: AdaptiveOpeningCoach
    mode: Mode
    lock: threading.RLock

class SessionStore:
    """Thread-safe, process-local session registry for single-worker deployments."""
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = threading.RLock()
        self.repository = OpeningRepository.load(Path(os.environ.get("KNIGHTFORGE_OPENINGS_PATH", "data/openings/repository.json")))
        self.analyzer: StockfishAnalyzer | None = None
        executable = os.environ.get("STOCKFISH_PATH")
        if executable:
            try:
                self.analyzer = StockfishAnalyzer(executable)
            except (OSError, RuntimeError):
                self.analyzer = None

    def create(self, mode: Mode) -> tuple[str, SessionRecord]:
        coach = AdaptiveOpeningCoach(demo_lesson(), self.repository, analyzer=self.analyzer,
                                     analysis_time_limit=0.75, analysis_multipv=2)
        session_id = secrets.token_urlsafe(18)
        record = SessionRecord(coach, mode, threading.RLock())
        with self._lock:
            self._sessions[session_id] = record
        return session_id, record

    def get(self, session_id: str) -> SessionRecord:
        with self._lock:
            record = self._sessions.get(session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Chess session not found or expired.")
        return record

store = SessionStore()
app = FastAPI(title="KnightForge Chess Sessions", version="0.1.0")

def state_for(record: SessionRecord) -> dict:
    payload = coach_state_payload(record.coach.prompt())
    payload["mode"] = record.mode
    if record.mode == "mastery":
        payload["coach"]["active_hint"] = None
        payload["engine"]["recommendation_arrow"] = None
    return payload

class CreateSessionRequest(BaseModel):
    mode: Mode = "guided"

class MoveRequest(BaseModel):
    uci: str = Field(min_length=4, max_length=5, pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")

class HintRequest(BaseModel):
    level: int = Field(ge=1, le=4)

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "stockfish_available": store.analyzer is not None}

@app.post("/api/sessions")
def create_session(request: CreateSessionRequest) -> dict:
    session_id, record = store.create(request.mode)
    with record.lock:
        return {"session_id": session_id, "state": state_for(record)}

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    record = store.get(session_id)
    with record.lock:
        return {"session_id": session_id, "state": state_for(record)}

@app.post("/api/sessions/{session_id}/moves")
def submit_move(session_id: str, request: MoveRequest) -> dict:
    record = store.get(session_id)
    with record.lock:
        try:
            result = record.coach.submit_uci(request.uci)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        payload = submission_payload(result)
        payload["state"]["mode"] = record.mode
        if record.mode == "mastery":
            payload["state"]["coach"]["active_hint"] = None
            payload["state"]["engine"]["recommendation_arrow"] = None
        return payload

@app.post("/api/sessions/{session_id}/hints")
def reveal_hint(session_id: str, request: HintRequest) -> dict:
    record = store.get(session_id)
    if record.mode == "mastery":
        raise HTTPException(status_code=403, detail="Hints are disabled in Mastery mode.")
    with record.lock:
        try:
            record.coach.reveal_hint(request.level)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": state_for(record)}

@app.post("/api/sessions/{session_id}/undo")
def undo(session_id: str) -> dict:
    record = store.get(session_id)
    with record.lock:
        try:
            record.coach.undo()
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": state_for(record)}

@app.post("/api/sessions/{session_id}/restart")
def restart(session_id: str) -> dict:
    record = store.get(session_id)
    with record.lock:
        record.coach.restart()
        return {"state": state_for(record)}

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")
app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")
