"""Claim salvage: decompose compound claims. Do not discard fringe claims wholesale."""

from __future__ import annotations

import re

from observer.core import ClaimStatus, EpistemicKind

SPLIT_RE = re.compile(r"\s*(?:;|\band then\b|\band that\b|\. (?=[A-Z]))\s*")


def classify_atomic(text: str) -> ClaimStatus:
    lowered = text.lower()
    if any(w in lowered for w in ("maybe", "might", "perhaps", "rumor", "allegedly")):
        return ClaimStatus.SPECULATIVE
    if any(w in lowered for w in ("secretly controls", "secretly control", "without any evidence")):
        return ClaimStatus.UNVERIFIED
    return ClaimStatus.UNKNOWN


def epistemic_kind(text: str) -> EpistemicKind:
    lowered = text.lower()
    if lowered.startswith("i think") or "in my opinion" in lowered:
        return EpistemicKind.OPINION
    if "allegedly" in lowered or "claimed that" in lowered:
        return EpistemicKind.ALLEGATION
    if lowered.startswith("if ") or "may have" in lowered:
        return EpistemicKind.HYPOTHESIS
    return EpistemicKind.UNKNOWN


def salvage(text: str) -> list[dict]:
    raw = (text or "").strip()
    if not raw:
        return []
    parts = [p.strip(" .") for p in SPLIT_RE.split(raw) if p.strip(" .")]
    if len(parts) <= 1:
        parts = [raw]
    atoms = []
    for part in parts:
        atoms.append(
            {
                "text": part,
                "status": classify_atomic(part).value,
                "epistemic_kind": epistemic_kind(part).value,
            }
        )
    return atoms
