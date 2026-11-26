from __future__ import annotations

from pathlib import Path

from knightforge_engine.opening_catalog import OpeningCatalog
from knightforge_engine.opening_dataset import LAUNCH_SYSTEM_IDS, load_lichess_opening_trees

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "openings"


def _labels(nodes):
    for node in nodes:
        if node.label:
            yield node.label
        yield from _labels(node.children)


def test_cc0_dataset_imports_all_thirty_launch_systems_as_legal_trees() -> None:
    catalog = OpeningCatalog.load(DATA / "opening_taxonomy.json")
    trees, report = load_lichess_opening_trees(
        DATA / "lichess_cc0" / "openings.json", catalog
    )

    assert tuple(trees) == LAUNCH_SYSTEM_IDS
    assert report.tree_count == 30
    assert report.source_line_count == 2744
    assert report.imported_line_count == 2744
    assert report.skipped_line_count == 0

    for opening_id in LAUNCH_SYSTEM_IDS:
        tree = trees[opening_id]
        tree.validate()
        assert tree.branch_count() == report.per_system_move_nodes[opening_id]
        assert tree.branch_count() > 0
        assert tree.review_status == "in_review"
        assert tree.license_name == "CC0 1.0 Universal"


def test_imported_opening_trees_retain_named_variations_and_jobava_content() -> None:
    catalog = OpeningCatalog.load(DATA / "opening_taxonomy.json")
    trees, _ = load_lichess_opening_trees(
        DATA / "lichess_cc0" / "openings.json", catalog
    )

    sicilian_labels = " ".join(_labels(trees["open-sicilian"].roots))
    assert "Najdorf Variation" in sicilian_labels
    assert "Dragon Variation" in sicilian_labels
    assert "Sveshnikov Variation" in sicilian_labels

    london_labels = " ".join(_labels(trees["london"].roots))
    assert "Rapport-Jobava System" in london_labels
    assert "Poisoned Pawn Variation" in london_labels
