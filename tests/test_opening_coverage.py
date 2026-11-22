"""Tests for taxonomy-to-move-tree opening coverage reporting."""

from knightforge_engine.opening_catalog import OpeningCatalog
from knightforge_engine.opening_coverage import analyze_opening_coverage
from knightforge_engine.opening_repository import OpeningRepository
from knightforge_engine.opening_tree import OpeningTree, VariationNode


def _catalog():
    return OpeningCatalog.from_dict({
        "schema_version": "1.0",
        "families": [{
            "id": "open-games",
            "name": "Open Games",
            "side": "white",
            "systems": [
                {"id": "ruy-lopez", "name": "Ruy Lopez",
                 "variations": ["Berlin Defence", "Marshall Attack"]},
                {"id": "italian-game", "name": "Italian Game", "variations": ["Evans Gambit"]},
            ],
        }],
    })


def test_coverage_reports_missing_systems_and_variations(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    repository.add(OpeningTree(
        opening_id="ruy-lopez",
        name="Ruy Lopez",
        side="white",
        roots=(VariationNode("e2e4", label="Berlin Defence"),),
    ))

    report = analyze_opening_coverage(_catalog(), repository)

    assert report.taxonomy_system_count == 2
    assert report.taxonomy_variation_count == 3
    assert report.matched_system_ids == ("ruy-lopez",)
    assert report.missing_system_ids == ("italian-game",)
    assert report.matched_variations == ("ruy-lopez:berlin defence",)
    assert report.missing_variations == (
        "italian-game:evans gambit",
        "ruy-lopez:marshall attack",
    )
    assert report.total_move_nodes == 1
    assert report.system_coverage_ratio == 0.5
    assert report.variation_coverage_ratio == 1 / 3


def test_coverage_flags_missing_provenance_eco_and_review_state(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    repository.add(OpeningTree(
        opening_id="ruy-lopez",
        name="Ruy Lopez",
        side="white",
        roots=(VariationNode("e2e4"),),
    ))

    report = analyze_opening_coverage(_catalog(), repository)

    assert report.trees_without_eco == ("ruy-lopez",)
    assert report.trees_without_source == ("ruy-lopez",)
    assert report.trees_without_license == ("ruy-lopez",)
    assert report.draft_tree_ids == ("ruy-lopez",)
    assert report.reviewed_tree_ids == ()


def test_coverage_counts_reviewed_records_and_serializes(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    repository.add(OpeningTree(
        opening_id="ruy-lopez",
        name="Ruy Lopez",
        side="white",
        source_name="Licensed source",
        license_name="CC BY 4.0",
        review_status="reviewed",
        roots=(VariationNode("e2e4", label="Berlin Defence"),),
    ))

    report = analyze_opening_coverage(_catalog(), repository)
    payload = report.to_dict()

    assert report.reviewed_tree_ids == ("ruy-lopez",)
    assert payload["stored_tree_count"] == 1
    assert payload["system_coverage_ratio"] == 0.5


def test_empty_placeholder_tree_does_not_count_as_playable_coverage(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    repository.add(OpeningTree(
        opening_id="ruy-lopez",
        name="Ruy Lopez",
        side="white",
        roots=(),
    ))

    report = analyze_opening_coverage(_catalog(), repository)

    assert report.stored_tree_count == 1
    assert report.matched_system_ids == ()
    assert report.missing_system_ids == ("italian-game", "ruy-lopez")
    assert report.trees_without_moves == ("ruy-lopez",)
    assert report.system_coverage_ratio == 0.0
