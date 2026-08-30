"""Contradiction engine. Suspicion is not evidence; conflict is recorded, not resolved."""

from __future__ import annotations

import json
import re
import uuid
from urllib.parse import urlparse

from observer import audit as audit_mod
from observer.core import ClaimStatus, EvidenceStatus
from observer.db import session_scope
from observer.models import ClaimRow, ContradictionRow, EvidenceRow, HypothesisRow, SourceRow

STOP = {
    "a",
    "an",
    "the",
    "of",
    "to",
    "and",
    "or",
    "in",
    "on",
    "for",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "it",
    "this",
    "that",
    "with",
    "by",
    "from",
    "as",
    "at",
    "into",
}
NEGATION = re.compile(
    r"\b(not|never|no|cannot|can't|didn't|doesn't|don't|did not|does not|do not)\b",
    re.I,
)


def _stem(word: str) -> str:
    w = word.lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5:
        return w[:-3]
    if w.endswith("ed") and len(w) > 4:
        return w[:-2]
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
        return w[:-1]
    return w


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for w in words:
        if w in STOP or NEGATION.fullmatch(w):
            continue
        out.add(_stem(w))
    return out


def _polarity(text: str) -> str:
    return "neg" if NEGATION.search(text or "") else "pos"


def detect_pair(text_a: str, text_b: str) -> dict | None:
    a = (text_a or "").strip()
    b = (text_b or "").strip()
    if not a or not b:
        return None
    if a.lower() == b.lower():
        return None
    if _polarity(a) == _polarity(b):
        return None
    overlap = _tokens(a) & _tokens(b)
    if len(overlap) >= 2 or any(len(t) >= 5 for t in overlap):
        return {"kind": "negation_polarity", "overlap": sorted(overlap)}
    return None


def _publisher_for_claim(claim: ClaimRow, sources: dict[str, SourceRow]) -> str:
    ids = json.loads(claim.source_ids or "[]")
    for sid in ids:
        src = sources.get(sid)
        if src is None:
            continue
        return (src.publisher or urlparse(src.url).hostname or src.id).lower()
    return ""


def _evidence_for_claim(claim_id: str, evidence: list[EvidenceRow]) -> EvidenceRow | None:
    for ev in evidence:
        if ev.claim_id == claim_id:
            return ev
    return None


def _append_id(raw: str, item_id: str) -> str:
    items = json.loads(raw or "[]")
    if item_id not in items:
        items.append(item_id)
    return json.dumps(items)


def scan_investigation(investigation_id: str) -> list[dict]:
    created: list[dict] = []
    with session_scope() as session:
        claims = (
            session.query(ClaimRow)
            .filter(ClaimRow.investigation_id == investigation_id)
            .all()
        )
        sources = {
            s.id: s
            for s in session.query(SourceRow)
            .filter(SourceRow.investigation_id == investigation_id)
            .all()
        }
        evidence = (
            session.query(EvidenceRow)
            .filter(EvidenceRow.investigation_id == investigation_id)
            .all()
        )
        existing = {
            tuple(sorted((r.claim_a_id, r.claim_b_id)))
            for r in session.query(ContradictionRow)
            .filter(ContradictionRow.investigation_id == investigation_id)
            .all()
        }
        for i, left in enumerate(claims):
            for right in claims[i + 1 :]:
                key = tuple(sorted((left.id, right.id)))
                if key in existing:
                    continue
                hit = detect_pair(left.text, right.text)
                if hit is None:
                    continue
                pub_a = _publisher_for_claim(left, sources)
                pub_b = _publisher_for_claim(right, sources)
                same_pub = bool(pub_a and pub_b and pub_a == pub_b)
                independent = bool(pub_a and pub_b and not same_pub)
                ev_a = _evidence_for_claim(left.id, evidence)
                ev_b = _evidence_for_claim(right.id, evidence)
                cid = f"cx_{uuid.uuid4().hex[:12]}"
                reason = (
                    "Negation polarity over shared content. "
                    + (
                        "Same-publisher conflict is not independent corroboration or independent dispute."
                        if same_pub
                        else "Independent publishers disagree; neither claim is established."
                    )
                )
                session.add(
                    ContradictionRow(
                        id=cid,
                        investigation_id=investigation_id,
                        claim_a_id=left.id,
                        claim_b_id=right.id,
                        evidence_a_id=ev_a.id if ev_a else None,
                        evidence_b_id=ev_b.id if ev_b else None,
                        kind=hit["kind"],
                        reason=reason,
                        overlap=json.dumps(hit["overlap"]),
                        independent=independent,
                        same_publisher=same_pub,
                        publisher_a=pub_a,
                        publisher_b=pub_b,
                    )
                )
                left.status = ClaimStatus.CONTRADICTED.value
                right.status = ClaimStatus.CONTRADICTED.value
                left.contradictions = _append_id(left.contradictions, cid)
                right.contradictions = _append_id(right.contradictions, cid)
                if ev_a:
                    ev_a.contradictions = _append_id(ev_a.contradictions, cid)
                    ev_a.status = EvidenceStatus.CONTESTED.value
                if ev_b:
                    ev_b.contradictions = _append_id(ev_b.contradictions, cid)
                    ev_b.status = EvidenceStatus.CONTESTED.value
                existing.add(key)
                created.append(
                    {
                        "id": cid,
                        "claim_a_id": left.id,
                        "claim_b_id": right.id,
                        "independent": independent,
                        "same_publisher": same_pub,
                        "kind": hit["kind"],
                        "reason": reason,
                    }
                )
        hyps = (
            session.query(HypothesisRow)
            .filter(HypothesisRow.investigation_id == investigation_id)
            .all()
        )
        for hyp in hyps:
            contra_ids = [row["id"] for row in created]
            if not contra_ids:
                continue
            current = json.loads(hyp.contradictory_evidence or "[]")
            for cid in contra_ids:
                if cid not in current:
                    current.append(cid)
            hyp.contradictory_evidence = json.dumps(current)
    if created:
        audit_mod.record(
            "contradictions_recorded",
            target=investigation_id,
            detail=f"count={len(created)}",
        )
    return created


def list_contradictions(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(ContradictionRow)
            .filter(ContradictionRow.investigation_id == investigation_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "claim_a_id": r.claim_a_id,
                "claim_b_id": r.claim_b_id,
                "evidence_a_id": r.evidence_a_id,
                "evidence_b_id": r.evidence_b_id,
                "kind": r.kind,
                "reason": r.reason,
                "overlap": json.loads(r.overlap or "[]"),
                "independent": r.independent,
                "same_publisher": r.same_publisher,
                "publisher_a": r.publisher_a,
                "publisher_b": r.publisher_b,
            }
            for r in rows
        ]
