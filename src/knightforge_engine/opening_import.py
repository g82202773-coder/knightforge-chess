"""Validated, provenance-aware ingestion for opening records.

Input files use a versioned JSON envelope:
{"schema_version": 1, "openings": [<OpeningTree JSON>, ...]}
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .opening_repository import OpeningRepository
from .opening_tree import OpeningTree

IMPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class OpeningImportReport:
    """Summary of a successfully committed opening import batch."""

    imported_ids: tuple[str, ...]
    skipped_ids: tuple[str, ...] = ()


def parse_opening_import(payload: Mapping[str, Any]) -> tuple[OpeningTree, ...]:
    """Parse a JSON-compatible import envelope and validate every record.

    Every imported record must identify its source and license, including
    drafts. This records provenance; it does not independently verify that
    the stated license grants permission to redistribute the source material.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("Opening import root must be an object.")
    if payload.get("schema_version") != IMPORT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported opening import schema_version: {payload.get('schema_version')!r}"
        )
    records = payload.get("openings")
    if not isinstance(records, list):
        raise TypeError("Opening import openings must be an array.")

    openings: list[OpeningTree] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        try:
            opening = OpeningTree.from_dict(record)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid opening record at index {index}: {exc}") from exc
        if not opening.source_name.strip():
            raise ValueError(f"Opening {opening.opening_id!r} is missing source_name.")
        if not opening.license_name.strip():
            raise ValueError(f"Opening {opening.opening_id!r} is missing license_name.")
        if not opening.roots:
            raise ValueError(f"Opening {opening.opening_id!r} has no move branches.")
        if opening.opening_id in seen_ids:
            raise ValueError(f"Duplicate opening_id in import batch: {opening.opening_id}")
        seen_ids.add(opening.opening_id)
        openings.append(opening)
    return tuple(openings)


def import_openings(
    payload: Mapping[str, Any], repository: OpeningRepository
) -> OpeningImportReport:
    """Validate a complete batch, then add it to the repository in one save.

    Existing IDs are rejected rather than silently overwritten. Callers must
    explicitly resolve conflicts before importing an updated source record.
    """
    openings = parse_opening_import(payload)
    repository.add_many(openings)
    return OpeningImportReport(tuple(opening.opening_id for opening in openings))
