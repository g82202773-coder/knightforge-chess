"""Tests for the opening taxonomy reader."""

import pytest

from knightforge_engine.opening_catalog import OpeningCatalog


def test_catalog_loads_taxonomy_and_searches_variations():
    catalog = OpeningCatalog.load("data/openings/opening_taxonomy.json")
    results = catalog.search("Jobava London")
    assert results
    assert any(item.system_name == "London System" for item in results)


def test_catalog_returns_system_and_variations():
    catalog = OpeningCatalog.from_dict({
        "schema_version": "1.0.0",
        "families": [{
            "id": "open",
            "name": "Open Games",
            "side": "white",
            "systems": [{
                "id": "test-opening",
                "name": "Test Opening",
                "variations": ["Main Line", "Quiet Line"],
            }],
        }],
    })
    entries = catalog.get_system("test-opening")
    assert [entry.variation_name for entry in entries] == [None, "Main Line", "Quiet Line"]


def test_catalog_rejects_duplicate_system_ids():
    payload = {
        "schema_version": "1.0.0",
        "families": [
            {"id": "a", "name": "A", "side": "white", "systems": [
                {"id": "same", "name": "One"}
            ]},
            {"id": "b", "name": "B", "side": "black", "systems": [
                {"id": "same", "name": "Two"}
            ]},
        ],
    }
    with pytest.raises(ValueError, match="Duplicate"):
        OpeningCatalog.from_dict(payload)


def test_catalog_rejects_invalid_side():
    with pytest.raises(ValueError, match="side"):
        OpeningCatalog.from_dict({
            "schema_version": "1.0.0",
            "families": [{"id": "a", "name": "A", "side": "invalid", "systems": []}],
        })
