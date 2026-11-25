"""KnightForge-authored London and Jobava London repertoire courses.

The move paths are deliberately treated as draft curriculum: OpeningTree.validate()
checks every branch against python-chess before the courses are exposed by the API.
"""
from __future__ import annotations

from .opening_tree import OpeningTree, VariationNode

# UCI paths are White's repertoire against representative Black setups. Each
# branch reaches a playable middlegame structure; it is not a forced game-to-mate.
_LONDON_LINES = (
    (
        "d2d4 d7d5 g1f3 g8f6 c1f4 e7e6 e2e3 f8d6 f1d3 e8g8 e1g1 c7c5 "
        "c2c3 b8c6 b1d2 b7b6"
    , "Classical ...e6 setup"),
    (
        "d2d4 d7d5 g1f3 g8f6 c1f4 c7c5 e2e3 b8c6 c2c3 e7e6 b1d2 f8d6 "
        "f1d3 e8g8 e1g1"
    , "Early ...c5 challenge"),
    (
        "d2d4 d7d5 g1f3 g8f6 c1f4 e7e6 e2e3 c7c5 c2c3 b8c6 b1d2 "
        "f8d6 f1d3 e8g8 e1g1"
    , "Symmetrical central pressure"),
)
_JOBAVA_LINES = (
    (
        "d2d4 d7d5 b1c3 g8f6 c1f4 e7e6 e2e3 f8d6 d1f3 e8g8 "
        "e1c1 c7c5 c3b5 d6f4 f3f4 b8a6 g1f3"
    , "Main Jobava plan: Qf3 and long castling"),
    (
        "d2d4 d7d5 b1c3 g8f6 c1f4 e7e6 e2e3 f8d6 d1f3 e8g8 "
        "e1c1 c7c5 c3b5 d6f4 f3f4 b8a6"
    , "Pressure on c7 and queenside"),
)
_EXPLANATIONS = {
    "d2d4": "Claim central space and open lines for the dark-squared bishop.",
    "b1c3": "Develop the b1-knight to c3: the defining Jobava move order.",
    "g1f3": "Develop toward the centre and support e5 and d4.",
    "c1f4": "Develop the London bishop outside the pawn chain before ...e6.",
    "e2e3": "Build a stable centre and free the f1-bishop.",
    "c2c3": "Support d4 and prepare a reliable central structure.",
    "f1d3": "Point the bishop toward the kingside and support a future e4 break.",
    "d1f3": "The Jobava queen move supports pressure on the kingside and helps prepare long castling.",
    "e1c1": "Castle long only after d1, c1 and b1 have been cleared.",
    "c3b5": "Use the advanced knight to create pressure on c7 and d6.",
    "d6f4": "Black exchanges the active bishop for White's London bishop.",
    "f3f4": "Recapture with the queen and keep active central influence.",
    "g1f3": "Complete development and prepare to coordinate the rooks.",
    "e1g1": "Castle kingside and connect the rooks.",
    "c7c5": "Black challenges White's central pawn chain immediately.",
    "b8c6": "Develop and increase pressure on d4.",
    "b7b6": "Prepare ...Bb7 and add pressure to the central dark squares.",
}

def _tree(lines: tuple[tuple[str, str], ...]) -> tuple[VariationNode, ...]:
    roots: dict[str, dict] = {}
    for raw_path, label in lines:
        cursor = roots
        path = raw_path.split()
        for index, move in enumerate(path):
            node = cursor.setdefault(move, {
                "move_uci": move, "label": "", "explanation": _EXPLANATIONS.get(move, ""),
                "children": {},
            })
            if index == len(path) - 1:
                node["label"] = label
            cursor = node["children"]

    def freeze(nodes: dict[str, dict]) -> tuple[VariationNode, ...]:
        return tuple(
            VariationNode(
                move_uci=item["move_uci"],
                label=item["label"],
                explanation=item["explanation"],
                children=freeze(item["children"]),
            )
            for item in nodes.values()
        )
    return freeze(roots)


def london_jobava_courses() -> tuple[OpeningTree, OpeningTree]:
    """Return two legally validated White repertoires with labelled branches."""
    courses = (
        OpeningTree(
            opening_id="london-system",
            name="London System",
            side="white",
            eco="D00",
            aliases=("London", "London System repertoire"),
            source_name="KnightForge original educational curriculum",
            license_name="KnightForge original draft; editorial review pending",
            review_status="in_review",
            roots=_tree(_LONDON_LINES),
        ),
        OpeningTree(
            opening_id="jobava-london",
            name="Jobava London System",
            side="white",
            eco="D00",
            aliases=("Jobava London", "Jobava-Prié Attack"),
            source_name="KnightForge original educational curriculum",
            license_name="KnightForge original draft; editorial review pending",
            review_status="in_review",
            roots=_tree(_JOBAVA_LINES),
        ),
    )
    for course in courses:
        course.validate()
    return courses
