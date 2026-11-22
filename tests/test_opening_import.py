"""Tests for provenance-aware opening import."""


import pytest

from knightforge_engine.opening_import import import_openings, parse_opening_import
from knightforge_engine.opening_repository import OpeningRepository
from knightforge_engine.opening_tree import OpeningTree, VariationNode


def _record(opening_id: str = "sicilian") -> dict:
    return OpeningTree(
        opening_id=opening_id,
        name="Sicilian Defence",
        side="black",
        source_name="Licensed test corpus",
        source_url="https://example.org/openings",
        license_name="CC BY 4.0",
        roots=(VariationNode("e2e4", children=(VariationNode("c7c5"),)),),
    ).to_dict()


def test_parse_import_validates_records_and_preserves_provenance():
    records = parse_opening_import({"schema_version": 1, "openings": [_record()]})
    assert len(records) == 1
    assert records[0].source_name == "Licensed test corpus"
    assert records[0].mainline_san() == ("e4", "c5")


def test_import_commits_batch_and_can_be_reloaded(tmp_path):
    path = tmp_path / "openings.json"
    repository = OpeningRepository.load(path)

    report = import_openings(
        {"schema_version": 1, "openings": [_record("sicilian"), _record("french")]},
        repository,
    )

    assert report.imported_ids == ("sicilian", "french")
    restored = OpeningRepository.load(path)
    assert len(restored.all()) == 2


def test_import_rejects_missing_provenance_before_mutation(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    record = _record()
    record["license_name"] = ""

    with pytest.raises(ValueError, match="license_name"):
        import_openings({"schema_version": 1, "openings": [record]}, repository)

    assert repository.all() == ()
    assert not repository.path.exists()


def test_import_rejects_duplicate_ids_inside_batch(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    with pytest.raises(ValueError, match="Duplicate opening_id"):
        import_openings(
            {"schema_version": 1, "openings": [_record(), _record()]}, repository
        )
    assert repository.all() == ()


def test_import_rejects_existing_ids_without_overwriting(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    original = OpeningTree.from_dict(_record())
    repository.add(original)
    replacement = _record()
    replacement["name"] = "Changed name"

    with pytest.raises(ValueError, match="already exists"):
        import_openings({"schema_version": 1, "openings": [replacement]}, repository)

    assert OpeningRepository.load(repository.path).get("sicilian") == original


def test_import_rejects_illegal_move_in_any_record_before_mutation(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    invalid = _record("invalid")
    invalid["roots"] = [{"move_uci": "e2e5"}]

    with pytest.raises(ValueError, match="Illegal move"):
        import_openings({"schema_version": 1, "openings": [_record(), invalid]}, repository)

    assert repository.all() == ()


def test_import_rejects_unknown_envelope_schema():
    with pytest.raises(ValueError, match="Unsupported"):
        parse_opening_import({"schema_version": 2, "openings": []})

def test_import_rejects_empty_opening_tree(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    record = _record()
    record["roots"] = []

    with pytest.raises(ValueError, match="no move branches"):
        import_openings({"schema_version": 1, "openings": [record]}, repository)

    assert repository.all() == ()
    assert not repository.path.exists()

