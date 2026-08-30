"""Append-only mutation log and 12-question adversarial audit."""

from __future__ import annotations

import json
import uuid

from observer.core import now
from observer.db import session_scope
from observer.models import AuditEventRow, AuditRow, EvidenceRow, HypothesisRow

AUDIT_QUESTIONS = [
    "What assumptions did we make?",
    "What evidence did we fail to investigate?",
    "What evidence contradicts us?",
    "Did we mistake correlation for causation?",
    "Did we infer intent without evidence?",
    "Did we overvalue a primary source?",
    "Did we overvalue an official source?",
    "Did we dismiss an inconvenient source merely because it is unpopular?",
    "Did we treat a popular source as credible merely because it is popular?",
    "Could an ordinary explanation account for the evidence?",
    "What would falsify our conclusion?",
    "Are we accidentally creating a narrative rather than reporting evidence?",
]


def record(action: str, *, actor: str = "observer", target: str = "", detail: str = "") -> dict:
    event_id = f"ae_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            AuditEventRow(
                id=event_id,
                created_at=now(),
                actor=actor,
                action=action,
                target=target,
                detail=detail[:4000],
            )
        )
    return {"id": event_id, "action": action, "target": target}


def list_events(limit: int = 200) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(AuditEventRow)
            .order_by(AuditEventRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "actor": r.actor,
                "action": r.action,
                "target": r.target,
                "detail": r.detail,
            }
            for r in rows
        ]


def adversarial_review(investigation_id: str) -> dict:
    warnings: list[str] = []
    answers: dict[str, str] = {}

    with session_scope() as session:
        evidence = (
            session.query(EvidenceRow)
            .filter(EvidenceRow.investigation_id == investigation_id)
            .all()
        )
        hypotheses = (
            session.query(HypothesisRow)
            .filter(HypothesisRow.investigation_id == investigation_id)
            .all()
        )

        if not evidence:
            warnings.append(
                "No evidence has been collected. Investigation cannot support a substantive conclusion."
            )
        for hyp in hypotheses:
            conditions = json.loads(hyp.falsification_conditions or "[]")
            if not conditions:
                warnings.append(f"{hyp.id}: missing falsification criteria.")
            if not json.loads(hyp.contradictory_evidence or "[]") and evidence:
                warnings.append(
                    f"{hyp.id}: Examiner found no contradictory evidence recorded. "
                    "Absence of recorded contradiction is not proof."
                )

        # Same-publisher copies are not independent corroboration — flagged in ledger,
        # restated here so the audit cannot ignore it.
        if len(evidence) >= 2:
            warnings.append(
                "Corroboration must be independent. Same-publisher copies are not independent."
            )

        answers[AUDIT_QUESTIONS[0]] = (
            "Assumed retrieved public pages are authentic copies of what the publisher presented, "
            "not that the publisher is correct."
        )
        answers[AUDIT_QUESTIONS[1]] = (
            "CourtListener opinions, GLEIF LEI records, SEC EDGAR copies, USPTO patent PDFs, "
            "and USAspending awards are queried when search is on and the question matches that desk. "
            "PACER login dockets remain forbidden. Four independent model reviewers are UNAVAILABLE. "
            "Wayback snapshots are queried for ingested public URLs; a snapshot is not independent corroboration of the live page."
        )
        answers[AUDIT_QUESTIONS[2]] = (
            "See contradictory_evidence on each hypothesis; empty lists are a warning, not a clearance."
        )
        answers[AUDIT_QUESTIONS[3]] = (
            "Co-occurrence in text is not causation. Relationships without inferred=false provenance "
            "must not be treated as documented control."
        )
        answers[AUDIT_QUESTIONS[4]] = (
            "Intent is not inferred from ordinary incentives alone."
        )
        answers[AUDIT_QUESTIONS[5]] = "Primary labels are not automatic truth."
        answers[AUDIT_QUESTIONS[6]] = "Official sources can be wrong."
        answers[AUDIT_QUESTIONS[7]] = "Unpopular sources were not auto-discarded; they remain UNVERIFIED until corroborated."
        answers[AUDIT_QUESTIONS[8]] = "Popularity is not credibility."
        answers[AUDIT_QUESTIONS[9]] = "Human-nature ordinary explanation is required alongside any manipulation hypothesis."
        answers[AUDIT_QUESTIONS[10]] = (
            "; ".join(
                json.loads(h.falsification_conditions or "[]")[0]
                for h in hypotheses
                if json.loads(h.falsification_conditions or "[]")
            )
            or "No falsification conditions recorded."
        )
        answers[AUDIT_QUESTIONS[11]] = (
            "Report sections keep FACT/ANALYSIS/HYPOTHESIS separate. Default conclusion is insufficient evidence."
        )

        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        session.add(
            AuditRow(
                id=audit_id,
                investigation_id=investigation_id,
                checklist_json=json.dumps(answers),
                warnings_json=json.dumps(warnings),
                created_at=now(),
            )
        )

    record("adversarial_review", target=investigation_id, detail=f"warnings={len(warnings)}")
    return {"id": audit_id, "investigation_id": investigation_id, "answers": answers, "warnings": warnings}


def latest_audit(investigation_id: str) -> dict | None:
    with session_scope() as session:
        row = (
            session.query(AuditRow)
            .filter(AuditRow.investigation_id == investigation_id)
            .order_by(AuditRow.created_at.desc())
            .first()
        )
        if row is None:
            return None
        return {
            "id": row.id,
            "investigation_id": row.investigation_id,
            "answers": json.loads(row.checklist_json or "{}"),
            "warnings": json.loads(row.warnings_json or "[]"),
            "created_at": row.created_at.isoformat(),
        }
