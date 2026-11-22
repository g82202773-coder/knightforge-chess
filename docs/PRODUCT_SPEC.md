# Product Specification

## 1. Product goal

KnightForge helps learners build chess understanding through structured teaching, deliberate practice, and feedback grounded in chess-engine analysis. The core promise is: **learn the reason behind a move, recognize the pattern again, and improve through measured practice.**

## 2. Audiences

- Beginner: rules, safe moves, basic checkmates, and tactical patterns.
- Improver: opening principles, calculation, positional play, and common endgames.
- Advanced learner: repertoire preparation, deeper variations, engine-assisted review, and tournament preparation.

## 3. Core modules

### Chess Academy
Rules and notation; opening principles; tactics; positional concepts; calculation and visualization; middlegames; endgames; checkmate patterns; tournament skills.

### Opening Encyclopedia
Organize openings by family and side to move. Each entry should contain:
- Standard name and ECO code when reliably known.
- Main line and named subvariations as a navigable move tree.
- Legal, engine-checked move sequences.
- Plans for both sides, typical pawn structures, and recurring tactical motifs.
- Common traps with accurate refutations.
- Practice positions and spaced-repetition review.

Start with representative, high-value openings (for example, Italian Game, Ruy Lopez, Sicilian Defence, French Defence, Caro-Kann, Queen's Gambit, King's Indian Defence, London System, and English Opening). Expand systematically; do not label the catalogue exhaustive prematurely.

### Tactics Trainer
Forks, pins, skewers, discovered attacks, double attacks, deflection, decoy, clearance, interference, zwischenzug, mating nets, defensive resources, and sacrifices. Every puzzle needs a legal position, side to move, validated solution, acceptable alternatives where applicable, difficulty estimate, theme tags, and provenance.

### AI Chess Coach
Use a chess engine to calculate candidate lines and evaluations. The coach may explain the supplied analysis in plain language, compare candidate moves, and relate mistakes to training themes. It must not create unsupported legal claims or fabricated variations.

### Practice Arena
Legal games against adjustable-strength opponents, practice positions, endgame drills, and PGN import/review as later milestones.

### Progress and Daily Training
Track lesson completion, puzzle accuracy, response time, recurring errors, theme-level performance, and training streaks. Recommend a realistic daily plan based on weaknesses; avoid treating speed as the only measure of skill.

## 4. Learning loop

1. Assess the learner with a short diagnostic.
2. Build a skill profile from results.
3. Assign lessons and puzzles at an appropriate level.
4. Record correctness, time, hints, and mistake themes.
5. Schedule review using spaced repetition.
6. Update the learner's plan as evidence accumulates.

## 5. MVP acceptance criteria

- Board supports all legal standard-chess moves, including castling, en passant, and all promotion choices.
- Check, checkmate, stalemate, draw claims/automatic draws, and move history behave correctly.
- Board state can be serialized as FEN and games as PGN.
- A learner can complete a beginner lesson and receive deterministic feedback.
- Puzzle solutions are validated against legal move generation.
- Progress persists across sessions for an authenticated user (authentication may follow the first local prototype).
- Engine analysis is clearly distinguished from human-authored lesson explanations.
- Automated tests cover rules edge cases and known regression positions.

## 6. Monetization hypothesis (not validated)

A free tier may include the beginner path, a daily puzzle allowance, and limited engine/AI coaching. Premium may unlock the full curriculum, larger puzzle access, deeper analysis, and offline lessons. Pricing and usage allowances must be tested against real inference and hosting costs before launch.

## 7. Content and legal requirements

- Prefer original lessons or content with explicit reuse rights.
- Record source, author, license, and attribution requirements for each imported dataset.
- Verify the license and distribution obligations of Stockfish and every dependency.
- Do not copy paid courses, proprietary puzzle collections, or copyrighted annotated games without permission.
- Review user privacy, account deletion, data retention, and payment compliance before public release.
