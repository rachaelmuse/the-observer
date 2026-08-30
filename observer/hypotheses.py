"""Competing hypotheses. A counter-hypothesis is required."""

from __future__ import annotations

import json
import uuid

from observer.core import now
from observer.db import session_scope
from observer.human_nature import dual_explanations
from observer.models import ConclusionRow, HypothesisRow, InvestigationRow


def build_competing_hypotheses(investigation_id: str, question: str) -> list[dict]:
    dual = dual_explanations(question)
    specs = [
        {
            "text": "Deliberate coordination may explain the observed pattern.",
            "falsification": [
                "Independent evidence demonstrates that the apparent coordination "
                "is better explained by unrelated actors."
            ],
            "is_counter": False,
        },
        {
            "text": "Independent actors may be responding to the same incentives.",
            "falsification": [
                "Direct evidence establishes coordinated planning or communication."
            ],
            "is_counter": False,
        },
        {
            "text": dual["ordinary_explanation"],
            "falsification": [
                "Evidence demonstrates behavior inconsistent with ordinary incentives."
            ],
            "is_counter": False,
        },
        {
            "text": "The apparent pattern may be coincidental or caused by incomplete data.",
            "falsification": [
                "Independent datasets reproduce the same relationship with strong evidence."
            ],
            "is_counter": True,
        },
    ]
    created: list[dict] = []
    with session_scope() as session:
        for i, spec in enumerate(specs, start=1):
            hid = f"{investigation_id}-H{i}"
            session.add(
                HypothesisRow(
                    id=hid,
                    investigation_id=investigation_id,
                    text=spec["text"],
                    supporting_evidence="[]",
                    contradictory_evidence="[]",
                    missing_evidence=json.dumps(
                        ["Independent corroboration from a second publisher is missing."]
                    ),
                    predictions="[]",
                    confidence=0.0,
                    falsification_conditions=json.dumps(spec["falsification"]),
                    is_counter=spec["is_counter"],
                )
            )
            created.append(
                {
                    "id": hid,
                    "text": spec["text"],
                    "is_counter": spec["is_counter"],
                    "falsification_conditions": spec["falsification"],
                }
            )
    return created


def list_hypotheses(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(HypothesisRow)
            .filter(HypothesisRow.investigation_id == investigation_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "text": r.text,
                "supporting_evidence": json.loads(r.supporting_evidence or "[]"),
                "contradictory_evidence": json.loads(r.contradictory_evidence or "[]"),
                "missing_evidence": json.loads(r.missing_evidence or "[]"),
                "predictions": json.loads(r.predictions or "[]"),
                "confidence": r.confidence,
                "falsification_conditions": json.loads(r.falsification_conditions or "[]"),
                "is_counter": r.is_counter,
            }
            for r in rows
        ]


def append_conclusion(investigation_id: str, body: str) -> dict:
    with session_scope() as session:
        existing = (
            session.query(ConclusionRow)
            .filter(ConclusionRow.investigation_id == investigation_id)
            .all()
        )
        version = len(existing) + 1
        cid = f"con_{uuid.uuid4().hex[:12]}"
        session.add(
            ConclusionRow(
                id=cid,
                investigation_id=investigation_id,
                version=version,
                body=body,
                created_at=now(),
            )
        )
        inv = session.get(InvestigationRow, investigation_id)
        if inv is not None:
            inv.updated_at = now()
        return {"id": cid, "version": version, "body": body}


def list_conclusions(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(ConclusionRow)
            .filter(ConclusionRow.investigation_id == investigation_id)
            .order_by(ConclusionRow.version)
            .all()
        )
        return [
            {
                "id": r.id,
                "version": r.version,
                "body": r.body,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
