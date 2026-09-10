"""Investigative question engine — uncomfortable questions, not a conclusion engine."""

from __future__ import annotations

CATEGORIES: dict[str, list[str]] = {
    "FACTS": [
        "What actually happened?",
        "What can be independently established?",
        "What is alleged?",
        "What remains unknown?",
    ],
    "PEOPLE": [
        "Who acted?",
        "Who knew?",
        "Who had authority?",
        "Who benefited?",
        "Who suffered?",
        "Who had the ability to prevent it?",
    ],
    "MONEY": [
        "Where did money originate?",
        "Where did it go?",
        "Who financed whom?",
        "Who owns whom?",
        "Who benefits financially?",
        "Who loses financially?",
    ],
    "POWER": [
        "Who had decision-making authority?",
        "Who gained power?",
        "Who lost power?",
        "Who could influence the outcome?",
    ],
    "INCENTIVES": [
        "What incentives existed?",
        "What behavior was rewarded?",
        "What behavior was punished?",
    ],
    "RELATIONSHIPS": [
        "Which people or organizations repeatedly intersect?",
        "Are those relationships documented?",
        "Are they ordinary business relationships or unusual?",
    ],
    "TIMELINE": [
        "What happened first?",
        "What changed immediately afterward?",
        "What happened months or years later?",
    ],
    "INFORMATION": [
        "Who knew?",
        "When did they know?",
        "Who reported it?",
        "Who repeated it?",
        "Who omitted it?",
        "Who corrected it?",
    ],
    "ALTERNATIVE_EXPLANATIONS": [
        "What is the strongest innocent explanation?",
        "What is the strongest non-conspiratorial explanation?",
        "What is the strongest deliberate-coordination explanation?",
        "What evidence distinguishes them?",
    ],
    "INQUIRY": [
        "Who?",
        "What?",
        "When?",
        "Where?",
        "Possible how — mechanism candidate; not fact until tested.",
        "Possible why — in many cases why remains possible, not proven.",
    ],
    "PLACE": [
        "Where did it happen?",
        "Where was it reported?",
        "Where is evidence missing?",
    ],
    "MECHANISM": [
        "How is this possible?",
        "What mechanism is documented vs inferred?",
        "Do not treat possible how as established fact.",
    ],
    "MOTIVE": [
        "Why might this have happened?",
        "In many cases why remains possible, not proven.",
        "What would distinguish motive from coincidence?",
    ],
}


def generate_questions(question: str) -> dict[str, list[str]]:
    _ = (question or "").strip()
    return {category: list(items) for category, items in CATEGORIES.items()}
