# KnightForge Chess Engine

This package is the shared chess foundation for KnightForge. It is designed to be consumed by the API and, through stable API contracts, by web and Android clients.

## Current implementation scope

- Authoritative standard-chess game state powered by `python-chess`.
- Legal move validation and SAN/UCI/FEN/PGN operations.
- Game termination and draw-state reporting from the rules library.
- A bounded UCI adapter for Stockfish analysis.
- Typed, provenance-aware records for opening lines and tactical knowledge.
- A versioned JSON opening repository with legal validation, ID/ECO/name/alias search, duplicate protection, and atomic file replacement.
- A versioned opening import pipeline that validates complete batches, legal move trees, source/license metadata, and duplicate IDs before one repository save.
- An opening coverage analyzer that compares taxonomy systems and named variations against stored, legally validated move trees and reports missing content, provenance gaps, review state, move-node totals, and transpositions.\n- A rules-backed tactical candidate scanner for immediate checks, captures, promotions, and mate-in-one, with an explicitly heuristic capture-ordering score.
- A position-aware guided lesson session engine that validates branching lesson trees, emits voice-ready coaching text and arrow coordinates, checks learner moves, follows actual opponent replies, and pauses safely on unknown opponent deviations.

## Important boundaries

The rules library decides legality and game state. Stockfish supplies search results and evaluations under explicit limits. The knowledge catalogue stores reviewed chess concepts and lines. These are separate responsibilities.

This package does **not** yet contain a complete opening encyclopedia, puzzle database, custom search algorithm, or a bundled Stockfish executable. Those require separate implementation, sourced content, validation, and testing. Stockfish must be installed separately and its distribution terms must be followed.

## Opening coverage analysis

The taxonomy is a naming/index layer, not playable opening content. Coverage is counted only when a repository tree uses the exact taxonomy system ID, and a named variation is counted only when a node in that tree carries the exact variation label. Similar names and aliases do not inflate coverage.

```python
from knightforge_engine import OpeningCatalog, OpeningRepository, analyze_opening_coverage

catalog = OpeningCatalog.load("data/openings/opening_taxonomy.json")
repository = OpeningRepository.load("data/openings/repository.json")
report = analyze_opening_coverage(catalog, repository)
print(report.to_dict())
```

The report exposes missing systems and variations, records missing ECO/source/license metadata, draft versus reviewed records, validated move-node totals, and transposition counts. These are content coverage metrics, not a claim that the taxonomy itself is exhaustive.

## Opening content import

Prepare a UTF-8 JSON document with this envelope:

```json
{
  "schema_version": 1,
  "openings": [
    {
      "schema_version": 1,
      "opening_id": "example-opening",
      "name": "Example Opening",
      "side": "both",
      "source_name": "A source whose terms permit this use",
      "source_url": "https://example.org/source",
      "license_name": "CC BY 4.0",
      "review_status": "draft",
      "roots": [{"move_uci": "e2e4"}]
    }
  ]
}
```

Every record must include source and license labels, and every move is replayed through the rules library. The importer records declared provenance but cannot independently establish that a source's license is genuine or grants redistribution rights. Existing IDs and duplicate IDs in the same batch are rejected; resolve conflicts explicitly rather than silently overwriting curated records.

```python
import json
from pathlib import Path
from knightforge_engine import OpeningRepository, import_openings

repository = OpeningRepository.load("data/openings/repository.json")
payload = json.loads(Path("data/openings/import.json").read_text(encoding="utf-8"))
report = import_openings(payload, repository)
print(report.imported_ids)
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Set `STOCKFISH_PATH` to the Stockfish executable when running analysis. Do not expose arbitrary executable paths or unrestricted engine settings through a public API.


## Position-aware guided learning\n\nSee [Position-Aware Guided Learning](../docs/GUIDED_LEARNING.md) for lesson construction, live coach prompts, branch selection, correction behavior, and client integration boundaries. The service returns text and board guidance metadata; it does not yet synthesize audio or render an animated coach.\n\n## Tactical candidate scanning\n\nSee [Tactical Candidate Scanning](../docs/TACTICAL_SCANNING.md) for the API, score semantics, and limitations. The scanner is a forcing-move candidate generator, not a substitute for Stockfish search.\n\n## Position-based variation matching

Opening-anchor recognition identifies curated opening anchors. The position-based variation matcher goes further: after a move history or FEN has been validated by `OpeningRecognizer`, it checks the position against every node in each eligible reviewed opening tree and returns the deepest matching line, SAN sequence, and variation labels.

See [Position-Based Variation Matching](../docs/POSITION_BASED_VARIATION_MATCHING.md) for matching semantics and an example. FEN can identify a position but cannot establish the move order; its transposition field is therefore `None`.
