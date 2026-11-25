"""FastAPI session server for the KnightForge browser board."""
from __future__ import annotations

import json
import os
import secrets
import threading
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
from .full_game import FullGame
from .guided_learning import GuidedLesson, LessonNode
from .opening_catalog import OpeningCatalog
from .opening_courses import london_jobava_courses
from .opening_import import parse_opening_import
from .opening_repository import OpeningRepository
from .opening_training import OpeningTrainingSession, TrainingMode
from .opening_tree import OpeningTree, VariationNode
from .positional_analysis import analyze_position
from .strategy_training import EXERCISES, LESSONS, StrategyMode, StrategySession
from .tactics_training import PUZZLES, TacticsMode, TacticsSession

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
    hint_level: int = 0

class SessionStore:
    """Thread-safe, process-local session registry for single-worker deployments."""
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._training_sessions: dict[str, tuple[OpeningTrainingSession, threading.RLock]] = {}
        self._tactics_sessions: dict[str, tuple[TacticsSession, threading.RLock]] = {}
        self._strategy_sessions: dict[str, tuple[StrategySession, threading.RLock]] = {}
        self._full_games: dict[str, tuple[FullGame, threading.RLock]] = {}
        self._lock = threading.RLock()
        self.repository = OpeningRepository.load(Path(os.environ.get("KNIGHTFORGE_OPENINGS_PATH", "data/openings/repository.json")))
        data_root = Path(__file__).resolve().parents[2] / "data" / "openings"
        self.study_openings: dict[str, OpeningTree] = {}
        self.opening_catalog: OpeningCatalog | None = None
        batch_path = data_root / "curated_batch_01.json"
        taxonomy_path = data_root / "opening_taxonomy.json"
        if batch_path.exists() and taxonomy_path.exists():
            try:
                batch = json.loads(batch_path.read_text(encoding="utf-8"))
                records = parse_opening_import(batch)
                self.study_openings = {record.opening_id: record for record in records}
                self.opening_catalog = OpeningCatalog.load(taxonomy_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                # Optional study content must not take down ordinary chess sessions.
                self.study_openings = {}
                self.opening_catalog = None
        # Built-in KnightForge repertoire courses are validated before exposure.
        for course in london_jobava_courses():
            self.study_openings.setdefault(course.opening_id, course)
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

def apply_mode_policy(payload: dict, record: SessionRecord) -> dict:
    """Enforce hint disclosure on every session response, not only the UI."""
    state = payload.get("state", payload)
    state["mode"] = record.mode
    coach = state["coach"]
    engine = state["engine"]
    expected = record.coach.prompt().prompt.expected_uci
    coach["hints_available"] = expected is not None and record.mode != "mastery"

    if record.mode in {"practice", "mastery"}:
        # Do not leak the lesson answer through prompt text, SAN/UCI fields,
        # explanation, arrows, or engine candidate payloads.
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
        # Move-comparison payloads also contain the engine's best SAN/UCI move.
        # Keep learner feedback, but never disclose the answer in test modes.
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


def state_for(record: SessionRecord) -> dict:
    return apply_mode_policy(coach_state_payload(record.coach.prompt()), record)

class CreateSessionRequest(BaseModel):
    mode: Mode = "guided"

class MoveRequest(BaseModel):
    uci: str = Field(min_length=4, max_length=5, pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")

class HintRequest(BaseModel):
    level: int = Field(ge=1, le=4)

class CreateTrainingRequest(BaseModel):
    opening_id: str = Field(min_length=1, max_length=100)
    mode: TrainingMode = "practice"
    learner_color: Literal["white", "black"] | None = None

class CreateTacticsRequest(BaseModel):
    puzzle_id: str = Field(min_length=1, max_length=100)
    mode: TacticsMode = "practice"

class CreateStrategyRequest(BaseModel):
    exercise_id: str = Field(min_length=1, max_length=100)
    mode: StrategyMode = "practice"

class PositionalAnalysisRequest(BaseModel):
    fen: str = Field(min_length=15, max_length=120)
    candidate_uci: list[str] | None = Field(default=None, max_length=12)

def _full_game_record(game_id: str) -> tuple[FullGame, threading.RLock]:
    with store._lock:
        record = store._full_games.get(game_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Game not found or expired.")
    return record


@app.post("/api/games")
def create_full_game() -> dict:
    game = FullGame()
    game_id = secrets.token_urlsafe(18)
    with store._lock:
        store._full_games[game_id] = (game, threading.RLock())
    return {"game_id": game_id, "state": game.state()}


@app.get("/api/games/{game_id}")
def get_full_game(game_id: str) -> dict:
    game, lock = _full_game_record(game_id)
    with lock:
        return {"game_id": game_id, "state": game.state()}


@app.post("/api/games/{game_id}/moves")
def play_full_game_move(game_id: str, request: MoveRequest) -> dict:
    game, lock = _full_game_record(game_id)
    with lock:
        try:
            return game.play(request.uci)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/undo")
def undo_full_game(game_id: str) -> dict:
    game, lock = _full_game_record(game_id)
    with lock:
        try:
            return {"state": game.undo()}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/restart")
def restart_full_game(game_id: str) -> dict:
    game, lock = _full_game_record(game_id)
    with lock:
        return {"state": game.restart()}


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
        if result.submission.applied and record.mode == "practice":
            record.hint_level = 0
        return apply_mode_policy(submission_payload(result), record)

@app.post("/api/sessions/{session_id}/hints")
def reveal_hint(session_id: str, request: HintRequest) -> dict:
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
def undo(session_id: str) -> dict:
    record = store.get(session_id)
    with record.lock:
        try:
            record.coach.undo()
            record.hint_level = 0
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"state": state_for(record)}

@app.post("/api/sessions/{session_id}/restart")
def restart(session_id: str) -> dict:
    record = store.get(session_id)
    with record.lock:
        record.coach.restart()
        record.hint_level = 0
        return {"state": state_for(record)}


def _opening_mainline_san(opening: OpeningTree) -> list[str]:
    board = chess.Board(opening.starting_fen)
    moves: list[str] = []
    for uci in opening.mainline_uci():
        move = chess.Move.from_uci(uci)
        moves.append(board.san(move))
        board.push(move)
    return moves


def _opening_node_payload(
    board: chess.Board, node: VariationNode, path: tuple[str, ...]
) -> dict:
    move = chess.Move.from_uci(node.move_uci)
    san = board.san(move)
    next_board = board.copy()
    next_board.push(move)
    next_path = (*path, node.move_uci)
    return {
        "uci": node.move_uci,
        "san": san,
        "label": node.label,
        "explanation": node.explanation,
        "white_plan": node.white_plan,
        "black_plan": node.black_plan,
        "path_uci": list(next_path),
        "fen_after": next_board.fen(),
        "children": [
            _opening_node_payload(next_board, child, next_path)
            for child in node.children
        ],
    }


def _opening_detail_payload(opening: OpeningTree, catalog: OpeningCatalog | None) -> dict:
    system = catalog.get_system_detail(opening.opening_id) if catalog else None
    board = chess.Board(opening.starting_fen)
    return {
        "opening_id": opening.opening_id,
        "name": opening.name,
        "side": opening.side,
        "aliases": list(opening.aliases),
        "family_id": system.family_id if system else None,
        "family_name": system.family_name if system else "Uncategorised",
        "review_status": opening.review_status,
        "source_name": opening.source_name,
        "license_name": opening.license_name,
        "starting_fen": opening.starting_fen,
        "branch_count": opening.branch_count(),
        "mainline_san": _opening_mainline_san(opening),
        "roots": [
            _opening_node_payload(board, node, ())
            for node in opening.roots
        ],
    }



@app.get("/api/tactics")
def list_tactical_puzzles(theme: str | None = None, difficulty: str | None = None) -> dict:
    puzzles = [
        puzzle for puzzle in PUZZLES
        if (theme is None or puzzle.theme == theme)
        and (difficulty is None or puzzle.difficulty == difficulty)
    ]
    return {
        "items": [
            {"puzzle_id": puzzle.puzzle_id, "title": puzzle.title,
             "theme": puzzle.theme, "difficulty": puzzle.difficulty}
            for puzzle in puzzles
        ],
        "count": len(puzzles),
        "themes": sorted({puzzle.theme for puzzle in PUZZLES}),
        "difficulties": sorted({puzzle.difficulty for puzzle in PUZZLES}),
    }


@app.post("/api/tactics")
def create_tactics_session(request: CreateTacticsRequest) -> dict:
    puzzle = next((item for item in PUZZLES if item.puzzle_id == request.puzzle_id), None)
    if puzzle is None:
        raise HTTPException(status_code=404, detail="Tactical puzzle not found.")
    try:
        session = TacticsSession(puzzle, request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session_id = secrets.token_urlsafe(18)
    with store._lock:
        store._tactics_sessions[session_id] = (session, threading.RLock())
    return {"tactics_id": session_id, "state": session.state()}


def _tactics_record(session_id: str) -> tuple[TacticsSession, threading.RLock]:
    with store._lock:
        record = store._tactics_sessions.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tactics session not found or expired.")
    return record


@app.get("/api/tactics/{session_id}")
def get_tactics_session(session_id: str) -> dict:
    session, lock = _tactics_record(session_id)
    with lock:
        return {"state": session.state()}


@app.post("/api/tactics/{session_id}/moves")
def submit_tactics_move(session_id: str, request: MoveRequest) -> dict:
    session, lock = _tactics_record(session_id)
    with lock:
        try:
            return session.submit(request.uci)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/tactics/{session_id}/hints")
def reveal_tactics_hint(session_id: str, request: HintRequest) -> dict:
    session, lock = _tactics_record(session_id)
    with lock:
        try:
            return {"state": session.reveal_hint(request.level)}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/tactics/{session_id}/restart")
def restart_tactics_session(session_id: str) -> dict:
    session, lock = _tactics_record(session_id)
    with lock:
        return {"state": session.restart()}



@app.get("/api/strategy/lessons")
def list_strategy_lessons(theme: str | None = None) -> dict:
    items = [lesson for lesson in LESSONS if theme is None or lesson.theme == theme]
    return {
        "items": [
            {"lesson_id": item.lesson_id, "title": item.title,
             "theme": item.theme, "level": item.level}
            for item in items
        ],
        "count": len(items),
        "themes": sorted({item.theme for item in LESSONS}),
        "content_status": "editorial_draft",
    }


@app.get("/api/strategy/lessons/{lesson_id}")
def get_strategy_lesson(lesson_id: str) -> dict:
    lesson = next((item for item in LESSONS if item.lesson_id == lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Strategy lesson not found.")
    return {
        "lesson_id": lesson.lesson_id, "title": lesson.title,
        "theme": lesson.theme, "level": lesson.level,
        "principle": lesson.principle, "why_it_matters": lesson.why_it_matters,
        "checklist": list(lesson.checklist), "example_plan": lesson.example_plan,
        "content_status": "editorial_draft",
    }


@app.get("/api/strategy/exercises")
def list_strategy_exercises(theme: str | None = None, difficulty: str | None = None) -> dict:
    items = [
        item for item in EXERCISES
        if (theme is None or item.theme == theme)
        and (difficulty is None or item.difficulty == difficulty)
    ]
    return {
        "items": [
            {"exercise_id": item.exercise_id, "title": item.title,
             "theme": item.theme, "difficulty": item.difficulty,
             "position_phase": "middlegame" if item.exercise_id.startswith("middlegame-") else "opening"}
            for item in items
        ],
        "count": len(items),
        "themes": sorted({item.theme for item in EXERCISES}),
        "difficulties": sorted({item.difficulty for item in EXERCISES}),
        "content_status": "editorial_draft",
    }


@app.post("/api/strategy/analyze")
def analyze_strategy_position(request: PositionalAnalysisRequest) -> dict:
    try:
        return analyze_position(request.fen, request.candidate_uci)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/strategy")
def create_strategy_session(request: CreateStrategyRequest) -> dict:
    exercise = next((item for item in EXERCISES if item.exercise_id == request.exercise_id), None)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Strategy exercise not found.")
    try:
        session = StrategySession(exercise, request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session_id = secrets.token_urlsafe(18)
    with store._lock:
        store._strategy_sessions[session_id] = (session, threading.RLock())
    return {"strategy_id": session_id, "state": session.state()}


def _strategy_record(session_id: str) -> tuple[StrategySession, threading.RLock]:
    with store._lock:
        record = store._strategy_sessions.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Strategy session not found or expired.")
    return record


@app.get("/api/strategy/{session_id}")
def get_strategy_session(session_id: str) -> dict:
    session, lock = _strategy_record(session_id)
    with lock:
        return {"state": session.state()}


@app.post("/api/strategy/{session_id}/moves")
def submit_strategy_move(session_id: str, request: MoveRequest) -> dict:
    session, lock = _strategy_record(session_id)
    with lock:
        try:
            return session.submit(request.uci)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/strategy/{session_id}/hints")
def reveal_strategy_hint(session_id: str, request: HintRequest) -> dict:
    session, lock = _strategy_record(session_id)
    with lock:
        try:
            return {"state": session.reveal_hint(request.level)}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/strategy/{session_id}/restart")
def restart_strategy_session(session_id: str) -> dict:
    session, lock = _strategy_record(session_id)
    with lock:
        return {"state": session.restart()}

@app.post("/api/training")
def create_training(request: CreateTrainingRequest) -> dict:
    opening = store.study_openings.get(request.opening_id)
    if opening is None:
        raise HTTPException(status_code=404, detail="Opening study not found.")
    learner_color = request.learner_color or (
        opening.side if opening.side in {"white", "black"} else "white"
    )
    try:
        training = OpeningTrainingSession(opening, learner_color, request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session_id = secrets.token_urlsafe(18)
    lock = threading.RLock()
    with store._lock:
        store._training_sessions[session_id] = (training, lock)
    return {"training_id": session_id, "state": training.state()}


def _training_record(training_id: str) -> tuple[OpeningTrainingSession, threading.RLock]:
    with store._lock:
        record = store._training_sessions.get(training_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Opening training session not found or expired.")
    return record


@app.get("/api/training/{training_id}")
def get_training(training_id: str) -> dict:
    training, lock = _training_record(training_id)
    with lock:
        return {"state": training.state()}


@app.post("/api/training/{training_id}/moves")
def submit_training_move(training_id: str, request: MoveRequest) -> dict:
    training, lock = _training_record(training_id)
    with lock:
        try:
            return training.submit(request.uci)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/training/{training_id}/hints")
def training_hint(training_id: str, request: HintRequest) -> dict:
    training, lock = _training_record(training_id)
    with lock:
        try:
            return {"state": training.reveal_hint(request.level)}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/training/{training_id}/undo")
def undo_training(training_id: str) -> dict:
    training, lock = _training_record(training_id)
    with lock:
        try:
            return {"state": training.undo()}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/training/{training_id}/restart")
def restart_training(training_id: str) -> dict:
    training, lock = _training_record(training_id)
    with lock:
        return {"state": training.restart()}


@app.get("/api/openings")
def list_openings(query: str = "", side: str | None = None) -> dict:
    """List legally validated study trees, including editorial review status."""
    if side not in {None, "white", "black", "both"}:
        raise HTTPException(status_code=422, detail="side must be white, black, or both.")
    term = query.strip().casefold()
    items = []
    for opening in store.study_openings.values():
        if side and opening.side not in {side, "both"}:
            continue
        def variation_labels(nodes):
            for node in nodes:
                yield node.label
                yield from variation_labels(node.children)

        searchable = (opening.name, opening.opening_id, *opening.aliases,
                      *tuple(variation_labels(opening.roots)))
        if term and not any(term in value.casefold() for value in searchable):
            continue
        system = (
            store.opening_catalog.get_system_detail(opening.opening_id)
            if store.opening_catalog else None
        )
        items.append({
            "opening_id": opening.opening_id,
            "name": opening.name,
            "side": opening.side,
            "aliases": list(opening.aliases),
            "family_name": system.family_name if system else "Uncategorised",
            "review_status": opening.review_status,
            "branch_count": opening.branch_count(),
            "mainline_san": _opening_mainline_san(opening),
        })
    return {"items": items, "count": len(items), "content_status": "in_review"}


@app.get("/api/openings/{opening_id}")
def get_opening(opening_id: str) -> dict:
    """Return a SAN/FEN annotated, legally validated opening variation tree."""
    opening = store.study_openings.get(opening_id)
    if opening is None:
        raise HTTPException(status_code=404, detail="Opening study not found.")
    return _opening_detail_payload(opening, store.opening_catalog)


WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")
app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")
