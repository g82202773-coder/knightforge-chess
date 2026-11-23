# Position-Based Variation Matching

The `PositionBasedVariationMatcher` complements opening-anchor recognition by matching the current position against every legal node in each eligible opening tree.

## Usage

```python
from knightforge_engine import (
    OpeningRecognizer,
    OpeningRepository,
    PositionBasedVariationMatcher,
)

repository = OpeningRepository.load("data/openings/repository.json")
recognition = OpeningRecognizer(repository).recognize("1. e4 c5 2. Nf3 d6 3. d4")
variation_result = PositionBasedVariationMatcher(repository).match(recognition)

for match in variation_result.matches:
    print(match.name, match.matched_line_san, match.variation_labels)
```

## Matching semantics

- The input must first pass `OpeningRecognizer`, which validates SAN/UCI/PGN moves or FEN.
- The matcher traverses all branches in every reviewed/published tree with source, license, and explicit anchor metadata.
- For each opening, it reports the deepest tree node reached by the supplied game position.
- If multiple distinct tree paths in the same opening reach that deepest position, all are returned; the result is marked ambiguous.
- A different move order is marked as a transposition when move history is available.
- FEN matching reports the matching line but sets `matched_via_transposition` to `None`, because FEN cannot reveal move history.
- Returned SAN is generated from the validated stored line, not copied from labels.

This is position-to-tree matching, not an engine evaluation or a guarantee that the stored line is objectively best. Source and license metadata remain curator-supplied claims that require human verification.
