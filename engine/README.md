# KnightForge Chess Engine

This package is the shared chess foundation for KnightForge. It is designed to be consumed by the API and, through stable API contracts, by web and Android clients.

## Current implementation scope

- Authoritative standard-chess game state powered by `python-chess`.
- Legal move validation and SAN/UCI/FEN/PGN operations.
- Game termination and draw-state reporting from the rules library.
- A bounded UCI adapter for Stockfish analysis.
- Typed, provenance-aware records for opening lines and tactical knowledge.

## Important boundaries

The rules library decides legality and game state. Stockfish supplies search results and evaluations under explicit limits. The knowledge catalogue stores reviewed chess concepts and lines. These are separate responsibilities.

This package does **not** yet contain a complete opening encyclopedia, puzzle database, custom search algorithm, or a bundled Stockfish executable. Those require separate implementation, sourced content, validation, and testing. Stockfish must be installed separately and its distribution terms must be followed.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Set `STOCKFISH_PATH` to the Stockfish executable when running analysis. Do not expose arbitrary executable paths or unrestricted engine settings through a public API.
