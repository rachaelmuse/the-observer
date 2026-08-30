"""Ordinary human mechanisms vs deliberate-manipulation hypotheses.

These mechanisms are not evidence of conspiracy.
"""

from __future__ import annotations

MECHANISMS = [
    "fear",
    "survival instincts",
    "tribalism",
    "loyalty",
    "status",
    "greed",
    "jealousy",
    "territorial behavior",
    "family protection",
    "revenge",
    "humiliation",
    "social conformity",
    "authority obedience",
    "scarcity",
    "competition",
    "belonging",
    "scapegoating",
    "dehumanization",
    "confirmation bias",
    "motivated reasoning",
    "group polarization",
    "moral outrage",
    "retaliation",
]


def dual_explanations(question: str) -> dict:
    q = (question or "").strip() or "the observed behavior"
    return {
        "mechanisms_considered": list(MECHANISMS),
        "ordinary_explanation": (
            f"What normal human explanation could account for this? "
            f"Incentives, fear, status, loyalty, conformity, or ordinary institutional inertia "
            f"could produce the pattern described in: {q}"
        ),
        "manipulation_hypothesis": (
            f"What deliberate manipulation hypothesis could account for it? "
            f"Coordinated messaging, concealed control, or engineered scapegoating "
            f"could produce the pattern described in: {q}"
        ),
        "rule": (
            "Compare both. Do not treat ordinary human mechanisms as proof of conspiracy. "
            "Suspicion is not evidence."
        ),
    }
