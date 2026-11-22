import pytest

from knightforge_engine.opening_tree import OpeningTree, VariationNode


def test_opening_tree_validates_multiple_branches_and_returns_mainline():
    tree = OpeningTree(
        opening_id="ruy-lopez",
        name="Ruy Lopez",
        side="white",
        roots=(
            VariationNode("e2e4", children=(
                VariationNode("e7e5", children=(
                    VariationNode("g1f3", children=(
                        VariationNode("b8c6", children=(
                            VariationNode("f1b5"),
                            VariationNode("f1c4"),
                        )),
                    )),
                )),
            )),
            VariationNode("d2d4"),
        ),
    )

    tree.validate()

    assert tree.mainline_uci() == ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5")
    assert tree.mainline_san() == ("e4", "e5", "Nf3", "Nc6", "Bb5")
    assert tree.branch_count() == 7


def test_opening_tree_rejects_illegal_branch():
    tree = OpeningTree(
        opening_id="bad",
        name="Bad line",
        side="white",
        roots=(VariationNode("e2e5"),),
    )
    with pytest.raises(ValueError, match="Illegal move"):
        tree.validate()


def test_opening_tree_rejects_duplicate_sibling_moves():
    tree = OpeningTree(
        opening_id="duplicate",
        name="Duplicate",
        side="white",
        roots=(VariationNode("e2e4"), VariationNode("e2e4")),
    )
    with pytest.raises(ValueError, match="Duplicate sibling"):
        tree.validate()


def test_reviewed_opening_requires_provenance_and_lines():
    tree = OpeningTree(
        opening_id="missing-source",
        name="Missing source",
        side="white",
        review_status="reviewed",
        roots=(VariationNode("e2e4"),),
    )
    with pytest.raises(ValueError, match="source and license"):
        tree.validate()


def test_mainline_san_respects_custom_starting_position():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    tree = OpeningTree(
        opening_id="custom",
        name="Custom start",
        side="both",
        starting_fen=fen,
        roots=(VariationNode("e2e4"),),
    )
    tree.validate()
    assert tree.mainline_san() == ("e4",)
