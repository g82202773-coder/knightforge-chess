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


## AdaptiveOpeningCoach integration

Pass a configured `StockfishAnalyzer` to `AdaptiveOpeningCoach` to enable
automatic position guidance. The coach analyses the starting position and
refreshes the bounded analysis after every applied move. The cached analysis
from the *pre-move* position is used to compare the submitted move; the
post-move analysis is then ready for the next prompt.

```python
from knightforge_engine import AdaptiveOpeningCoach, StockfishAnalyzer

coach = AdaptiveOpeningCoach(lesson, repository, analyzer=StockfishAnalyzer())

# The current state already contains the best engine candidate and first hint.
state = coach.state
print(state.recommendation.san)
print(state.active_hint.text)

# Submit a move. The result includes the comparison and guidance for the
# resulting position, without a separate analysis request.
result = coach.submit_uci("e2e4")
print(result.state.move_comparison.explanation)
print(result.state.recommendation.san)
print(result.state.recommendation_arrow)

# Reveal progressively stronger hints for the current recommendation.
state = coach.reveal_hint(2)  # source-square clue
state = coach.reveal_hint(3)  # source-to-target arrow
state = coach.reveal_hint(4)  # full move
```

`OpeningCoachState.recommendation` contains validated engine facts and PV;
`active_hint` begins at level 1; `recommendation_arrow` exposes the complete
candidate arrow for clients that choose to render it. A client can render
`active_hint.arrow_from` / `active_hint.arrow_to` to preserve progressive
disclosure. `move_comparison` refers to the move just submitted and the
analysis of its exact pre-move FEN. If analysis is unavailable or invalid,
`analysis_error` explains why and lesson execution remains usable.

Automatic analysis is enabled only when an analyzer is supplied. Its default
budget is 1 second and MultiPV 3; callers can set bounded
`analysis_time_limit`, `analysis_depth`, and `analysis_multipv` at
construction. Each applied ply triggers one new analysis, so deployments
should configure the Stockfish executable and resource budget deliberately.
