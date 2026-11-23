# Tactical Candidate Scanning

KnightForge's tactical scanner is a rules-backed candidate generator. It enumerates legal moves and retains moves that immediately give check, capture, or promote. It also marks moves that produce checkmate on the next position.

## Example

```python
from knightforge_engine import ChessGame, TacticalScanner

game = ChessGame()
game.push_san("e4")
game.push_san("d5")

scan = TacticalScanner(game).scan()
for candidate in scan.candidates:
    print(candidate.san, candidate.motifs, candidate.capture_priority_cp)
```

## Semantics and limitations

- Legality and check/checkmate status come from `python-chess`.
- A candidate may have more than one motif, for example a checking capture.
- `capture_priority_cp` is victim piece value minus attacker piece value, using a simple material table. It is only a move-ordering heuristic; it is **not** static exchange evaluation and does not predict whether the capture wins material after replies.
- The scanner finds immediate forcing candidates only. It does not prove multi-move combinations, identify every fork/pin/skewer, evaluate quiet threats, or classify blunders.
- Candidate ordering is a deterministic heuristic, not a chess-strength ranking.
- The scanner copies the game board and does not mutate the caller's game.

Use Stockfish analysis for position evaluation and deeper tactical search. Do not present this scanner's output as a complete tactical solution.
