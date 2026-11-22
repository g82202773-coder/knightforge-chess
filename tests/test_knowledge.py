import pytest

from knightforge_engine.knowledge import (
    KnowledgeLine,
    KnowledgeRecord,
    KnowledgeType,
    ReviewStatus,
)


def test_legal_opening_line_validates() -> None:
    KnowledgeLine(("e2e4", "c7c5"), label="Sicilian Defence").validate()


def test_illegal_opening_line_is_rejected() -> None:
    with pytest.raises(ValueError):
        KnowledgeLine(("e2e5",)).validate()


def test_reviewed_opening_requires_a_line_and_provenance() -> None:
    record = KnowledgeRecord(
        record_id="opening.sicilian",
        title="Sicilian Defence",
        knowledge_type=KnowledgeType.OPENING,
        summary="A response to 1.e4.",
        tags=("open-game", "semi-open"),
        source_name="KnightForge editorial",
        source_url=None,
        license_name="Original content",
        review_status=ReviewStatus.REVIEWED,
        lines=(KnowledgeLine(("e2e4", "c7c5")),),
    )
    record.validate()
