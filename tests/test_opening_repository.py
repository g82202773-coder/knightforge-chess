"""Tests for the persistent opening repository."""

import json

import pytest

from knightforge_engine.opening_repository import OpeningRepository
from knightforge_engine.opening_tree import OpeningTree, VariationNode


def _opening(
    opening_id: str = "ruy-lopez",
    name: str = "Ruy Lopez",
    eco: str = "C60",
    aliases: tuple[str, ...] = ("Spanish Opening",),
    move: str = "e2e4",
) -> OpeningTree:
    return OpeningTree(
        opening_id=opening_id,
        name=name,
        side="white",
        eco=eco,
        aliases=aliases,
        roots=(VariationNode(move),),
    )


def test_missing_repository_loads_as_empty(tmp_path):
    repository = OpeningRepository.load(tmp_path / "nested" / "openings.json")
    assert repository.all() == ()
    assert repository.get("missing") is None


def test_add_persists_and_reload_restores_validated_opening(tmp_path):
    path = tmp_path / "data" / "openings.json"
    repository = OpeningRepository.load(path)
    opening = _opening()

    repository.add(opening)
    restored = OpeningRepository.load(path)

    assert restored.get("ruy-lopez") == opening
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_add_rejects_duplicate_id_without_overwriting(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    original = _opening()
    repository.add(original)

    with pytest.raises(ValueError, match="already exists"):
        repository.add(_opening(name="Different opening"))

    assert OpeningRepository.load(repository.path).get("ruy-lopez") == original


def test_upsert_replaces_existing_record_and_persists(tmp_path):
    path = tmp_path / "openings.json"
    repository = OpeningRepository.load(path)
    repository.add(_opening())
    replacement = _opening(name="Ruy Lopez: Updated", aliases=("Spanish",))

    repository.upsert(replacement)

    restored = OpeningRepository.load(path)
    assert restored.get("ruy-lopez") == replacement
    assert len(restored.all()) == 1


def test_search_matches_id_name_eco_and_alias(tmp_path):
    repository = OpeningRepository.load(tmp_path / "openings.json")
    repository.add(_opening())

    assert repository.search("RUY")[0].opening_id == "ruy-lopez"
    assert repository.search("c60")[0].name == "Ruy Lopez"
    assert repository.search("spanish")[0].opening_id == "ruy-lopez"
    assert repository.search("absent") == ()


def test_remove_persists_and_reports_missing_ids(tmp_path):
    path = tmp_path / "openings.json"
    repository = OpeningRepository.load(path)
    repository.add(_opening())

    assert repository.remove("ruy-lopez") is True
    assert repository.remove("ruy-lopez") is False
    assert OpeningRepository.load(path).all() == ()


def test_repository_rejects_unknown_schema_version(tmp_path):
    path = tmp_path / "openings.json"
    path.write_text(json.dumps({"schema_version": 99, "openings": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported"):
        OpeningRepository.load(path)


def test_repository_rejects_duplicate_ids_in_file(tmp_path):
    path = tmp_path / "openings.json"
    record = _opening().to_dict()
    path.write_text(
        json.dumps({"schema_version": 1, "openings": [record, record]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate opening_id"):
        OpeningRepository.load(path)


def test_repository_rejects_corrupt_json(tmp_path):
    path = tmp_path / "openings.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot load"):
        OpeningRepository.load(path)


def test_add_rejects_illegal_opening_without_writing(tmp_path):
    path = tmp_path / "openings.json"
    repository = OpeningRepository.load(path)
    invalid = _opening(move="e2e5")

    with pytest.raises(ValueError, match="Illegal move"):
        repository.add(invalid)

    assert not path.exists()
    assert repository.all() == ()
