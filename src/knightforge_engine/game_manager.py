"""Complete chess gameplay, chess clocks, PGN I/O, and multiplayer match state.

Supports Human vs AI (7 levels), Local 2-Player, and Online Private Multiplayer
with invite codes, time controls (Bullet/Blitz/Rapid/Classical/Custom),
increment/delay, draw offers, claimable threefold/50-move draws, and full PGN.
"""
from __future__ import annotations

import io
import secrets
import time
from dataclasses import dataclass
from typing import Any, Literal

import chess
import chess.pgn

from .ai_opponent import AIDifficulty, ChessAIOpponent
from .opening_recognition import OpeningRecognizer
from .opening_repository import OpeningRepository
from .positional_analysis import analyze_position
from .tactics import TacticalScanner
from .variation_matching import PositionBasedVariationMatcher

MatchMode = Literal["human_vs_ai", "local_pvp", "online_pvp"]
ColorName = Literal["white", "black"]

CLOCK_PRESETS: dict[str, tuple[int, int, int]] = {
    # preset_name: (base_seconds, increment_seconds, delay_seconds)
    "unlimited": (0, 0, 0),
    "bullet_1_0": (60, 0, 0),
    "bullet_2_1": (120, 1, 0),
    "blitz_3_0": (180, 0, 0),
    "blitz_3_2": (180, 2, 0),
    "blitz_5_0": (300, 0, 0),
    "rapid_10_0": (600, 0, 0),
    "rapid_15_10": (900, 10, 0),
    "classical_30_0": (1800, 0, 0),
    "correspondence": (0, 0, 0),
}


@dataclass
class ChessClock:
    """Server-authoritative chess clock with increment, delay, pause, and timeout."""

    base_seconds: float = 0.0
    increment_seconds: float = 0.0
    delay_seconds: float = 0.0
    white_remaining: float = 0.0
    black_remaining: float = 0.0
    active_side: ColorName | None = None
    last_tick: float | None = None
    paused: bool = False

    def __post_init__(self) -> None:
        if self.base_seconds > 0 and self.white_remaining == 0 and self.black_remaining == 0:
            self.white_remaining = float(self.base_seconds)
            self.black_remaining = float(self.base_seconds)

    @property
    def enabled(self) -> bool:
        return self.base_seconds > 0

    def start_turn(self, side: ColorName, now: float | None = None) -> None:
        if not self.enabled:
            return
        self.active_side = side
        self.last_tick = time.monotonic() if now is None else now
        self.paused = False

    def current_times(self, now: float | None = None) -> tuple[float, float]:
        if not self.enabled:
            return (0.0, 0.0)
        w, b = self.white_remaining, self.black_remaining
        if self.active_side and self.last_tick is not None and not self.paused:
            elapsed = max(0.0, (time.monotonic() if now is None else now) - self.last_tick)
            billable = max(0.0, elapsed - self.delay_seconds)
            if self.active_side == "white":
                w = max(0.0, w - billable)
            else:
                b = max(0.0, b - billable)
        return (round(w, 2), round(b, 2))

    def check_timeout(self, now: float | None = None) -> ColorName | None:
        """Return the color that flagged on time, or None."""
        if not self.enabled:
            return None
        w, b = self.current_times(now)
        if w <= 0.0:
            self.white_remaining = 0.0
            self.active_side = None
            return "white"
        if b <= 0.0:
            self.black_remaining = 0.0
            self.active_side = None
            return "black"
        return None

    def commit_move(self, mover: ColorName, now: float | None = None) -> ColorName | None:
        """Deduct elapsed time for mover, add increment, and start opponent's clock."""
        if not self.enabled:
            return None
        ts = time.monotonic() if now is None else now
        w, b = self.current_times(ts)
        self.white_remaining, self.black_remaining = w, b
        if mover == "white" and self.white_remaining <= 0.0:
            self.active_side = None
            return "white"
        if mover == "black" and self.black_remaining <= 0.0:
            self.active_side = None
            return "black"
        if mover == "white":
            self.white_remaining = round(self.white_remaining + self.increment_seconds, 2)
            self.active_side = "black"
        else:
            self.black_remaining = round(self.black_remaining + self.increment_seconds, 2)
            self.active_side = "white"
        self.last_tick = ts
        return None

    def toggle_pause(self, now: float | None = None) -> bool:
        if not self.enabled:
            return False
        ts = time.monotonic() if now is None else now
        if not self.paused:
            w, b = self.current_times(ts)
            self.white_remaining, self.black_remaining = w, b
            self.paused = True
        else:
            self.last_tick = ts
            self.paused = False
        return self.paused

    def stop(self, now: float | None = None) -> None:
        if self.enabled:
            w, b = self.current_times(now)
            self.white_remaining, self.black_remaining = w, b
        self.active_side = None
        self.last_tick = None

    def to_dict(self, now: float | None = None) -> dict[str, Any]:
        w, b = self.current_times(now)
        return {
            "enabled": self.enabled,
            "base_seconds": self.base_seconds,
            "increment_seconds": self.increment_seconds,
            "delay_seconds": self.delay_seconds,
            "white_remaining": w,
            "black_remaining": b,
            "active_side": self.active_side,
            "paused": self.paused,
        }


_START_COUNTS = {
    chess.PAWN: 8,
    chess.KNIGHT: 2,
    chess.BISHOP: 2,
    chess.ROOK: 2,
    chess.QUEEN: 1,
}
_MAT_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}
_PIECE_LETTERS = {
    chess.QUEEN: "q",
    chess.ROOK: "r",
    chess.BISHOP: "b",
    chess.KNIGHT: "n",
    chess.PAWN: "p",
}


def compute_material_summary(board: chess.Board) -> dict[str, Any]:
    """Compute captured pieces and material balance from a live board."""
    captured_by_white: list[str] = []
    captured_by_black: list[str] = []
    white_score = 0
    black_score = 0
    for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
        w_cnt = len(board.pieces(pt, chess.WHITE))
        b_cnt = len(board.pieces(pt, chess.BLACK))
        white_score += w_cnt * _MAT_VALUES[pt]
        black_score += b_cnt * _MAT_VALUES[pt]
        # Missing black pieces were captured by White; missing white pieces by Black
        for _ in range(max(0, _START_COUNTS[pt] - b_cnt)):
            captured_by_white.append(_PIECE_LETTERS[pt])
        for _ in range(max(0, _START_COUNTS[pt] - w_cnt)):
            captured_by_black.append(_PIECE_LETTERS[pt].upper())
    return {
        "captured_by_white": captured_by_white,
        "captured_by_black": captured_by_black,
        "white_advantage": white_score - black_score,
    }


class FullChessMatch:
    """Complete, server-authoritative chess game covering all 20 official rules."""

    def __init__(
        self,
        *,
        mode: MatchMode = "human_vs_ai",
        player_color: ColorName = "white",
        difficulty: AIDifficulty = "intermediate",
        time_control: str = "rapid_10_0",
        custom_base_seconds: int | None = None,
        custom_increment_seconds: int = 0,
        custom_delay_seconds: int = 0,
        starting_fen: str | None = None,
        repository: OpeningRepository | None = None,
        ai: ChessAIOpponent | None = None,
    ) -> None:
        if starting_fen:
            board = chess.Board(starting_fen)
            if not board.is_valid():
                raise ValueError("Starting FEN is not a valid chess position.")
            self.board = board
        else:
            self.board = chess.Board()

        self.starting_fen = self.board.fen()
        self.mode: MatchMode = mode
        self.player_color: ColorName = player_color
        self.difficulty: AIDifficulty = difficulty
        self.repository = repository
        self.ai = ai or ChessAIOpponent()

        if custom_base_seconds is not None:
            base, inc, delay = max(0, custom_base_seconds), max(0, custom_increment_seconds), max(
                0, custom_delay_seconds
            )
        else:
            base, inc, delay = CLOCK_PRESETS.get(time_control, CLOCK_PRESETS["rapid_10_0"])

        self.clock = ChessClock(
            base_seconds=float(base),
            increment_seconds=float(inc),
            delay_seconds=float(delay),
        )
        self.time_control = time_control
        self.invite_code: str | None = (
            secrets.token_hex(4).upper() if mode == "online_pvp" else None
        )
        self.white_token: str = secrets.token_urlsafe(12)
        self.black_token: str | None = (
            None if mode == "online_pvp" else secrets.token_urlsafe(12)
        )

        self.moves_san: list[str] = []
        self.moves_uci: list[str] = []
        self.fen_history: list[str] = [self.starting_fen]
        self.draw_offer_by: ColorName | None = None
        self.termination_reason: str | None = None
        self.winner: ColorName | None = None
        self.last_eval_cp_white: int | None = None
        self.last_mate_in: int | None = None
        self.last_engine_source: str | None = None

        if self.mode == "human_vs_ai" and self.player_color == "black" and not self.is_over:
            self._execute_ai_move()

    @property
    def turn(self) -> ColorName:
        return "white" if self.board.turn == chess.WHITE else "black"

    @property
    def is_over(self) -> bool:
        if self.termination_reason is not None:
            return True
        flagged = self.clock.check_timeout()
        if flagged is not None:
            self.termination_reason = "timeout"
            self.winner = "black" if flagged == "white" else "white"
            self.clock.stop()
            return True
        outcome = self.board.outcome(claim_draw=False)
        if outcome is not None:
            self.termination_reason = outcome.termination.name.lower()
            if outcome.winner is True:
                self.winner = "white"
            elif outcome.winner is False:
                self.winner = "black"
            else:
                self.winner = None
            self.clock.stop()
            return True
        return False

    def join_online(self) -> tuple[ColorName, str]:
        """Seat the second player in an online private match."""
        if self.mode != "online_pvp":
            raise RuntimeError("Invite join is only available for online matches.")
        if self.black_token is not None:
            raise RuntimeError("Both player seats are already occupied.")
        self.black_token = secrets.token_urlsafe(12)
        return "black", self.black_token

    def submit_move(self, uci: str, *, player_token: str | None = None) -> dict[str, Any]:
        """Validate and apply a legal move; trigger AI reply when in human_vs_ai mode."""
        if self.is_over:
            raise RuntimeError(f"Game is already over ({self.termination_reason}).")
        if self.mode == "online_pvp":
            if self.black_token is None:
                raise RuntimeError("Waiting for opponent to join via invite code.")
            expected_token = self.white_token if self.turn == "white" else self.black_token
            if player_token != expected_token:
                raise RuntimeError("It is not your turn.")
        elif self.mode == "human_vs_ai" and self.turn != self.player_color:
            raise RuntimeError("It is currently the AI's turn.")

        mover = self.turn
        if self.clock.enabled and self.clock.active_side is None and len(self.moves_uci) >= 1:
            self.clock.start_turn(mover)

        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Malformed UCI move: {uci}") from exc
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move in current position: {uci}")

        san = self.board.san(move)
        self.board.push(move)
        self.moves_san.append(san)
        self.moves_uci.append(move.uci())
        self.fen_history.append(self.board.fen())
        self.draw_offer_by = None

        if self.clock.enabled:
            if len(self.moves_uci) == 1:
                self.clock.start_turn(self.turn)
            else:
                flagged = self.clock.commit_move(mover)
                if flagged is not None:
                    self.termination_reason = "timeout"
                    self.winner = "black" if flagged == "white" else "white"
                    self.clock.stop()

        ai_reply: dict[str, Any] | None = None
        if not self.is_over and self.mode == "human_vs_ai" and self.turn != self.player_color:
            ai_reply = self._execute_ai_move()

        return {
            "played_uci": move.uci(),
            "played_san": san,
            "ai_reply": ai_reply,
            "state": self.state_dict(),
        }

    def _execute_ai_move(self) -> dict[str, Any] | None:
        if self.is_over:
            return None
        ai_color = self.turn
        decision = self.ai.choose_move(self.board, difficulty=self.difficulty)
        move = chess.Move.from_uci(decision.uci)
        san = self.board.san(move)
        self.board.push(move)
        self.moves_san.append(san)
        self.moves_uci.append(move.uci())
        self.fen_history.append(self.board.fen())
        self.last_eval_cp_white = decision.score_cp_white
        self.last_mate_in = decision.mate_in
        self.last_engine_source = decision.engine_source
        if self.clock.enabled:
            if len(self.moves_uci) == 1:
                self.clock.start_turn(self.turn)
            else:
                self.clock.commit_move(ai_color)
        _ = self.is_over
        return {
            "uci": decision.uci,
            "san": san,
            "engine_source": decision.engine_source,
            "score_cp_white": decision.score_cp_white,
            "mate_in": decision.mate_in,
        }

    def undo(self) -> None:
        """Undo moves in supported offline modes (human_vs_ai and local_pvp)."""
        if self.mode == "online_pvp":
            raise RuntimeError("Undo is disabled in online multiplayer games.")
        if not self.moves_uci:
            raise ValueError("There is no move to undo.")
        self.termination_reason = None
        self.winner = None
        self.draw_offer_by = None
        if (
            self.mode == "human_vs_ai"
            and self.turn == self.player_color
            and len(self.moves_uci) >= 2
        ):
            self.board.pop()
            self.moves_san.pop()
            self.moves_uci.pop()
            if len(self.fen_history) > 1:
                self.fen_history.pop()
        self.board.pop()
        self.moves_san.pop()
        self.moves_uci.pop()
        if len(self.fen_history) > 1:
            self.fen_history.pop()

    def restart(self) -> None:
        if self.mode == "online_pvp":
            raise RuntimeError("Create a new match to rematch online.")
        self.board = chess.Board(self.starting_fen)
        self.moves_san.clear()
        self.moves_uci.clear()
        self.fen_history = [self.starting_fen]
        self.termination_reason = None
        self.winner = None
        self.draw_offer_by = None
        self.clock = ChessClock(
            base_seconds=self.clock.base_seconds,
            increment_seconds=self.clock.increment_seconds,
            delay_seconds=self.clock.delay_seconds,
        )
        if self.mode == "human_vs_ai" and self.player_color == "black":
            self._execute_ai_move()

    def resign(self, color: ColorName | None = None) -> None:
        if self.is_over:
            return
        resigning = color or (self.player_color if self.mode == "human_vs_ai" else self.turn)
        self.termination_reason = "resignation"
        self.winner = "black" if resigning == "white" else "white"
        self.clock.stop()

    def handle_draw_action(
        self,
        action: Literal["offer", "accept", "decline", "claim"],
        actor: ColorName | None = None,
    ) -> str:
        if self.is_over:
            raise RuntimeError("Game is already finished.")
        side = actor or self.turn
        if action == "claim":
            if self.board.can_claim_threefold_repetition():
                self.termination_reason = "threefold_repetition"
                self.winner = None
                self.clock.stop()
                return "Draw claimed by threefold repetition."
            if self.board.can_claim_fifty_moves():
                self.termination_reason = "fifty_move_rule"
                self.winner = None
                self.clock.stop()
                return "Draw claimed under the fifty-move rule."
            raise ValueError("Position is not eligible for a threefold or 50-move draw claim.")
        if action == "offer":
            if self.mode == "human_vs_ai":
                # AI accepts draw if materially equal or worse in endgame / repetition
                cp = self.last_eval_cp_white or 0
                ai_advantage = cp if self.player_color == "black" else -cp
                if len(self.moves_uci) >= 30 and ai_advantage <= 20:
                    self.termination_reason = "draw_agreement"
                    self.winner = None
                    self.clock.stop()
                    return "AI accepted your draw offer."
                return "AI declined your draw offer."
            self.draw_offer_by = side
            return f"{side.capitalize()} offered a draw."
        if action == "accept":
            if self.draw_offer_by is None:
                raise ValueError("There is no active draw offer to accept.")
            self.termination_reason = "draw_agreement"
            self.winner = None
            self.draw_offer_by = None
            self.clock.stop()
            return "Draw agreed."
        self.draw_offer_by = None
        return "Draw offer declined."

    def export_pgn(self) -> str:
        game = chess.pgn.Game.from_board(self.board)
        game.headers["Event"] = f"KnightForge {self.mode}"
        game.headers["Site"] = "KnightForge Chess"
        if self.is_over:
            if self.winner == "white":
                game.headers["Result"] = "1-0"
            elif self.winner == "black":
                game.headers["Result"] = "0-1"
            else:
                game.headers["Result"] = "1/2-1/2"
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        return game.accept(exporter)

    @classmethod
    def from_pgn(
        cls,
        pgn_text: str,
        *,
        mode: MatchMode = "local_pvp",
        repository: OpeningRepository | None = None,
        ai: ChessAIOpponent | None = None,
    ) -> FullChessMatch:
        """Import and replay a PGN mainline into a live playable FullChessMatch."""
        parsed = chess.pgn.read_game(io.StringIO(pgn_text))
        if parsed is None:
            raise ValueError("No valid PGN game found.")
        if parsed.errors:
            raise ValueError(f"PGN parse error: {parsed.errors[0]}")
        start_fen = parsed.headers.get("FEN", chess.STARTING_FEN)
        match = cls(
            mode=mode,
            time_control="unlimited",
            starting_fen=start_fen,
            repository=repository,
            ai=ai,
        )
        for move in parsed.mainline_moves():
            if move not in match.board.legal_moves:
                raise ValueError(f"PGN contains illegal move: {move.uci()}")
            san = match.board.san(move)
            match.board.push(move)
            match.moves_san.append(san)
            match.moves_uci.append(move.uci())
            match.fen_history.append(match.board.fen())
        _ = match.is_over
        return match

    def state_dict(self) -> dict[str, Any]:
        finished = self.is_over
        opening_name: str | None = None
        variation_labels: list[str] = []
        if (
            self.repository is not None
            and self.moves_uci
            and self.starting_fen == chess.STARTING_FEN
        ):
            rec = OpeningRecognizer(self.repository).recognize(self.moves_uci, notation="uci")
            var = PositionBasedVariationMatcher(self.repository).match(rec)
            if var.matches:
                opening_name = var.matches[0].name
                variation_labels = list(var.matches[0].variation_labels)
            elif rec.matches:
                opening_name = rec.matches[0].name

        checked_king = None
        if self.board.is_check():
            ksq = self.board.king(self.board.turn)
            if ksq is not None:
                checked_king = chess.square_name(ksq)

        return {
            "fen": self.board.fen(),
            "turn": self.turn,
            "mode": self.mode,
            "player_color": self.player_color,
            "difficulty": self.difficulty,
            "invite_code": self.invite_code,
            "waiting_for_opponent": self.mode == "online_pvp" and self.black_token is None,
            "is_check": self.board.is_check(),
            "checked_king_square": checked_king,
            "is_over": finished,
            "termination": self.termination_reason,
            "winner": self.winner,
            "draw_offer_by": self.draw_offer_by,
            "can_claim_draw": (
                not finished
                and (
                    self.board.can_claim_threefold_repetition()
                    or self.board.can_claim_fifty_moves()
                )
            ),
            "legal_moves_uci": [] if finished else sorted(m.uci() for m in self.board.legal_moves),
            "moves_san": list(self.moves_san),
            "moves_uci": list(self.moves_uci),
            "fen_history": list(self.fen_history),
            "material": compute_material_summary(self.board),
            "clock": self.clock.to_dict(),
            "opening": {"name": opening_name, "variations": variation_labels},
            "eval_cp_white": self.last_eval_cp_white,
            "mate_in": self.last_mate_in,
            "engine_source": self.last_engine_source,
        }
