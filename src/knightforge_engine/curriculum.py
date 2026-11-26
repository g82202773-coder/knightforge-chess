"""Structured 5-level Chess Academy covering Rules, Openings, Gambits,
Strategy, Middlegames, and Endgames — every move legally validated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .guided_learning import GuidedLesson, LessonNode

LessonCategory = Literal[
    "basics", "rules", "opening", "gambit", "tactics", "strategy", "middlegame", "endgame"
]
DifficultyLevel = Literal["beginner", "intermediate", "advanced", "expert"]


@dataclass(frozen=True, slots=True)
class LessonEntry:
    """Curriculum metadata paired with a legally validated GuidedLesson."""

    lesson: GuidedLesson
    category: LessonCategory
    level: int
    difficulty: DifficultyLevel
    summary: str
    objectives: tuple[str, ...]
    key_ideas: tuple[str, ...] = ()

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "lesson_id": self.lesson.lesson_id,
            "title": self.lesson.title,
            "learner_color": self.lesson.learner_color,
            "starting_fen": self.lesson.starting_fen,
            "category": self.category,
            "level": self.level,
            "difficulty": self.difficulty,
            "summary": self.summary,
            "objectives": list(self.objectives),
            "key_ideas": list(self.key_ideas),
        }


def _chain_nodes(steps: list[tuple[str, str, str]]) -> tuple[LessonNode, ...]:
    """Construct a linear LessonNode tree from (uci, explanation, hint)."""
    child: tuple[LessonNode, ...] = ()
    for uci, explanation, hint in reversed(steps):
        child = (LessonNode(uci, explanation, children=child, hint=hint),)
    return child


def _build_entries() -> tuple[LessonEntry, ...]:
    entries = (
        # ---------------- LEVEL 0: ABSOLUTE PIECE BASICS ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "basics-pawn-one-step",
                "Level 0 · Pawn Basics: One Step Forward",
                "white",
                _chain_nodes([
                    (
                        "e3e4",
                        "A pawn normally moves 1 square straight forward and never backward.",
                        "Push the e3 pawn one square ahead to e4.",
                    ),
                ]),
                starting_fen="4k3/8/8/8/8/4P3/8/4K3 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Learn how a pawn marches one square straight forward.",
            objectives=("Move a pawn one square forward",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "basics-pawn-two-steps",
                "Level 0 · Pawn Basics: 1 or 2 Steps From Start",
                "white",
                _chain_nodes([
                    (
                        "e2e4",
                        "On its very first move from rank 2, a pawn may advance 1 or 2 squares.",
                        "Advance your e2 pawn two squares straight to e4.",
                    ),
                ]),
                starting_fen="4k3/8/8/8/8/8/4P3/4K3 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Use the pawn's special two-square opening step from its starting rank.",
            objectives=("Advance a starting-rank pawn two squares to claim the centre",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "basics-pawn-capture",
                "Level 0 · Pawn Basics: Diagonal Captures",
                "white",
                _chain_nodes([
                    (
                        "e4d5",
                        "Pawns move straight forward, but they capture 1 square diagonally.",
                        "Capture Black's d5 pawn diagonally with your e4 pawn.",
                    ),
                ]),
                starting_fen="4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Capture an enemy piece diagonally with a pawn.",
            objectives=("Distinguish pawn movement from diagonal pawn capture",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "basics-knight-jump",
                "Level 0 · Knight Basics: The L-Shape Jump",
                "white",
                _chain_nodes([
                    (
                        "g1f3",
                        "Knights move in an L-shape (2 squares + 1) and can jump over pieces.",
                        "Jump your g1 knight over the pawns to f3.",
                    ),
                ]),
                starting_fen="4k3/8/8/8/8/8/PPPPPPPP/4K1N1 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Master the knight's unique L-shape jump over blocking pawns.",
            objectives=("Move a knight in an L-shape", "Jump over friendly pawns"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "basics-bishop-diagonal",
                "Level 0 · Bishop Basics: Long Diagonals",
                "white",
                _chain_nodes([
                    (
                        "c1f4",
                        "Bishops glide any number of empty squares diagonally on one color.",
                        "Slide your dark-squared bishop from c1 to f4.",
                    ),
                ]),
                starting_fen="4k3/8/8/8/8/8/8/2B1K3 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Control long diagonals with the bishop.",
            objectives=("Move a bishop diagonally across open squares",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "basics-rook-lines",
                "Level 0 · Rook Basics: Files & Ranks",
                "white",
                _chain_nodes([
                    (
                        "a1a7",
                        "Rooks travel any number of empty squares horizontally or vertically.",
                        "Slide your rook straight up the a-file to a7.",
                    ),
                ]),
                starting_fen="4k3/8/8/8/8/8/8/R3K3 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Use rooks along open vertical files and horizontal ranks.",
            objectives=("Move a rook straight along an open file",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "basics-queen-king",
                "Level 0 · Queen & King Basics",
                "white",
                _chain_nodes([
                    (
                        "d1h5",
                        "The Queen combines Rook + Bishop power — straight or diagonal.",
                        "Sweep your queen diagonally from d1 to h5.",
                    ),
                    ("e8f8", "The King steps 1 square in any safe direction.", ""),
                    (
                        "e1e2",
                        "Your King also moves 1 square at a time and may never step into check.",
                        "Step your white king one square up to e2.",
                    ),
                ]),
                starting_fen="4k3/8/8/8/8/8/8/3QK3 w - - 0 1",
            ),
            category="basics",
            level=0,
            difficulty="beginner",
            summary="Combine Queen mobility with safe one-square King movement.",
            objectives=("Move the Queen diagonally", "Move the King one safe square"),
        ),
        # ---------------- LEVEL 1: ABSOLUTE BEGINNER ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "rules-castling-safety",
                "Level 1 · Castling & King Safety",
                "white",
                _chain_nodes([
                    (
                        "e1g1",
                        "Castle kingside to tuck your king behind pawns and activate the rook.",
                        "Move your king two squares toward the h1 rook.",
                    ),
                ]),
                starting_fen=(
                    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
                ),
            ),
            category="rules",
            level=1,
            difficulty="beginner",
            summary="Castle kingside to protect your king and activate the rook in one move.",
            objectives=("Recognize legal castling conditions", "Connect your rooks early"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "rules-en-passant",
                "Level 1 · En Passant Capture",
                "white",
                _chain_nodes([
                    (
                        "e5d6",
                        "Capture Black's d5 pawn en passant on d6 on the immediate next move.",
                        "Your e5 pawn can capture diagonally to d6.",
                    ),
                ]),
                starting_fen=(
                    "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
                ),
            ),
            category="rules",
            level=1,
            difficulty="beginner",
            summary="Master the special en passant pawn capture before the opportunity expires.",
            objectives=("Execute en passant on the immediate next move",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "rules-pawn-promotion",
                "Level 1 · Pawn Promotion",
                "white",
                _chain_nodes([
                    (
                        "e7e8q",
                        "Advance to the eighth rank and promote your pawn into a queen.",
                        "Push the e7 pawn to e8 and promote to a queen.",
                    ),
                ]),
                starting_fen="7k/4P3/6K1/8/8/8/8/8 w - - 0 1",
            ),
            category="rules",
            level=1,
            difficulty="beginner",
            summary="Promote a passed pawn on the eighth rank to deliver immediate checkmate.",
            objectives=("Promote to a queen for checkmate",),
        ),
        # ---------------- LEVEL 2: BEGINNER OPENINGS ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "open-game-first-five",
                "Open Game: First Five Moves",
                "white",
                (
                    LessonNode(
                        "e2e4",
                        "Occupy the centre. The e4-pawn controls d5 and f5 and opens lines.",
                        children=(
                            LessonNode(
                                "e7e5",
                                "Black contests the centre with the same central pawn advance.",
                                children=(
                                    LessonNode(
                                        "g1f3",
                                        "Develop the knight toward the centre and attack e5.",
                                        children=(
                                            LessonNode(
                                                "b8c6",
                                                "Black develops a knight and supports e5.",
                                                children=(
                                                    LessonNode(
                                                        "f1b5",
                                                        "The Ruy Lopez bishop pressures c6.",
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            category="opening",
            level=2,
            difficulty="beginner",
            summary="Learn the foundational Open Game sequence leading into the Ruy Lopez.",
            objectives=("Claim central space", "Develop with tempo", "Pressure Black's centre"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "opening-italian-game",
                "Italian Game: Targeting f7",
                "white",
                (
                    LessonNode(
                        "e2e4",
                        "Claim central space with e4.",
                        children=(
                            LessonNode(
                                "e7e5",
                                "Black responds symmetrically.",
                                children=(
                                    LessonNode(
                                        "g1f3",
                                        "Develop and attack e5.",
                                        children=(
                                            LessonNode(
                                                "b8c6",
                                                "Black defends e5.",
                                                children=(
                                                    LessonNode(
                                                        "f1c4",
                                                        "Aim the bishop at the weak f7 square.",
                                                        children=(
                                                            LessonNode(
                                                                "f8c5",
                                                                "Giuoco Piano symmetry.",
                                                                children=(
                                                                    LessonNode(
                                                                        "c2c3", "Prepare d4."
                                                                    ),
                                                                ),
                                                            ),
                                                            LessonNode(
                                                                "g8f6",
                                                                "Two Knights Defence.",
                                                                children=(
                                                                    LessonNode(
                                                                        "d2d3",
                                                                        "Defend e4 solidly.",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            category="opening",
            level=2,
            difficulty="beginner",
            summary="Play the Italian Game cleanly against both Giuoco Piano and Two Knights.",
            objectives=("Develop harmoniously", "Prepare the c3-d4 central break"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "opening-london-system",
                "London System: Solid Pyramid",
                "white",
                _chain_nodes([
                    ("d2d4", "Claim central dark squares with d4.", ""),
                    ("d7d5", "Black contests the centre.", ""),
                    ("c1f4", "Develop Bf4 before closing the diagonal with e3.", ""),
                    ("g8f6", "Black develops a kingside knight.", ""),
                    ("e2e3", "Build the solid London pawn pyramid.", ""),
                    ("e7e6", "Black prepares ...Bd6.", ""),
                    ("g1f3", "Control the critical e5 outpost.", ""),
                ]),
            ),
            category="opening",
            level=2,
            difficulty="beginner",
            summary="Master the reliable London System setup and key e5 square control.",
            objectives=("Develop Bf4 outside the pawn chain", "Anchor the d4-e3-c3 pyramid"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "opening-sicilian-najdorf",
                "Sicilian Defence: Asymmetric Counterplay",
                "black",
                _chain_nodes([
                    ("e2e4", "White claims central space.", ""),
                    ("c7c5", "Fight for d4 asymmetrically from the flank.", ""),
                    ("g1f3", "White prepares d4.", ""),
                    ("d7d6", "Control e5 and keep pawn structure flexible.", ""),
                    ("d2d4", "White opens the centre.", ""),
                    ("c5d4", "Trade a flank pawn for a central pawn.", ""),
                    ("f3d4", "White recaptures centrally.", ""),
                    ("g8f6", "Develop with tempo on e4.", ""),
                ]),
            ),
            category="opening",
            level=3,
            difficulty="intermediate",
            summary="Play Black's sharpest defence to 1.e4 and win an extra central pawn.",
            objectives=("Create a half-open c-file", "Develop with tempo on e4"),
        ),
        # ---------------- GAMBIT ACADEMY ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "gambit-kings-gambit",
                "Gambit Academy · King's Gambit",
                "white",
                _chain_nodes([
                    ("e2e4", "Occupy the centre.", ""),
                    ("e7e5", "Black mirrors central control.", ""),
                    ("f2f4", "Offer the f-pawn to deflect e5 and open the f-file.", ""),
                    ("e5f4", "Black accepts the gambit pawn.", ""),
                    ("g1f3", "Stop ...Qh4+ while preparing a strong d4 centre.", ""),
                ]),
            ),
            category="gambit",
            level=3,
            difficulty="intermediate",
            summary="Sacrifice the f-pawn on move 2 for open lines and kingside attacking play.",
            objectives=("Open the f-file", "Prevent ...Qh4+ with 3.Nf3"),
            key_ideas=(
                "Compensation: Open f-file + central pawn duo after d4",
                "Defence for Black: 2...Bc5 (Declined) or 2...d5 (Falkbeer)",
            ),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "gambit-evans-gambit",
                "Gambit Academy · Evans Gambit",
                "white",
                _chain_nodes([
                    ("e2e4", "Open the centre.", ""),
                    ("e7e5", "Black replies e5.", ""),
                    ("g1f3", "Attack e5.", ""),
                    ("b8c6", "Defend e5.", ""),
                    ("f1c4", "Italian bishop.", ""),
                    ("f8c5", "Giuoco Piano.", ""),
                    ("b2b4", "Offer the b-pawn to deflect Black's bishop with tempo.", ""),
                    ("c5b4", "Black takes the offered pawn.", ""),
                    ("c2c3", "Gain tempo on the bishop and prepare an immediate d4.", ""),
                ]),
            ),
            category="gambit",
            level=3,
            difficulty="intermediate",
            summary="Deflect Black's bishop with 4.b4 to seize a dominant centre and swift attack.",
            objectives=("Gain tempo with c3 and d4", "Exploit Black's uncastled king"),
            key_ideas=("Compensation: Two tempos + sweeping central pawns",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "gambit-smith-morra",
                "Gambit Academy · Smith-Morra Gambit",
                "white",
                _chain_nodes([
                    ("e2e4", "King's pawn.", ""),
                    ("c7c5", "Sicilian Defence.", ""),
                    ("d2d4", "Challenge c5 immediately.", ""),
                    ("c5d4", "Black captures.", ""),
                    ("c2c3", "Offer a pawn for rapid development and open c/d files.", ""),
                    ("d4c3", "Black accepts.", ""),
                    ("b1c3", "Recapture with development — White leads in piece activity.", ""),
                ]),
            ),
            category="gambit",
            level=3,
            difficulty="intermediate",
            summary="Turn the Sicilian into a fierce attacking battle with open central files.",
            objectives=("Develop all minor pieces rapidly", "Target d6 and f7"),
            key_ideas=("Compensation: Open c/d files + 2-move development lead",),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "gambit-danish-gambit",
                "Gambit Academy · Danish Gambit",
                "white",
                _chain_nodes([
                    ("e2e4", "Open game.", ""),
                    ("e7e5", "Black mirrors.", ""),
                    ("d2d4", "Center Game.", ""),
                    ("e5d4", "Black captures d4.", ""),
                    ("c2c3", "Offer a second pawn to unleash both bishops on long diagonals.", ""),
                    ("d4c3", "Black captures c3.", ""),
                    ("f1c4", "Develop aiming at f7.", ""),
                ]),
            ),
            category="gambit",
            level=3,
            difficulty="intermediate",
            summary="Sacrifice pawns to unleash twin bishops raking Black's kingside.",
            objectives=("Maximize bishop diagonal pressure", "Attack before Black castles"),
            key_ideas=("Compensation: Twin bishops raking the kingside", "Defence: 3...d5!"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "gambit-queens-gambit",
                "Gambit Academy · Queen's Gambit",
                "white",
                _chain_nodes([
                    ("d2d4", "Occupy d4.", ""),
                    ("d7d5", "Black occupies d5.", ""),
                    ("c2c4", "Offer the flank c-pawn to lure Black's d5 pawn away.", ""),
                    ("d5c4", "Black accepts (QGA).", ""),
                    ("g1f3", "Stop ...e5 and prepare to recover the c4 pawn smoothly.", ""),
                ]),
            ),
            category="gambit",
            level=2,
            difficulty="beginner",
            summary="Learn why the Queen's Gambit is a sound positional pawn offer.",
            objectives=("Fight for central control", "Prevent Black from holding c4"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "gambit-budapest",
                "Gambit Academy · Budapest Gambit",
                "black",
                _chain_nodes([
                    ("d2d4", "White plays d4.", ""),
                    ("g8f6", "Black develops flexibly.", ""),
                    ("c2c4", "White expands.", ""),
                    ("e7e5", "Counter-strike the centre immediately with 2...e5.", ""),
                    ("d4e5", "White accepts.", ""),
                    ("f6g4", "Attack e5 right away and activate Black's pieces rapidly.", ""),
                ]),
            ),
            category="gambit",
            level=3,
            difficulty="intermediate",
            summary="Surprise 1.d4 players with sharp tactical piece play from move 2.",
            objectives=("Regain e5 with active pieces", "Spot smothered-mate traps on d3"),
        ),
        # ---------------- STRATEGY ACADEMY (LEVEL 3-4) ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "strategy-open-files",
                "Strategy Academy · Seizing the Open File",
                "white",
                _chain_nodes([
                    (
                        "a1d1",
                        "Place your rook on the open d-file to threaten infiltration to d7.",
                        "Move a rook onto the completely open file.",
                    ),
                ]),
                starting_fen="2r2rk1/pp3ppp/4p3/8/8/4P3/PP3PPP/R4RK1 w - - 0 1",
            ),
            category="strategy",
            level=3,
            difficulty="intermediate",
            summary="Dominate open files with rooks to create invasion targets on the 7th rank.",
            objectives=("Identify open files", "Seize file control before the opponent"),
            key_ideas=("Rooks belong on open and half-open files", "Aim for the 7th rank"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "strategy-knight-outpost",
                "Strategy Academy · Dominant Knight Outpost",
                "white",
                _chain_nodes([
                    (
                        "c3d5",
                        "Plant the knight on the permanent d5 outpost where no black pawn attacks.",
                        "Jump your knight onto the weak central square in Black's camp.",
                    ),
                ]),
                starting_fen="r2q1rk1/pp3ppp/2nbp3/3p4/3P4/2N2N2/PP2BPPP/R2Q1RK1 w - - 0 1",
            ),
            category="strategy",
            level=4,
            difficulty="advanced",
            summary="Exploit holes in enemy pawns by anchoring a knight outpost.",
            objectives=("Spot weak squares", "Anchor minor pieces on protected outposts"),
            key_ideas=("Outposts cannot be chased by enemy pawns",),
        ),
        # ---------------- MIDDLEGAME ACADEMY (LEVEL 3-4) ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "middlegame-central-break",
                "Middlegame · Timely Central Pawn Break",
                "white",
                _chain_nodes([
                    (
                        "e4d5",
                        "Open the e-file while Black's king is still uncastled in the centre.",
                        "Capture on d5 to open lines toward the uncastled king.",
                    ),
                ]),
                starting_fen=(
                    "r1bqk2r/ppp2ppp/2n1pn2/3p4/3PP3/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 0 6"
                ),
            ),
            category="middlegame",
            level=3,
            difficulty="intermediate",
            summary="Open central files when ahead in development against an uncastled king.",
            objectives=("Open files against an uncastled king", "Create initiative"),
        ),
        # ---------------- ENDGAME ACADEMY (LEVEL 2-5) ----------------
        LessonEntry(
            lesson=GuidedLesson(
                "endgame-king-queen-mate",
                "Endgame · King & Queen Box Mate",
                "white",
                _chain_nodes([
                    (
                        "d6e7",
                        "Restrict Black's king to the corner without causing stalemate.",
                        "Keep the queen close to force the king to h8.",
                    ),
                    ("g8h8", "Only legal reply.", ""),
                    ("e7g7", "Deliver supported queen checkmate on g7.", ""),
                ]),
                starting_fen="6k1/8/3Q1K2/8/8/8/8/8 w - - 0 1",
            ),
            category="endgame",
            level=2,
            difficulty="beginner",
            summary="Coordinate king and queen to deliver checkmate cleanly without stalemate.",
            objectives=("Avoid stalemate", "Deliver supported mate"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "endgame-opposition-basics",
                "Endgame · King Opposition & Key Squares",
                "white",
                _chain_nodes([
                    (
                        "e4e5",
                        "Seize direct opposition in front of your pawn to control key squares.",
                        "Advance your king straight ahead to confront Black's king.",
                    ),
                ]),
                starting_fen="8/4k3/8/8/4K3/4P3/8/8 w - - 0 1",
            ),
            category="endgame",
            level=3,
            difficulty="intermediate",
            summary="Take direct opposition so your king leads the pawn safely to promotion.",
            objectives=("Place your king in front of your pawn", "Seize direct opposition"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "endgame-lucena-bridge",
                "Endgame · Lucena Position (Building the Bridge)",
                "white",
                _chain_nodes([
                    (
                        "f1f4",
                        "Lift the rook to the fourth rank to build the winning Lucena bridge.",
                        "Move the rook to the 4th rank so it can shield vertical checks later.",
                    ),
                ]),
                starting_fen="1K1k4/1P6/8/8/8/8/r7/5R2 w - - 0 1",
            ),
            category="endgame",
            level=4,
            difficulty="advanced",
            summary="Master the most important winning rook endgame: building the Lucena bridge.",
            objectives=("Lift the rook to the 4th rank", "Shield your king from checks"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "endgame-philidor-defence",
                "Endgame · Philidor Drawing Technique",
                "black",
                _chain_nodes([
                    (
                        "a2a6",
                        "Hold the 6th rank to stop White's king advancing ahead of the pawn.",
                        "Place your rook on the 6th rank to cut off White's king.",
                    ),
                ]),
                starting_fen="4k3/8/8/3PK3/8/8/r7/5R2 b - - 0 1",
            ),
            category="endgame",
            level=4,
            difficulty="advanced",
            summary="Draw inferior rook-and-pawn endgames using the classic Philidor defence.",
            objectives=("Occupy the third rank first", "Check from behind after pawn push"),
        ),
        LessonEntry(
            lesson=GuidedLesson(
                "endgame-expert-breakthrough",
                "Level 5 Expert · Three-Pawn Breakthrough",
                "white",
                _chain_nodes([
                    (
                        "b5b6",
                        "Sacrifice the central pawn to force an unstoppable passed pawn.",
                        "Push the middle pawn to shatter Black's pawn chain.",
                    ),
                    ("c7b6", "Black captures.", ""),
                    (
                        "a5a6",
                        "Sacrifice again so the remaining c-pawn races cleanly to promotion.",
                        "Push the a-pawn to clear the c-pawn's path.",
                    ),
                ]),
                starting_fen="7k/ppp5/8/PPP5/8/8/8/7K w - - 0 1",
            ),
            category="endgame",
            level=5,
            difficulty="expert",
            summary="Execute the classic 3-vs-3 pawn breakthrough sacrifice to force promotion.",
            objectives=("Calculate forcing pawn sacrifices", "Exploit the rule of the square"),
        ),
    )
    for entry in entries:
        entry.lesson.validate()
    return entries


class CurriculumCatalog:
    """Read-only registry of validated 5-level KnightForge Academy lessons."""

    def __init__(self, entries: tuple[LessonEntry, ...] | None = None) -> None:
        items = _build_entries() if entries is None else entries
        self._by_id: dict[str, LessonEntry] = {}
        for item in items:
            item.lesson.validate()
            if item.lesson.lesson_id in self._by_id:
                raise ValueError(f"Duplicate lesson_id: {item.lesson.lesson_id}")
            self._by_id[item.lesson.lesson_id] = item

    def all(self) -> tuple[LessonEntry, ...]:
        return tuple(self._by_id.values())

    def get(self, lesson_id: str) -> LessonEntry | None:
        return self._by_id.get(lesson_id)

    def filter(
        self,
        *,
        category: str | None = None,
        level: int | None = None,
    ) -> tuple[LessonEntry, ...]:
        result = self.all()
        if category:
            result = tuple(e for e in result if e.category == category)
        if level is not None:
            result = tuple(e for e in result if e.level == level)
        return result
