# Coach Decision Layer

The `CoachDecisionLayer` converts a validated `AnalysisResult` into legal,
beginner-readable candidate recommendations. It is deterministic and derives
its move facts from the analysed board and replayed principal variations.

## Example

```python
from knightforge_engine import CoachDecisionLayer

decision = CoachDecisionLayer(analysis)
best = decision.best
print(best.piece, best.from_square, best.to_square, best.san)
print(best.hints[0].text)  # progressively reveal hints 1 through 4
comparison = decision.compare_move("d2d4", position_fen=analysis.fen)
print(comparison.explanation)
```

## Contract and safety boundaries

- Every candidate PV is replayed through python-chess. Malformed or illegal
  engine lines are rejected rather than shown to a learner.
- Each recommendation includes piece, source/destination squares, SAN/UCI,
  capture/check/mate/promotion facts, and the validated candidate continuation.
- Four hint levels progressively disclose piece type, source square,
  destination square/arrow, and finally the move itself. A client can reveal
  one level at a time and render the supplied arrow coordinates.
- `compare_move` requires the exact pre-move FEN used for analysis. It reports
  whether the played move appears in the returned candidate list and its rank.
  A missing move is not labelled a blunder, and no centipawn-loss estimate is
  claimed because this adapter does not analyse the resulting position.
- Centipawn and mate values remain explicitly identified as engine output from
  the side-to-move perspective. They are not win probabilities, objective
  truths, or established chess principles.
- The module does not infer strategic plans from a score. Explanations are
  limited to concrete, rules-backed board facts and transparent engine ranking.
- Engine recommendations remain distinct from reviewed opening knowledge.
  They must not be published as opening theory without independent sourcing
  and review.

For an accurate move-quality loss estimate, analyse both the original position
and the position after the learner's move under a comparable engine limit.
That is a separate operation and is intentionally not approximated here.
