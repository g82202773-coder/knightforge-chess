"""Loadable, searchable opening taxonomy with strict structural validation.

The taxonomy is an index of names, not a repertoire database. A named entry
becomes playable study content only after validated move trees are attached.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class OpeningReference:
    """One named opening system or variation in the taxonomy."""

    family_id: str
    family_name: str
    system_id: str
    system_name: str
    side: str
    variation_name: str | None = None

    @property
    def qualified_name(self) -> str:
        if self.variation_name:
            return f"{self.system_name} — {self.variation_name}"
        return self.system_name


class OpeningCatalog:
    """Validated, reusable reader for KnightForge's opening taxonomy JSON."""

    def __init__(self, schema_version: str, references: tuple[OpeningReference, ...]):
        self.schema_version = schema_version
        self._references = references

    @classmethod
    def load(cls, path: str | Path) -> OpeningCatalog:
        """Read and validate a taxonomy file from disk."""
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot load opening taxonomy: {exc}") from exc
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> OpeningCatalog:
        """Validate taxonomy structure and flatten its named entries."""
        if not isinstance(payload, dict):
            raise ValueError("Taxonomy root must be an object.")
        version = payload.get("schema_version")
        families = payload.get("families")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("schema_version is required.")
        if not isinstance(families, list):
            raise ValueError("families must be an array.")

        references: list[OpeningReference] = []
        seen_ids: set[str] = set()
        for family_index, family in enumerate(families):
            if not isinstance(family, dict):
                raise ValueError(f"Family {family_index} must be an object.")
            family_id = cls._required_text(family, "id", f"family {family_index}")
            family_name = cls._required_text(family, "name", family_id)
            side = family.get("side")
            if side not in {"white", "black", "both"}:
                raise ValueError(f"Invalid side for family {family_id}.")
            systems = family.get("systems")
            if not isinstance(systems, list):
                raise ValueError(f"systems must be an array for family {family_id}.")

            for system_index, system in enumerate(systems):
                if not isinstance(system, dict):
                    raise ValueError(f"System {system_index} in {family_id} must be an object.")
                system_id = cls._required_text(system, "id", family_id)
                system_name = cls._required_text(system, "name", system_id)
                if system_id in seen_ids:
                    raise ValueError(f"Duplicate opening system id: {system_id}")
                seen_ids.add(system_id)
                references.append(
                    OpeningReference(family_id, family_name, system_id, system_name, side)
                )
                variations = system.get("variations", [])
                if not isinstance(variations, list) or any(
                    not isinstance(item, str) or not item.strip() for item in variations
                ):
                    raise ValueError(f"variations must be non-empty strings for {system_id}.")
                for variation in variations:
                    references.append(
                        OpeningReference(
                            family_id, family_name, system_id, system_name, side, variation
                        )
                    )
        return cls(version, tuple(references))

    @staticmethod
    def _required_text(item: dict[str, Any], key: str, context: str) -> str:
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} is required for {context}.")
        return value.strip()

    def all(self) -> tuple[OpeningReference, ...]:
        """Return every system and named variation in stable source order."""
        return self._references

    def search(self, query: str, limit: int = 25) -> tuple[OpeningReference, ...]:
        """Case-insensitive substring search across names and family labels."""
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        term = query.strip().casefold()
        if not term:
            return self._references[:limit]
        matches = (
            item
            for item in self._references
            if term in item.qualified_name.casefold()
            or term in item.family_name.casefold()
            or term in item.system_id.casefold()
        )
        return tuple(list(matches)[:limit])

    def get_system(self, system_id: str) -> tuple[OpeningReference, ...]:
        """Return the system plus its variations, or an empty tuple."""
        return tuple(item for item in self._references if item.system_id == system_id)
