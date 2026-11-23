import chess

from knightforge_engine.opening_recognition import OpeningRecognizer
from knightforge_engine.opening_repository import OpeningRepository
from knightforge_engine.opening_tree import OpeningTree, VariationNode
from knightforge_engine.variation_matching import PositionBasedVariationMatcher


def _repository(tmp_path):
    opening = OpeningTree(
        opening_id="sicilian-najdorf",
        name="Sicilian Defence: Najdorf Variation",
        side="black",
        eco="B90",
        source_name="Curated test source",
        source_url="https://example.org/openings",
        license_name="CC BY 4.0",
        review_status="reviewed",
        roots=(VariationNode("e2e4", children=(
            VariationNode("c7c5", children=(
                VariationNode("g1f3", children=(
                    VariationNode("d7d6", children=(
                        VariationNode("d2d4", label="Open Sicilian", children=(
                            VariationNode("c5d4", label="Open Sicilian: Main Capture"),
                        )),
                        VariationNode("b1c3", label="Closed Sicilian"),
                    )),
                )),
            )),
        )),),
        anchor_uci=("e2e4", "c7c5", "g1f3", "d7d6"),
    )
    repository = OpeningRepository(tmp_path / "openings.json")
    repository.add(opening)
    return repository


def test_matches_named_variation_beyond_opening_anchor(tmp_path):
    repository = _repository(tmp_path)
    recognition = OpeningRecognizer(repository).recognize("1. e4 c5 2. Nf3 d6 3. d4")
    result = PositionBasedVariationMatcher(repository).match(recognition)

    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.opening_id == "sicilian-najdorf"
    assert match.matched_ply == 5
    assert match.matched_line_san == ("e4", "c5", "Nf3", "d6", "d4")
    assert match.variation_labels == ("Open Sicilian",)
    assert match.matched_via_transposition is False


def test_matches_deeper_subvariation_node(tmp_path):
    repository = _repository(tmp_path)
    recognition = OpeningRecognizer(repository).recognize(
        "1. e4 c5 2. Nf3 d6 3. d4 cxd4"
    )
    result = PositionBasedVariationMatcher(repository).match(recognition)

    assert result.matches[0].matched_ply == 6
    assert result.matches[0].variation_labels == (
        "Open Sicilian",
        "Open Sicilian: Main Capture",
    )


def test_reports_transposed_variation_path(tmp_path):
    repository = _repository(tmp_path)
    recognition = OpeningRecognizer(repository).recognize(
        "1. Nf3 c5 2. e4 d6 3. d4"
    )
    result = PositionBasedVariationMatcher(repository).match(recognition)

    assert result.matches[0].matched_ply == 5
    assert result.matches[0].matched_via_transposition is True
    assert result.matches[0].variation_labels == ("Open Sicilian",)


def test_fen_matches_variation_without_claiming_move_order(tmp_path):
    repository = _repository(tmp_path)
    board = chess.Board()
    for uci in ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4"):
        board.push_uci(uci)
    recognition = OpeningRecognizer(repository).recognize(fen=board.fen())
    result = PositionBasedVariationMatcher(repository).match(recognition)

    assert result.matches[0].variation_labels == ("Open Sicilian",)
    assert result.matches[0].matched_via_transposition is None
    assert result.input_kind == "fen"


def test_does_not_match_unreviewed_tree(tmp_path):
    repository = OpeningRepository(tmp_path / "draft.json")
    repository.add(OpeningTree(
        opening_id="draft",
        name="Draft",
        side="white",
        roots=(VariationNode("e2e4"),),
        anchor_uci=("e2e4",),
    ))
    recognition = OpeningRecognizer(repository).recognize("1. e4")
    result = PositionBasedVariationMatcher(repository).match(recognition)
    assert result.matches == ()
