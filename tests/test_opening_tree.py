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


def test_opening_tree_round_trip_preserves_metadata_and_branches():
    tree = OpeningTree(
        opening_id="sicilian",
        name="Sicilian Defence",
        side="black",
        eco="B20",
        aliases=("Sicilian",),
        source_name="Test source",
        source_url="https://example.org/chess",
        license_name="CC BY 4.0",
        review_status="reviewed",
        transposition_notes=("Can transpose from another move order.",),
        roots=(VariationNode("e2e4", children=(
            VariationNode("c7c5", label="Open Sicilian"),
            VariationNode("e7e6", label="French Defence"),
        )),),
    )

    restored = OpeningTree.from_dict(tree.to_dict())

    assert restored == tree
    assert restored.mainline_san() == ("e4", "c5")


def test_deserialization_rejects_unknown_schema_version():
    with pytest.raises(ValueError, match="Unsupported"):
        OpeningTree.from_dict({"schema_version": 2})


def test_deserialization_rejects_malformed_node_fields():
    payload = {
        "schema_version": 1,
        "opening_id": "broken",
        "name": "Broken",
        "side": "white",
        "roots": [{"move_uci": "e2e4", "children": "not-an-array"}],
    }
    with pytest.raises(TypeError, match="children"):
        OpeningTree.from_dict(payload)


def test_transposition_index_detects_reached_identical_positions():
    # The two move orders reach the same position after 1.Nf3 d5 2.g3
    # and 1.g3 d5 2.Nf3.
    tree = OpeningTree(
        opening_id="transposition-test",
        name="Transposition test",
        side="both",
        roots=(
            VariationNode("g1f3", children=(
                VariationNode("d7d5", children=(VariationNode("g2g3"),)),
            )),
            VariationNode("g2g3", children=(
                VariationNode("d7d5", children=(VariationNode("g1f3"),)),
            )),
        ),
    )

    matches = tree.transpositions()

    assert matches
    assert any(len(paths) == 2 for paths in matches.values())





def test_position_key_distinguishes_side_to_move():
    white_to_move = chess.Board("8/8/8/8/8/8/4k3/4K3 w - - 0 1")
    black_to_move = chess.Board("8/8/8/8/8/8/4k3/4K3 b - - 0 1")
    assert OpeningTree._position_key(white_to_move) != OpeningTree._position_key(black_to_move)


def test_position_key_distinguishes_castling_rights():
    with_rights = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    without_rights = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
    assert OpeningTree._position_key(with_rights) != OpeningTree._position_key(without_rights)


def test_position_key_keeps_only_legally_relevant_en_passant():
    legal_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    no_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - - 0 1")
    assert OpeningTree._position_key(legal_ep) != OpeningTree._position_key(no_ep)
