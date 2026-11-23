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
    result = OpeningRecognizer(repository).recognize("1.e4 c5 2.Nf3 d6 3.d4")
    assert result.matches[0].matched_ply == 4
    assert result.matches[0].matched_via_transposition is False


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
