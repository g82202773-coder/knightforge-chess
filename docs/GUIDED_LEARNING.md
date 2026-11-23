# Position-Aware Guided Learning

The guided lesson engine is the backend foundation for KnightForge's personal chess coach. It validates a branching lesson against the chess rules library and emits a prompt derived from the live board position.

## Current capability

- A lesson declares its ID, title, learner color, starting FEN, and branching LessonNode move tree.
- Every branch is replayed with python-chess before the lesson can start.
- Each prompt includes the current FEN, side to move, legal UCI moves, expected SAN/UCI, source and destination squares for an arrow, highlighted squares, explanation, and a voice-ready script.
- A legal but incorrect learner move is not applied; the coach gives corrective guidance and allows a retry.
- Expected opponent replies select their corresponding branch. An opponent move outside the curated tree is applied to the board, but guided continuation pauses instead of inventing an opening line.
- Undo restores the previous board, including the full python-chess move stack, and lesson branch. Restart restores the declared starting FEN.

## Example

Create a GuidedLesson with a LessonNode tree, then construct GuidedLessonSession(lesson). Call session.prompt() to obtain the current voice script and arrow coordinates. Submit moves with session.submit_uci("e2e4").

## Client responsibilities and boundaries

The service returns text and visual metadata. A web or Android client must render the chessboard, arrow, square highlights, speech bubble, avatar, and actual audio playback. This module does not synthesize speech, animate a face, call an LLM, or run Stockfish. Voice text is generated from the current validated lesson node and board, not played from a fixed prerecorded clip.

Unexpected opponent replies deliberately pause the curated lesson. A future analysis adapter can inspect the new position with Stockfish and propose candidate continuations; any recommendation must be marked as engine analysis rather than reviewed opening theory. The engine must not label a continuation as a known Jobava London line unless reviewed knowledge supports that claim.
