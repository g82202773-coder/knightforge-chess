"""Validation tests for the first curated opening study batch."""

import json
from pathlib import Path

from knightforge_engine.opening_catalog import OpeningCatalog
from knightforge_engine.opening_coverage import analyze_opening_coverage
from knightforge_engine.opening_import import parse_opening_import
from knightforge_engine.opening_repository import OpeningRepository

ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "openings" / "curated_batch_01.json"
TAXONOMY_PATH = ROOT / "data" / "openings" / "opening_taxonomy.json"


def test_curated_batch_contains_taxonomy_systems_and_legal_anchored_lines(tmp_path):
    payload = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
    taxonomy = OpeningCatalog.load(TAXONOMY_PATH)
    records = parse_opening_import(payload)

    assert len(records) == 8
    assert len({record.opening_id for record in records}) == len(records)

    for record in records:
        system = taxonomy.get_system_detail(record.opening_id)
        assert system is not None, record.opening_id
        assert record.name == system.name
        assert record.review_status == "in_review"
        assert record.source_name
        assert "Pending" in record.license_name
        assert record.anchor_uci
        record.validate()
        assert record._contains_path(record.roots, record.anchor_uci)


def test_curated_batch_imports_atomically_and_is_not_misreported_as_published(tmp_path):
    payload = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
    repository = OpeningRepository.load(tmp_path / "openings.json")
    taxonomy = OpeningCatalog.load(TAXONOMY_PATH)

    imported = parse_opening_import(payload)
    repository.add_many(imported)
    report = analyze_opening_coverage(taxonomy, repository)

    assert len(repository.all()) == 8
    assert report.stored_tree_count == 8
    assert report.reviewed_tree_ids == ()
    assert report.matched_system_ids == ()
    assert set(report.missing_system_ids) >= {record.opening_id for record in imported}
