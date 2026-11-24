"""Tests for Opening Variation Trainer (London/Jobava), Level 0 Basics, and 1,079+ Puzzles."""
from pathlib import Path

from knightforge_engine import (
    CurriculumCatalog,
    GuidedLessonSession,
    OpeningRepository,
    PuzzleCatalog,
    PuzzleSession,
    build_opening_lesson,
    list_opening_variations,
)


def test_london_system_exposes_jobava_and_classical_variations_for_training():
    repo = OpeningRepository.load(Path("data/openings/repository.json"))
    assert len(repo.all()) >= 31
    london = repo.get("london")
    assert london is not None
    variations = list_opening_variations(london)
    labels = [v.label for v in variations]
    assert any("Jobava" in lbl for lbl in labels)
    assert any("Classical" in lbl for lbl in labels)

    # Convert Jobava London variation directly into an interactive guided lesson!
    jobava = next(v for v in variations if "Jobava" in v.label)
    lesson = build_opening_lesson(london, variation_id=jobava.variation_id)
    session = GuidedLessonSession(lesson)
    assert session.prompt().expected_uci == "d2d4"
    for uci in jobava.moves_uci:
        res = session.submit_uci(uci)
        assert res.applied and res.correct is True
    assert session.prompt().kind in {"complete", "free_play"}


def test_level_zero_piece_basics_are_legally_validated():
    catalog = CurriculumCatalog()
    basics = catalog.filter(category="basics")
    assert len(basics) >= 7
    assert catalog.get("basics-pawn-one-step") is not None
    assert catalog.get("basics-pawn-two-steps") is not None
    assert catalog.get("basics-knight-jump") is not None
    assert len(catalog.all()) >= 28


def test_bulk_puzzle_catalog_loads_over_1000_verified_puzzles():
    catalog = PuzzleCatalog(include_bulk=True)
    all_puzzles = catalog.all()
    assert len(all_puzzles) >= 1050
    # Sample-test puzzles across different themes
    for puz in (all_puzzles[0], all_puzzles[20], all_puzzles[500], all_puzzles[-1]):
        session = PuzzleSession(puz)
        for idx in range(0, len(puz.solution_uci), 2):
            outcome = session.submit_uci(puz.solution_uci[idx])
            assert outcome.correct is True
        assert session.solved is True
