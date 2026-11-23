"""KnightForge chess rules, analysis, and knowledge package."""

from .adaptive_coach import AdaptiveOpeningCoach, OpeningCoachState, OpeningCoachSubmission
from .analysis import AnalysisResult, EngineLine, StockfishAnalyzer
from .coach_decision import CoachDecisionLayer, CoachHint, EngineRecommendation, MoveComparison
from .core import ChessGame, GameStatus, MoveResult
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
from .opening_tree import OpeningTree, VariationNode
from .position import MoveOption, PositionInspector, SquareState
from .tactics import TacticalCandidate, TacticalScan, TacticalScanner
from .variation_matching import (
    PositionBasedVariationMatcher,
    VariationMatchResult,
    VariationPositionMatch,
)

__all__ = [
    "AdaptiveOpeningCoach",
    "AnalysisResult",
    "ChessGame",
    "CoachDecisionLayer",
    "CoachHint",
    "CoachPrompt",
    "EngineLine",
    "EngineRecommendation",
    "GameStatus",
    "GuidedLesson",
    "GuidedLessonSession",
    "KnowledgeLine",
    "KnowledgeRecord",
    "KnowledgeType",
    "LessonNode",
    "MoveComparison",
    "MoveOption",
    "MoveResult",
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
    "SquareState",
    "StockfishAnalyzer",
    "TacticalCandidate",
    "TacticalScan",
    "TacticalScanner",
    "VariationMatchResult",
    "VariationNode",
    "VariationPositionMatch",
    "analyze_opening_coverage",
    "import_openings",
    "parse_opening_import",
]
