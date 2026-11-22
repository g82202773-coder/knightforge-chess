"""Atomic JSON persistence for validated KnightForge opening trees.

This repository is a single-process, single-writer local store. A future
multi-worker service should replace it with a transactional database adapter.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .opening_tree import OpeningTree

REPOSITORY_SCHEMA_VERSION = 1


class OpeningRepository:
    """Persist validated opening trees in a versioned JSON document."""

    def __init__(self, path: str | Path, openings: tuple[OpeningTree, ...] = ()) -> None:
        self.path = Path(path)
        self._openings: dict[str, OpeningTree] = {}
        for opening in openings:
            opening.validate()
            if opening.opening_id in self._openings:
                raise ValueError(f"Duplicate opening_id: {opening.opening_id}")
            self._openings[opening.opening_id] = opening

    @classmethod
    def load(cls, path: str | Path) -> OpeningRepository:
        """Load and validate a repository; a missing file means an empty store."""
        source = Path(path)
        if not source.exists():
            return cls(source)
        try:
            payload: Any = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot load opening repository: {exc}") from exc
        if not isinstance(payload, dict):
            raise TypeError("Opening repository root must be an object.")
        if payload.get("schema_version") != REPOSITORY_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported opening repository schema_version: "
                f"{payload.get('schema_version')!r}"
            )
        records = payload.get("openings")
        if not isinstance(records, list):
            raise TypeError("Opening repository openings must be an array.")
        openings = tuple(OpeningTree.from_dict(item) for item in records)
        return cls(source, openings)

    def all(self) -> tuple[OpeningTree, ...]:
        """Return stored openings in insertion order."""
        return tuple(self._openings.values())

    def get(self, opening_id: str) -> OpeningTree | None:
        """Return one opening by stable ID, or None when it is absent."""
        return self._openings.get(opening_id)

    def search(self, query: str, limit: int = 25) -> tuple[OpeningTree, ...]:
        """Search IDs, names, ECO codes, and aliases case-insensitively."""
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        term = query.strip().casefold()
        if not term:
            return self.all()[:limit]
        matches = (
            opening
            for opening in self._openings.values()
            if any(
                term in value.casefold()
                for value in (
                    opening.opening_id,
                    opening.name,
                    opening.eco or "",
                    *opening.aliases,
                )
            )
        )
        return tuple(list(matches)[:limit])

    def add(self, opening: OpeningTree) -> None:
        """Validate and insert a new opening; duplicate IDs are rejected."""
        opening.validate()
        if opening.opening_id in self._openings:
            raise ValueError(f"Opening already exists: {opening.opening_id}")
        self._openings[opening.opening_id] = opening
        self.save()

    def add_many(self, openings: tuple[OpeningTree, ...]) -> None:
        """Validate and persist a batch as one repository update.

        The batch is rejected before mutation if it contains invalid records
        or IDs that already exist in the repository.
        """
        staged: dict[str, OpeningTree] = {}
        for opening in openings:
            opening.validate()
            if opening.opening_id in self._openings or opening.opening_id in staged:
                raise ValueError(f"Opening already exists: {opening.opening_id}")
            staged[opening.opening_id] = opening
        if not staged:
            return
        self._openings.update(staged)
        try:
            self.save()
        except Exception:
            for opening_id in staged:
                del self._openings[opening_id]
            raise

    def upsert(self, opening: OpeningTree) -> None:
        """Validate and insert or replace an opening by stable ID."""
        opening.validate()
        self._openings[opening.opening_id] = opening
        self.save()

    def remove(self, opening_id: str) -> bool:
        """Remove an opening and persist; return False when the ID is absent."""
        if opening_id not in self._openings:
            return False
        del self._openings[opening_id]
        self.save()
        return True

    def save(self) -> None:
        """Atomically replace the JSON file after serializing validated records."""
        for opening in self._openings.values():
            opening.validate()
        payload = {
            "schema_version": REPOSITORY_SCHEMA_VERSION,
            "openings": [opening.to_dict() for opening in self._openings.values()],
        }
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                temporary_file.write(serialized)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass
