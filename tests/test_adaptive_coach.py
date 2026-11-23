"""Tests for adaptive opening-coach orchestration."""
import chess

from knightforge_engine import (
    AdaptiveOpeningCoach,
    GuidedLesson,
    LessonNode,
    OpeningRepository,
    OpeningTree,
    VariationNode,
)
from knightforge_engine.analysis import AnalysisResult, EngineLine


def reviewed_repository(tmp_path):
    tree = OpeningTree(
        opening_id="open-game",
        name="Open Game",
        side="both",
        source_name="Curated test source",
        license_name="CC0",
        review_status="reviewed",
        anchor_uci=("e2e4", "e7e5"),
        roots=(VariationNode(
            "e2e4",
            children=(VariationNode(
                "e7e5",
                label="Open Game",
                children=(VariationNode(
                    "g1f3", label="King's Knight Opening"
                ),),
            ),),
        ),),
    )
    repository = OpeningRepository.load(tmp_path / "openings.json")
    repository.add(tree)
    return repository


def lesson():
    return GuidedLesson(
        "open-game-coach",
        "Open Game Coach",
        "white",
        (LessonNode(
            "e2e4",
            "Occupy the centre.",
            children=(LessonNode(
                "e7e5",
                "Black mirrors the central pawn move.",
                children=(LessonNode(
                    "g1f3", "Develop the knight toward the centre."
                ),),
            ),),
        ),),
    )


def test_coach_connects_lesson_to_reviewed_opening_and_variation(tmp_path):
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path))
    initial = coach.prompt()
    assert initial.prompt.expected_uci == "e2e4"
    assert initial.knowledge_status == "no_reviewed_match"

    coach.submit_uci("e2e4")
    after_black = coach.submit_uci("e7e5").state
    assert after_black.knowledge_status == "reviewed_opening_anchor_only"
    assert after_black.recognition.matches[0].name == "Open Game"

    after_knight = coach.submit_uci("g1f3").state
    assert after_knight.knowledge_status == "reviewed_variation_match"
    assert after_knight.variation_match.matches[0].matched_line_san == (
        "e4", "e5", "Nf3"
    )
    assert after_knight.prompt.expected_uci is None


def test_coach_reports_unreviewed_deviation_without_inventing_theory(tmp_path):
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path))
    coach.submit_uci("e2e4")
    deviation = coach.submit_uci("d7d5").state
    assert deviation.prompt.kind == "opponent_deviation"
    assert deviation.knowledge_status == "no_reviewed_match"
    assert not deviation.variation_match.matches


def test_coach_undo_refreshes_position_knowledge(tmp_path):
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path))
    coach.submit_uci("e2e4")
    coach.submit_uci("e7e5")
    undone = coach.undo()
    board_after_e4 = chess.Board()
    board_after_e4.push_uci("e2e4")
    assert undone.fen == board_after_e4.fen()
    assert undone.prompt.expected_uci == "e7e5"


class FakeAnalyzer:
    def __init__(self):
        self.calls = []

    def analyse(self, fen, *, time_limit=1.0, depth=None, multipv=3):
        board = chess.Board(fen)
        preferred = {
            chess.STARTING_FEN: "g1f3",
        }.get(fen)
        if preferred is None:
            preferred = "e7e5" if board.turn == chess.BLACK and board.piece_at(chess.E7) else next(
                move.uci() for move in board.legal_moves
            )
        move = chess.Move.from_uci(preferred)
        if move not in board.legal_moves:
            move = next(iter(board.legal_moves))
        self.calls.append((fen, time_limit, depth, multipv))
        san = board.san(move)
        return AnalysisResult(
            engine_name="Fake Stockfish",
            engine_version="test",
            fen=fen,
            depth=depth or 8,
            nodes=100,
            lines=(EngineLine(
                multipv=1,
                depth=depth or 8,
                score_cp=25,
                score_mate=None,
                moves_uci=(move.uci(),),
                moves_san=(san,),
            ),),
        )


def test_stockfish_analysis_is_only_available_after_opponent_deviation(tmp_path):
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path))
    try:
        coach.analyze_deviation()
    except RuntimeError as exc:
        assert "only available after" in str(exc)
    else:
        raise AssertionError("analysis should not run during a normal lesson")


def test_stockfish_deviation_analysis_is_bounded_and_not_book_theory(tmp_path):
    analyzer = FakeAnalyzer()
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path), analyzer=analyzer)
    coach.submit_uci("e2e4")
    deviation = coach.submit_uci("d7d5").state
    assert deviation.prompt.kind == "opponent_deviation"

    result = coach.analyze_deviation(time_limit=0.5, depth=12, multipv=2)
    assert result.engine_name == "Fake Stockfish"
    assert len(result.lines[0].moves_san) == 1
    assert analyzer.calls[-1] == (deviation.fen, 0.5, 12, 2)
    assert deviation.knowledge_status == "no_reviewed_match"


def test_stockfish_analysis_requires_configured_analyzer_after_deviation(tmp_path):
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path))
    coach.submit_uci("e2e4")
    coach.submit_uci("d7d5")
    try:
        coach.analyze_deviation()
    except RuntimeError as exc:
        assert "No Stockfish analyzer configured" in str(exc)
    else:
        raise AssertionError("missing analyzer should be reported")


def test_engine_decision_is_attached_automatically_and_move_is_compared(tmp_path):
    analyzer = FakeAnalyzer()
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path), analyzer=analyzer)

    initial = coach.state
    assert initial.recommendation is not None
    assert initial.recommendation.uci == "g1f3"
    assert initial.active_hint is not None
    assert initial.active_hint.level == 1

    submitted = coach.submit_uci("e2e4")
    assert submitted.state.move_comparison is not None
    assert submitted.state.move_comparison.played_uci == "e2e4"
    assert submitted.state.move_comparison.matched_candidate_rank is None
    # The new side-to-move position is already analysed before submit_uci returns.
    assert submitted.state.recommendation is not None
    assert submitted.state.recommendation.uci == "e7e5"
    assert submitted.state.active_hint.level == 1


def test_progressive_hint_reveal_updates_arrow_without_reanalysing(tmp_path):
    analyzer = FakeAnalyzer()
    coach = AdaptiveOpeningCoach(lesson(), reviewed_repository(tmp_path), analyzer=analyzer)
    calls_before = len(analyzer.calls)

    source_hint = coach.reveal_hint(2)
    assert source_hint.active_hint.level == 2
    assert source_hint.active_hint.arrow_from == "g1"
    assert source_hint.active_hint.arrow_to is None

    arrow_hint = coach.reveal_hint(3)
    assert (arrow_hint.active_hint.arrow_from, arrow_hint.active_hint.arrow_to) == (
        "g1", "f3"
    )
    assert arrow_hint.recommendation_arrow == ("g1", "f3")
    assert len(analyzer.calls) == calls_before


def test_wrong_lesson_move_keeps_position_decision_and_returns_comparison(tmp_path):
    coach = AdaptiveOpeningCoach(
        lesson(), reviewed_repository(tmp_path), analyzer=FakeAnalyzer()
    )
    result = coach.submit_uci("d2d4")
    assert not result.submission.applied
    assert result.state.fen == chess.STARTING_FEN
    assert result.state.move_comparison is not None
    assert result.state.recommendation.uci == "g1f3"
