# Adaptive Opening Coach

`AdaptiveOpeningCoach` composes three existing validated services:

1. `GuidedLessonSession` enforces legal moves and the curated lesson branch.
2. `OpeningRecognizer` identifies reviewed opening anchors from move history (or position-only FEN for custom lesson starts).
3. `PositionBasedVariationMatcher` finds the deepest reviewed variation node reached by the current position.

## Example

```python
from knightforge_engine import AdaptiveOpeningCoach, GuidedLesson, LessonNode, OpeningRepository

repository = OpeningRepository.load("data/openings/repository.json")
lesson = GuidedLesson(
    lesson_id="open-game-01",
    title="Open Game",
    learner_color="white",
    roots=(LessonNode("e2e4", "Control the centre.", children=()),),
)
coach = AdaptiveOpeningCoach(lesson, repository)
state = coach.prompt()
print(state.prompt.voice_script, state.prompt.arrow_from, state.prompt.arrow_to)
print(state.knowledge_status, state.variation_match.matches)
```

## Knowledge status

- `reviewed_variation_match`: the current position reaches a node in a reviewed opening tree.
- `reviewed_opening_anchor_only`: the opening anchor is recognized, but no deeper reviewed node matches.
- `no_reviewed_match`: no reviewed opening/variation is established for this position.

The service never upgrades an engine guess or an unreviewed record into opening theory. The lesson tree still controls expected moves; recognition and variation matching provide independently validated context. For non-standard lesson starting FENs, the service uses position-only matching and does not claim a historical move order.

## Safe engine analysis after a deviation

Pass a server-configured `StockfishAnalyzer` into the coach to enable explicit analysis after an unexpected opponent move:

```python
from knightforge_engine import AdaptiveOpeningCoach, StockfishAnalyzer

coach = AdaptiveOpeningCoach(lesson, repository, analyzer=StockfishAnalyzer())
# After the opponent makes an unlisted but legal move:
submission = coach.session.submit_uci("d7d5")
analysis = coach.analyze_deviation(time_limit=1.0, depth=14, multipv=3)
for line in analysis.lines:
    print(line.moves_san, line.score_cp, line.score_mate)
```

The executable must be installed and configured on the trusted server with `STOCKFISH_PATH`. The executable path is never accepted from a learner request. Analysis is opt-in and available only while the lesson is paused at an opponent deviation. The adapter enforces 0.05–30 seconds, depth 1–40, and MultiPV 1–5; it validates the FEN and replays returned PV moves through legal move validation.

Engine candidate lines are analysis suggestions, **not verified opening theory**. They must not be added to the opening catalogue automatically. The coach does not silently call Stockfish on every move, so deployments retain control over CPU usage.

Clients still render audio, avatar, arrows, highlights, and speech UI.
