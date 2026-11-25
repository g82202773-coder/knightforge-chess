# Lichess opening-line data

This directory contains a selected subset of opening names and PGN move lines from the
[lichess-org/chess-openings](https://github.com/lichess-org/chess-openings) repository.

- Upstream revision: `48a8c0e733facfdc9a3723fe882e51ec28014074`
- License: CC0 1.0 Universal (see [COPYING.txt](COPYING.txt))
- Upstream source: https://github.com/lichess-org/chess-openings/tree/48a8c0e733facfdc9a3723fe882e51ec28014074
- Local subset: `openings.json`

The source project describes the dataset as ECO, opening name, and a well-known or
common move sequence. KnightForge preserves those source labels and PGN lines. The
KnightForge importer independently replays every PGN with python-chess and refuses
to expose invalid move branches. The imported records are opening references, not
engine evaluations or expert-authored explanations. KnightForge course annotations
remain separately marked for editorial review.

The selected records are grouped into 30 KnightForge launch systems. Dataset attribution
is provided even though CC0 does not require it.
