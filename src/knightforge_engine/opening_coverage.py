"""Measure validated opening-tree coverage against the opening taxonomy."""

from __future__ import annotations

from dataclasses import dataclass

from .opening_catalog import OpeningCatalog
from .opening_repository import OpeningRepository
from .opening_tree import OpeningTree, VariationNode


@dataclass(frozen=True, slots=True)
class OpeningCoverageReport:
    """Deterministic coverage metrics; taxonomy names are not treated as move data."""

    taxonomy_system_count: int
    taxonomy_variation_count: int
    stored_tree_count: int
    matched_system_ids: tuple[str, ...]
    missing_system_ids: tuple[str, ...]
    matched_variations: tuple[str, ...]
    missing_variations: tuple[str, ...]
    trees_without_eco: tuple[str, ...]
    trees_without_source: tuple[str, ...]
    trees_without_license: tuple[str, ...]
    trees_without_moves: tuple[str, ...]
    draft_tree_ids: tuple[str, ...]
    reviewed_tree_ids: tuple[str, ...]
    total_move_nodes: int
    total_transposition_positions: int

    @property
    def system_coverage_ratio(self) -> float:
        if not self.taxonomy_system_count:
            return 1.0
        return len(self.matched_system_ids) / self.taxonomy_system_count

    @property
    def variation_coverage_ratio(self) -> float:
        if not self.taxonomy_variation_count:
            return 1.0
        return len(self.matched_variations) / self.taxonomy_variation_count

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable report without hiding missing coverage."""
        return {
            "taxonomy_system_count": self.taxonomy_system_count,
            "taxonomy_variation_count": self.taxonomy_variation_count,
            "stored_tree_count": self.stored_tree_count,
            "matched_system_ids": list(self.matched_system_ids),
            "missing_system_ids": list(self.missing_system_ids),
            "matched_variations": list(self.matched_variations),
            "missing_variations": list(self.missing_variations),
            "trees_without_eco": list(self.trees_without_eco),
            "trees_without_source": list(self.trees_without_source),
            "trees_without_license": list(self.trees_without_license),
            "trees_without_moves": list(self.trees_without_moves),
            "draft_tree_ids": list(self.draft_tree_ids),
            "reviewed_tree_ids": list(self.reviewed_tree_ids),
            "total_move_nodes": self.total_move_nodes,
            "total_transposition_positions": self.total_transposition_positions,
            "system_coverage_ratio": self.system_coverage_ratio,
            "variation_coverage_ratio": self.variation_coverage_ratio,
        }


def _labels(nodes: tuple[VariationNode, ...]) -> set[str]:
    found: set[str] = set()
    for node in nodes:
        if node.label.strip():
            found.add(node.label.strip().casefold())
        found.update(_labels(node.children))
    return found


def _count_transpositions(tree: OpeningTree) -> int:
    return len(tree.transpositions())


def analyze_opening_coverage(
    catalog: OpeningCatalog, repository: OpeningRepository
) -> OpeningCoverageReport:
    """Compare stored trees and their labelled branches with taxonomy entries.

    A system is matched only by its stable taxonomy system ID. A variation is
    matched only when a move-tree node carries the exact taxonomy variation
    label. This intentionally avoids claiming coverage from similar names,
    aliases, or taxonomy labels that have no validated moves.
    """
    references = catalog.all()
    systems: dict[str, str] = {}
    variations: dict[str, set[str]] = {}
    for reference in references:
        systems[reference.system_id] = reference.system_name
        if reference.variation_name:
            variations.setdefault(reference.system_id, set()).add(
                reference.variation_name.casefold()
            )

    trees = repository.all()
    by_id = {tree.opening_id: tree for tree in trees}
    matched_system_ids = tuple(sorted(set(systems) & set(by_id)))
    missing_system_ids = tuple(sorted(set(systems) - set(by_id)))

    matched_variations: list[str] = []
    missing_variations: list[str] = []
    for system_id in sorted(variations):
        tree = by_id.get(system_id)
        labels = _labels(tree.roots) if tree is not None else set()
        for variation in sorted(variations[system_id]):
            qualified = f"{system_id}:{variation}"
            (matched_variations if variation in labels else missing_variations).append(
                qualified
            )

    return OpeningCoverageReport(
        taxonomy_system_count=len(systems),
        taxonomy_variation_count=sum(len(items) for items in variations.values()),
        stored_tree_count=len(trees),
        matched_system_ids=matched_system_ids,
        missing_system_ids=missing_system_ids,
        matched_variations=tuple(matched_variations),
        missing_variations=tuple(missing_variations),
        trees_without_eco=tuple(sorted(t.opening_id for t in trees if not t.eco)),
        trees_without_source=tuple(sorted(t.opening_id for t in trees if not t.source_name.strip())),
        trees_without_license=tuple(sorted(t.opening_id for t in trees if not t.license_name.strip())),
        trees_without_moves=tuple(sorted(t.opening_id for t in trees if not t.roots)),
        draft_tree_ids=tuple(sorted(t.opening_id for t in trees if t.review_status == "draft")),
        reviewed_tree_ids=tuple(sorted(
            t.opening_id for t in trees if t.review_status in {"reviewed", "published"}
        )),
        total_move_nodes=sum(t.branch_count() for t in trees),
        total_transposition_positions=sum(_count_transpositions(t) for t in trees),
    )
