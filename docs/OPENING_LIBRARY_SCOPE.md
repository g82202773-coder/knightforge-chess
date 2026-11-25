# KnightForge Launch Opening Library Scope

## Launch target

KnightForge Version 1 targets 30 major opening systems. This is a deliberately curated first-release set, selected for beginner-to-advanced usefulness and broad coverage of open games, semi-open defences, queen's-pawn systems, Indian defences, flank openings, and gambits.

The opening taxonomy remains broader than this launch set. A taxonomy name is not evidence that a playable course exists.

## The 30 launch systems

| # | System ID | Opening / system |
|---:|---|---|
| 1 | ruy-lopez | Ruy Lopez |
| 2 | italian-game | Italian Game |
| 3 | scotch-game | Scotch Game |
| 4 | kings-gambit | King's Gambit |
| 5 | vienna-game | Vienna Game |
| 6 | four-knights | Four Knights Game |
| 7 | petrov | Petrov Defence |
| 8 | open-sicilian | Open Sicilian |
| 9 | anti-sicilians | Anti-Sicilians |
| 10 | french | French Defence |
| 11 | caro-kann | Caro-Kann Defence |
| 12 | pirc | Pirc Defence |
| 13 | scandinavian | Scandinavian Defence |
| 14 | alekhine | Alekhine's Defence |
| 15 | queens-gambit | Queen's Gambit |
| 16 | slav | Slav Defence |
| 17 | semi-slav | Semi-Slav Defence |
| 18 | london | London System, including Jobava London |
| 19 | colle | Colle System |
| 20 | trompowsky | Trompowsky Attack |
| 21 | catalan | Catalan Opening |
| 22 | kings-indian | King's Indian Defence |
| 23 | grunfeld | Grünfeld Defence |
| 24 | nimzo-indian | Nimzo-Indian Defence |
| 25 | benoni | Benoni Defence |
| 26 | benko | Benko Gambit |
| 27 | english | English Opening |
| 28 | reti | Réti Opening |
| 29 | dutch-stonewall | Stonewall Dutch |
| 30 | dutch-leningrad | Leningrad Dutch |

## Variation coverage contract

For every selected system, the launch library should contain:

1. The principal move order and the major named variations listed for that system in `data/openings/opening_taxonomy.json`.
2. Each named variation as a labelled branch in a legal move tree. A label without a move sequence is taxonomy metadata only.
3. Important opponent alternatives, common transpositions, and known gambit/anti-gambit responses where applicable.
4. Move-by-move explanations: strategic purpose, development priorities, pawn breaks, king safety, typical tactical motifs, and plans for both sides.
5. A useful middlegame hand-off: model positions, candidate plans, and common mistakes.
6. Practice, guided, and mastery training paths that use the same validated tree.

## Quality gates

- Replay every branch from its declared FEN with python-chess and reject illegal moves.
- Preserve move-order distinctions when they change the position or available plans.
- Do not invent ECO codes, sources, licenses, or claim one canonical line where theory has multiple move orders.
- Every course carries a clear editorial status. Draft and in-review courses must not be described as fully reviewed.
- Run unit, API, and browser end-to-end tests before marking a course launch-ready.
- Stockfish analysis may help evaluate positions, but an engine's top line must not be represented as the only playable continuation.

## Meaning of "all variations"

Chess opening theory is open-ended: new ideas, transpositions, and move-order refinements continue to appear. "All variations" for this launch means all principal and important named branches enumerated in the KnightForge taxonomy for the 30 selected systems, plus the practical responses needed to train them. It does not mean every legal chess continuation to checkmate.
