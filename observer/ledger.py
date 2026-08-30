"""Evidence ledger. Same-publisher copies are not independent corroboration."""

from __future__ import annotations

import json
import uuid
from urllib.parse import urlparse

from observer.core import EvidenceStatus
from observer.db import session_scope
from observer.models import EvidenceRow, SourceRow


def add_evidence(
    investigation_id: str,
    *,
    source_id: str,
    claim_id: str | None,
    description: str,
    content_hash: str,
    evidence_type: str = "excerpt",
    relevance: float = 0.5,
    reliability: float = 0.3,
) -> dict:
    eid = f"ev_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            EvidenceRow(
                id=eid,
                investigation_id=investigation_id,
                source_id=source_id,
                claim_id=claim_id,
                type=evidence_type,
                description=description[:4000],
                content_hash=content_hash,
                relevance=relevance,
                reliability=reliability,
                corroboration_count=0,
                contradictions="[]",
                confidence=min(relevance, reliability),
                status=EvidenceStatus.UNREVIEWED.value,
            )
        )
    _refresh_corroboration(investigation_id)
    return {"id": eid, "investigation_id": investigation_id, "source_id": source_id, "claim_id": claim_id}


def _refresh_corroboration(investigation_id: str) -> None:
    with session_scope() as session:
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
        by_claim: dict[str, list[EvidenceRow]] = {}
        for ev in evidence:
            key = ev.claim_id or "_none"
            by_claim.setdefault(key, []).append(ev)
        for rows in by_claim.values():
            publishers: dict[str, str] = {}
            independent = 0
            seen_pub: set[str] = set()
            for ev in rows:
                src = sources.get(ev.source_id)
                pub = ""
                if src is not None:
                    pub = (src.publisher or urlparse(src.url).hostname or src.id).lower()
                publishers[ev.id] = pub
                if pub and pub not in seen_pub:
                    seen_pub.add(pub)
                    independent += 1
            for ev in rows:
                ev.corroboration_count = max(0, independent - 1)


def list_evidence(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(EvidenceRow)
            .filter(EvidenceRow.investigation_id == investigation_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "source_id": r.source_id,
                "claim_id": r.claim_id,
                "type": r.type,
                "description": r.description,
                "content_hash": r.content_hash,
                "relevance": r.relevance,
                "reliability": r.reliability,
                "corroboration_count": r.corroboration_count,
                "contradictions": json.loads(r.contradictions or "[]"),
                "confidence": r.confidence,
                "status": r.status,
            }
            for r in rows
        ]
