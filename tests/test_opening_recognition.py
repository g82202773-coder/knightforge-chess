import chess
import pytest

from knightforge_engine.opening_recognition import OpeningRecognizer
from knightforge_engine.opening_repository import OpeningRepository
from knightforge_engine.opening_tree import OpeningTree, VariationNode


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
                        VariationNode("d2d4", label="Open Sicilian"),
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


def test_recognizes_san_sequence_and_returns_converted_moves(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize(
        "1.e4 c5 2.Nf3 d6"
    )

    assert result.moves_san == ("e4", "c5", "Nf3", "d6")
    assert result.ply == 4
    assert result.matches[0].opening_id == "sicilian-najdorf"
    assert result.matches[0].matched_via_transposition is False
    assert result.matches[0].source_name == "Curated test source"


def test_recognizes_uci_sequence(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize(
        ["e2e4", "c7c5", "g1f3", "d7d6"], notation="uci"
    )
    assert result.matches[0].name == "Sicilian Defence: Najdorf Variation"


def test_recognizes_pgn_mainline(tmp_path):
    pgn = """[Event "Test"]
[Result "*"]

1. e4 c5 2. Nf3 d6 *
"""
    result = OpeningRecognizer(_repository(tmp_path)).recognize(pgn, notation="pgn")
    assert result.matches[0].opening_id == "sicilian-najdorf"
    assert result.input_kind == "uci"


def test_position_recognition_from_fen_does_not_claim_history(tmp_path):
    repository = _repository(tmp_path)
    board = chess.Board()
    for move in ("e2e4", "c7c5", "g1f3", "d7d6"):
        board.push_uci(move)

    result = OpeningRecognizer(repository).recognize(fen=board.fen())

    assert result.matches[0].opening_id == "sicilian-najdorf"
    assert result.moves_uci == ()
    assert result.input_kind == "fen"


def test_recognizes_transposed_position(tmp_path):
    repository = _repository(tmp_path)
    # The anchor position after 1.e4 c5 2.Nf3 d6 is also reached by this
    # different move order only if the exact board state is the same.
    result = OpeningRecognizer(repository).recognize("1.Nf3 c5 2.e4 d6")
    assert result.matches[0].matched_ply == 4
    assert result.matches[0].matched_via_transposition is True


def test_does_not_recognize_unreviewed_openings(tmp_path):
    repository = OpeningRepository(tmp_path / "openings.json")
    draft = OpeningTree(
        opening_id="draft",
        name="Draft opening",
        side="white",
        roots=(VariationNode("e2e4"),),
        anchor_uci=("e2e4",),
    )
    repository.add(draft)

    result = OpeningRecognizer(repository).recognize("1.e4")
    assert result.matches == ()


def test_rejects_illegal_moves(tmp_path):
    recognizer = OpeningRecognizer(_repository(tmp_path))
    with pytest.raises(ValueError, match="Invalid SAN move"):
        recognizer.recognize("1.e5")


def test_requires_moves_or_fen(tmp_path):
    recognizer = OpeningRecognizer(_repository(tmp_path))
    with pytest.raises(ValueError, match="Provide move history or a FEN"):
        recognizer.recognize()


def test_rejects_both_moves_and_fen(tmp_path):
    recognizer = OpeningRecognizer(_repository(tmp_path))
    with pytest.raises(ValueError, match="not both"):
        recognizer.recognize("1.e4", fen=chess.STARTING_FEN)


def test_accepts_black_move_number_san_tokens(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize(
        ["1. e4", "1... c5", "2. Nf3", "2... d6"]
    )
    assert result.moves_san == ("e4", "c5", "Nf3", "d6")
    assert result.matches[0].opening_id == "sicilian-najdorf"


def test_accepts_san_with_separated_move_numbers(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize(
        "1. e4 c5 2. Nf3 d6"
    )
    assert result.matches[0].opening_id == "sicilian-najdorf"


def test_recognizes_castling_san_and_uci(tmp_path):
    repository = OpeningRepository(tmp_path / "castle.json")
    opening = OpeningTree(
        opening_id="ruy-castle",
        name="Castling test line",
        side="white",
        source_name="Test source",
        license_name="CC BY 4.0",
        review_status="reviewed",
        roots=(VariationNode("e2e4", children=(
            VariationNode("e7e5", children=(
                VariationNode("g1f3", children=(
                    VariationNode("b8c6", children=(
                        VariationNode("f1b5", children=(
                            VariationNode("a7a6", children=(
                                VariationNode("b5a4", children=(
                                    VariationNode("g8f6", children=(
                                        VariationNode("e1g1", label="Castling line"),
                                    )),
                                )),
                            )),
                        )),
                    )),
                )),
            )),
        )),),
        anchor_uci=("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6",
                    "b5a4", "g8f6", "e1g1"),
    )
    repository.add(opening)
    result = OpeningRecognizer(repository).recognize(
        "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O"
    )
    assert result.matches[0].variation_labels == ("Castling line",)


def test_fen_rejects_invalid_position(tmp_path):
    recognizer = OpeningRecognizer(_repository(tmp_path))
    with pytest.raises(ValueError, match="valid chess position"):
        recognizer.recognize(fen="8/8/8/8/8/8/8/8 w - - 0 1")


def test_unknown_valid_position_returns_no_match(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize("1. d4 d5")
    assert result.matches == ()
    assert result.ambiguous is False


def test_reports_ambiguous_shared_anchor(tmp_path):
    repository = _repository(tmp_path)
    original = repository.get("sicilian-najdorf")
    assert original is not None
    duplicate = OpeningTree(
        opening_id="sicilian-shared-anchor",
        name="Shared anchor test",
        side="black",
        source_name="Curated test source",
        license_name="CC BY 4.0",
        review_status="reviewed",
        roots=original.roots,
        anchor_uci=original.anchor_uci,
    )
    repository.add(duplicate)
    result = OpeningRecognizer(repository).recognize("1. e4 c5 2. Nf3 d6")
    assert len(result.matches) == 2
    assert result.ambiguous is True


def test_explicit_headerless_pgn_is_supported(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize(
        "1. e4 c5 2. Nf3 d6", notation="pgn"
    )
    assert result.matches[0].opening_id == "sicilian-najdorf"


def test_auto_detection_keeps_headerless_numbered_san_as_san(tmp_path):
    result = OpeningRecognizer(_repository(tmp_path)).recognize(
        "1. e4 c5 2. Nf3 d6"
    )
    assert result.input_kind == "san"
    assert result.matches[0].opening_id == "sicilian-najdorf"
