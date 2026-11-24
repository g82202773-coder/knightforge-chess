"""KnightForge chess rules, AI engine, education academy, and platform package."""

from .adaptive_coach import AdaptiveOpeningCoach, OpeningCoachState, OpeningCoachSubmission
from .ai_opponent import AIDifficulty, AIMoveDecision, CandidateEval, ChessAIOpponent
from .analysis import AnalysisResult, EngineLine, StockfishAnalyzer
from .coach_decision import CoachDecisionLayer, CoachHint, EngineRecommendation, MoveComparison
from .coach_presentation import coach_state_payload, submission_payload
from .core import ChessGame, GameStatus, MoveResult
from .curriculum import CurriculumCatalog, LessonEntry
from .game_analyzer import ChessCoachAssistant, MoveReview, analyze_pgn_game
from .game_manager import CLOCK_PRESETS, ChessClock, FullChessMatch
from .guided_learning import (
    CoachPrompt,
    GuidedLesson,
    GuidedLessonSession,
    LessonNode,
    MoveSubmission,
)
from .knowledge import KnowledgeLine, KnowledgeRecord, KnowledgeType
from .opening_catalog import (
    OpeningCatalog,
    OpeningFamily,
    OpeningReference,
    OpeningSystem,
    OpeningVariation,
)
from .opening_coverage import OpeningCoverageReport, analyze_opening_coverage
from .opening_import import OpeningImportReport, import_openings, parse_opening_import
from .opening_recognition import OpeningMatch, OpeningRecognition, OpeningRecognizer
from .opening_repository import OpeningRepository
from .opening_trainer import VariationLine, build_opening_lesson, list_opening_variations
from .opening_tree import OpeningTree, VariationNode
from .position import MoveOption, PositionInspector, SquareState
from .positional_analysis import analyze_position
from .puzzles import (
    Puzzle,
    PuzzleAttemptOutcome,
    PuzzleCatalog,
    PuzzleHint,
    PuzzleSession,
    compute_elo_delta,
)
from .storage import ProgressStore
from .tactics import TacticalCandidate, TacticalScan, TacticalScanner
from .variation_matching import (
    PositionBasedVariationMatcher,
    VariationMatchResult,
    VariationPositionMatch,
)

__all__ = [
    "AIDifficulty",
    "AIMoveDecision",
    "AdaptiveOpeningCoach",
    "AnalysisResult",
    "CLOCK_PRESETS",
    "CandidateEval",
    "ChessAIOpponent",
    "ChessClock",
    "ChessCoachAssistant",
    "ChessGame",
    "CoachDecisionLayer",
    "CoachHint",
    "CoachPrompt",
    "CurriculumCatalog",
    "EngineLine",
    "EngineRecommendation",
    "FullChessMatch",
    "GameStatus",
    "GuidedLesson",
    "GuidedLessonSession",
    "KnowledgeLine",
    "KnowledgeRecord",
    "KnowledgeType",
    "LessonEntry",
    "LessonNode",
    "MoveComparison",
    "MoveOption",
    "MoveResult",
    "MoveReview",
    "MoveSubmission",
    "OpeningCatalog",
    "OpeningCoachState",
    "OpeningCoachSubmission",
    "OpeningCoverageReport",
    "OpeningFamily",
    "OpeningImportReport",
    "OpeningMatch",
    "OpeningRecognition",
    "OpeningRecognizer",
    "OpeningReference",
    "OpeningRepository",
    "OpeningSystem",
    "OpeningTree",
    "OpeningVariation",
    "PositionBasedVariationMatcher",
    "PositionInspector",
    "ProgressStore",
    "Puzzle",
    "PuzzleAttemptOutcome",
    "PuzzleCatalog",
    "PuzzleHint",
    "PuzzleSession",
    "SquareState",
    "StockfishAnalyzer",
    "TacticalCandidate",
    "TacticalScan",
    "TacticalScanner",
    "VariationLine",
    "VariationMatchResult",
    "VariationNode",
    "VariationPositionMatch",
    "analyze_opening_coverage",
    "analyze_pgn_game",
    "analyze_position",
    "build_opening_lesson",
    "list_opening_variations",
    "coach_state_payload",
    "compute_elo_delta",
    "import_openings",
    "parse_opening_import",
    "submission_payload",
]
