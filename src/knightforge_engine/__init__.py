"""KnightForge chess rules, analysis, and knowledge package."""

from .core import ChessGame, GameStatus, MoveResult
from .knowledge import KnowledgeLine, KnowledgeRecord, KnowledgeType

__all__ = [
    "ChessGame",
    "GameStatus",
    "KnowledgeLine",
    "KnowledgeRecord",
    "KnowledgeType",
    "MoveResult",
    "OpeningTree",
    "VariationNode",
]

from .opening_tree import OpeningTree, VariationNode
