"""Public evidence intake. Submission is not verification. Popularity is not proof."""

from __future__ import annotations

import uuid

from observer import audit as audit_mod
from observer.core import content_hash, now
from observer.db import session_scope
from observer.models import PublicSubmissionRow

CLASSIFICATIONS = {
    "EVIDENCE",
    "LEAD",
    "CORRECTION",
    "COMMENTARY",
    "HYPOTHESIS",
    "TESTIMONY",
    "UNKNOWN",
    "CHALLENGE",
}


def submit(
    body: str,
    *,
    classification: str = "UNKNOWN",
    url: str = "",
    investigation_id: str = "",
    kind: str = "submission",
) -> dict:
    text = (body or "").strip()
    if not text:
        raise ValueError("empty submission")
    klass = (classification or "UNKNOWN").upper()
    if klass not in CLASSIFICATIONS:
        klass = "UNKNOWN"
    sid = f"ps_{uuid.uuid4().hex[:12]}"
    digest = content_hash(text)
    stamp = now()
    with session_scope() as session:
        session.add(
            PublicSubmissionRow(
                id=sid,
                created_at=stamp,
                classification=klass,
                status="UNREVIEWED",
                body=text[:8000],
                url=(url or "").strip()[:2000],
                content_hash=digest,
                investigation_id=(investigation_id or "").strip()[:64],
                kind=kind if kind in {"submission", "challenge"} else "submission",
            )
        )
    audit_mod.record("public_submission", target=sid, detail=klass)
    return get_submission(sid)


def get_submission(submission_id: str) -> dict:
    with session_scope() as session:
        row = session.get(PublicSubmissionRow, submission_id)
        if row is None:
            raise KeyError(submission_id)
        return _row(row)


def list_submissions(limit: int = 100) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(PublicSubmissionRow)
            .order_by(PublicSubmissionRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_row(r) for r in rows]


def _row(row: PublicSubmissionRow) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat(),
        "classification": row.classification,
        "status": row.status,
        "body": row.body,
        "url": row.url,
        "content_hash": row.content_hash,
        "investigation_id": row.investigation_id,
        "kind": row.kind,
        "verified": False,
        "note": "UNREVIEWED. A submission is not evidence until independently reviewed.",
    }
