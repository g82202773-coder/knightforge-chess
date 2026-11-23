# Opening Recognition

KnightForge recognizes openings from validated move history or a FEN position. Recognition is deliberately conservative: a taxonomy name alone is never enough to produce a match.

## Input forms

`OpeningRecognizer(repository).recognize(...)` accepts one of:

- SAN text, for example `1. e4 c5 2. Nf3 d6`.
- A sequence of SAN tokens, including black move-number tokens such as `1... c5`.
- UCI tokens, with `notation="uci"`, for example `["e2e4", "c7c5"]`.
- PGN text, with `notation="pgn"`; PGN headers are also recognized in auto mode.
- A FEN string using `fen=...`.

Do not supply both moves and FEN. SAN/UCI moves are checked against the legal moves at every ply. FEN input is checked for position validity.

## Match semantics

A stored opening is eligible only when it is reviewed or published, has source and license metadata, and has a legal explicit `anchor_uci` path in its move tree.

For move history, KnightForge compares every reached position against eligible anchor positions. This recognizes a transposition when a different move order reaches the same chess position. The result records the ply where the anchor position was reached and whether the match was transposed.

For FEN, KnightForge can identify an exact stored anchor position, but cannot recover the move order that produced it. A FEN result therefore has no claimed move history.

If multiple reviewed records share the same anchor position, all are returned and `ambiguous` is true. The recognizer does not silently choose one.

## Variation labels

Variation labels are taken from the stored tree path for the matched anchor. A label in the taxonomy is not itself a playable line. A variation becomes recognizable only after a legal move tree, explicit anchor, provenance, license metadata, and review status have been supplied.

## PGN scope

PGN recognition currently uses the mainline. Alternative PGN branches are not yet imported into the repository automatically; add them as explicit branches in a reviewed `OpeningTree` or use a future PGN branch-import workflow.

## Data quality boundary

Source and license fields are provenance claims supplied during import; KnightForge does not independently certify copyright ownership or redistribution permission. Reviewers must verify source accuracy, licensing, opening naming, and move-tree quality before publishing records.

## Current validation coverage

The test suite covers SAN and UCI recognition, PGN mainline parsing, headerless PGN when explicitly selected, FEN matching, transpositions, ambiguity, unreviewed-record exclusion, illegal SAN, invalid FEN, and unknown valid positions.
