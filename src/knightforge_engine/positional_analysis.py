"""Explainable positional feature analysis for KnightForge.

Scores are teaching heuristics, not chess-engine evaluations. Stockfish remains
the independent verification layer planned for a later increment.
"""
from __future__ import annotations

from collections import Counter

import chess

PIECE_VALUES = {
    chess.PAWN: 1.0, chess.KNIGHT: 3.2, chess.BISHOP: 3.3,
    chess.ROOK: 5.0, chess.QUEEN: 9.0, chess.KING: 0.0,
}


def _pawn_attacks(board: chess.Board, color: chess.Color, square: chess.Square) -> bool:
    return any(
        board.piece_at(origin) == chess.Piece(chess.PAWN, color)
        and square in board.attacks(origin)
        for origin in board.pieces(chess.PAWN, color)
    )


def _pawn_report(board: chess.Board, color: chess.Color) -> dict:
    pawns = sorted(board.pieces(chess.PAWN, color), key=lambda sq: (chess.square_file(sq), chess.square_rank(sq)))
    files = Counter(chess.square_file(sq) for sq in pawns)
    doubled = [chess.square_name(sq) for sq in pawns if files[chess.square_file(sq)] > 1]
    isolated = []
    backward = []
    passed = []
    enemy_pawns = board.pieces(chess.PAWN, not color)
    for square in pawns:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        adjacent_friendly = any(abs(chess.square_file(other) - file_) == 1 for other in pawns)
        if not adjacent_friendly:
            isolated.append(chess.square_name(square))
        enemy_ahead = [
            other for other in enemy_pawns
            if abs(chess.square_file(other) - file_) <= 1
            and ((chess.square_rank(other) > rank) if color else (chess.square_rank(other) < rank))
        ]
        if not enemy_ahead:
            passed.append(chess.square_name(square))
        elif adjacent_friendly:
            next_rank = rank + (1 if color else -1)
            if 0 <= next_rank <= 7:
                forward = chess.square(file_, next_rank)
                enemy_pawn_controls = _pawn_attacks(board, not color, forward)
                friendly_support = any(
                    abs(chess.square_file(other) - file_) == 1
                    and ((chess.square_rank(other) < rank) if color else (chess.square_rank(other) > rank))
                    for other in pawns
                )
                if enemy_pawn_controls and not friendly_support:
                    backward.append(chess.square_name(square))
    return {
        "isolated": isolated,
        "doubled": doubled,
        "backward_candidates": backward,
        "passed": passed,
        "counts": {
            "isolated": len(isolated), "doubled": len(doubled),
            "backward_candidates": len(backward), "passed": len(passed),
        },
        "method_note": "Backward-pawn flags are heuristic candidates and need human review.",
    }


def _weak_squares(board: chess.Board, color: chess.Color) -> list[str]:
    """Central squares in enemy territory that enemy pawns cannot challenge."""
    enemy_half = range(4, 8) if color else range(0, 4)
    return [
        chess.square_name(square) for square in chess.SQUARES
        if chess.square_rank(square) in enemy_half
        and chess.square_file(square) in {2, 3, 4, 5}
        and board.piece_at(square) is None
        and not _pawn_attacks(board, not color, square)
    ]


def _outposts(board: chess.Board, color: chess.Color) -> list[str]:
    result = []
    enemy_half = range(4, 8) if color else range(0, 4)
    for square in chess.SQUARES:
        if chess.square_rank(square) not in enemy_half:
            continue
        if board.piece_at(square) is not None or _pawn_attacks(board, not color, square):
            continue
        if _pawn_attacks(board, color, square):
            result.append(chess.square_name(square))
    return result


def _rook_report(board: chess.Board, color: chess.Color) -> dict:
    open_files = []
    half_open_files = []
    active_rooks = []
    for file_ in range(8):
        white_pawns = any(chess.square_file(sq) == file_ for sq in board.pieces(chess.PAWN, chess.WHITE))
        black_pawns = any(chess.square_file(sq) == file_ for sq in board.pieces(chess.PAWN, chess.BLACK))
        if not white_pawns and not black_pawns:
            open_files.append(chess.FILE_NAMES[file_])
        elif not (white_pawns if color else black_pawns):
            half_open_files.append(chess.FILE_NAMES[file_])
    for square in board.pieces(chess.ROOK, color):
        file_ = chess.square_file(square)
        if chess.FILE_NAMES[file_] in open_files or chess.FILE_NAMES[file_] in half_open_files:
            active_rooks.append(chess.square_name(square))
    seventh = 6 if color else 1
    seventh_rank_rooks = [
        chess.square_name(sq) for sq in board.pieces(chess.ROOK, color)
        if chess.square_rank(sq) == seventh
    ]
    return {
        "open_files": open_files,
        "half_open_files": half_open_files,
        "rooks_on_open_or_half_open_files": active_rooks,
        "rooks_on_seventh_rank": seventh_rank_rooks,
    }


def _features(board: chess.Board) -> dict:
    return {
        "white_pawns": _pawn_report(board, chess.WHITE),
        "black_pawns": _pawn_report(board, chess.BLACK),
        "white_weak_squares": _weak_squares(board, chess.WHITE),
        "black_weak_squares": _weak_squares(board, chess.BLACK),
        "white_outpost_squares": _outposts(board, chess.WHITE),
        "black_outpost_squares": _outposts(board, chess.BLACK),
        "white_rooks": _rook_report(board, chess.WHITE),
        "black_rooks": _rook_report(board, chess.BLACK),
    }


def _material_balance(board: chess.Board) -> float:
    score = 0.0
    for piece_type, value in PIECE_VALUES.items():
        score += value * (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK)))
    return score


def _heuristic_score(board: chess.Board) -> float:
    """White-centric explainable positional heuristic, deliberately not centipawns."""
    score = _material_balance(board)
    features = _features(board)
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        own = features["white_pawns" if color else "black_pawns"]
        rooks = features["white_rooks" if color else "black_rooks"]
        outposts = features["white_outpost_squares" if color else "black_outpost_squares"]
        score += sign * (
            0.12 * len(rooks["rooks_on_open_or_half_open_files"])
            + 0.08 * len(rooks["rooks_on_seventh_rank"])
            + 0.10 * len(outposts)
            + 0.08 * own["counts"]["passed"]
            - 0.10 * own["counts"]["isolated"]
            - 0.08 * own["counts"]["doubled"]
            - 0.08 * own["counts"]["backward_candidates"]
        )
    return round(score, 2)


def _reply_priority(board: chess.Board, move: chess.Move) -> tuple[float, int, int]:
    captured = board.piece_at(move.to_square)
    capture_value = PIECE_VALUES.get(captured.piece_type, 0.0) if captured else 0.0
    gives_check = board.gives_check(move)
    return (capture_value + (0.6 if gives_check else 0.0), int(gives_check), -move.to_square)


def _best_practical_reply(board: chess.Board) -> dict | None:
    legal = list(board.legal_moves)
    if not legal:
        return None
    # Tactical forcing factors only: this is a practical-reply heuristic, not a search.
    move = max(legal, key=lambda candidate: _reply_priority(board, candidate))
    san = board.san(move)
    captured = board.piece_at(move.to_square)
    board.push(move)
    reply = {
        "uci": move.uci(),
        "san": san,
        "is_check": board.is_check(),
        "captured_piece": chess.piece_name(captured.piece_type) if captured else None,
        "selection_basis": "Highest immediate capture/check priority among legal replies; not a minimax or engine result.",
    }
    board.pop()
    return reply


def analyze_position(fen: str, candidate_uci: list[str] | None = None) -> dict:
    """Analyze pawn structure, outposts, rook files and legal candidate moves."""
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ValueError("Invalid FEN position.") from exc
    if not board.is_valid():
        raise ValueError("FEN describes an invalid chess position.")
    before = _features(board)
    candidate_moves = list(board.legal_moves)[:12] if candidate_uci is None else [
        chess.Move.from_uci(uci) for uci in candidate_uci
    ]
    if not candidate_moves:
        raise ValueError("Provide at least one legal candidate move.")
    if len(candidate_moves) > 12:
        raise ValueError("Analyze at most 12 candidate moves at a time.")
    results = []
    seen = set()
    for move in candidate_moves:
        if move in seen:
            continue
        seen.add(move)
        if move not in board.legal_moves:
            raise ValueError(f"Candidate move is illegal: {move.uci()}")
        san = board.san(move)
        after = board.copy(stack=False)
        after.push(move)
        score = _heuristic_score(after)
        reply = _best_practical_reply(after) if not after.is_game_over() else None
        results.append({
            "uci": move.uci(),
            "san": san,
            "heuristic_score_white": score,
            "score_change_white": round(score - _heuristic_score(board), 2),
            "features_after": _features(after),
            "opponent_practical_reply": reply,
        })
    results.sort(key=lambda item: item["heuristic_score_white"], reverse=board.turn == chess.WHITE)
    return {
        "fen": board.fen(),
        "side_to_move": "white" if board.turn else "black",
        "position_features": before,
        "candidates": results,
        "methodology": {
            "name": "KnightForge explainable positional heuristic",
            "score_unit": "heuristic points, not centipawns",
            "limitations": [
                "Feature weights are teaching heuristics, not calibrated chess-engine values.",
                "Backward-pawn identification is approximate.",
                "Opponent reply selection prioritizes immediate captures and checks; it is not a full search.",
                "Use Stockfish for independent tactical and evaluation verification when integrated.",
            ],
        },
    }
