"""KnightForge chess rules, analysis, and knowledge package."""

from .core import ChessGame, GameStatus, MoveResult
from .guided_learning import (\n    CoachPrompt,\n    GuidedLesson,\n    GuidedLessonSession,\n    LessonNode,\n    MoveSubmission,\n)
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

__all__ = [\n\n]""KnightForge chess rules, analysis, and knowledge package."""

from .core import ChessGame, GameStatus, MoveResult
from .guided_learning import (\n    CoachPrompt,\n    GuidedLesson,\n    GuidedLessonSession,\n    LessonNode,\n    MoveSubmission,\n)
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
    "ChessGame",
    "CoachPrompt",
    "GuidedLesson",
    "GuidedLessonSession",
    "LessonNode",
    "MoveSubmission",
    "GameStatus",
    "KnowledgeLine",
    "KnowledgeRecord",
    "KnowledgeType",
    "MoveOption",
    "MoveResult",
    "OpeningCatalog",
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
