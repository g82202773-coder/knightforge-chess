from __future__ import annotations

import chess

from knightforge_engine.opening_courses import london_jobava_courses


def _walk(board: chess.Board, nodes) -> int:
    count = 0
    for node in nodes:
        move = chess.Move.from_uci(node.move_uci)
        assert move in board.legal_moves, f"illegal move {node.move_uci} in {board.fen()}"
        child = board.copy()
        child.push(move)
        count += 1 + _walk(child, node.children)
    return count


def test_london_and_jobava_courses_are_legal_and_have_named_variations() -> None:
    london, jobava = london_jobava_courses()

    assert london.opening_id == "london-system"
    assert jobava.opening_id == "jobava-london"
    assert london.side == jobava.side == "white"

    for course in (london, jobava):
        course.validate()
        assert _walk(chess.Board(course.starting_fen), course.roots) == course.branch_count()
        assert course.branch_count() >= 15
        assert course.mainline_san()

    assert any("Classical" in node.label for node in _all_nodes(london.roots))
    assert any("Jobava" in node.label for node in _all_nodes(jobava.roots))


def _all_nodes(nodes):
    for node in nodes:
        yield node
        yield from _all_nodes(node.children)
