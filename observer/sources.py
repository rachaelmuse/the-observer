"""Source credibility records. Labels are not truth."""

from __future__ import annotations

import uuid
from urllib.parse import urlparse

from observer.core import now
from observer.db import session_scope
from observer.models import SourceRow

HIERARCHY = [
    "primary_record",
    "direct_document",
    "court_record",
    "government_record",
    "corporate_filing",
    "financial_record",
    "original_interview",
    "firsthand_testimony",
    "reputable_secondary_reporting",
    "specialist_analysis",
    "general_reporting",
    "social_media",
    "anonymous_claim",
    "unverified_material",
]


def infer_hierarchy(source_type: str, url: str) -> str:
    st = (source_type or "").lower()
    host = (urlparse(url).hostname or "").lower()
    if st in HIERARCHY:
        return st
    if host.endswith(".gov") or ".gov." in host:
        return "government_record"
    if any(x in host for x in ("sec.gov", "edgar")):
        return "financial_record"
    if any(x in host for x in ("twitter.com", "x.com", "facebook.com", "reddit.com")):
        return "social_media"
    return "general_reporting"


def register_source(
    investigation_id: str,
    *,
    url: str,
    title: str,
    publisher: str,
    content_hash: str,
    source_type: str = "general_reporting",
    author: str = "",
    limitations: str = "",
) -> dict:
    sid = f"src_{uuid.uuid4().hex[:12]}"
    hierarchy = infer_hierarchy(source_type, url)
    retrieved = now()
    with session_scope() as session:
        session.add(
            SourceRow(
                id=sid,
                investigation_id=investigation_id,
                source_identity=publisher or urlparse(url).hostname or "unknown",
                source_type=source_type,
                original_source=url,
                author=author,
                title=title,
                publisher=publisher,
                url=url,
                retrieved_at=retrieved,
                content_hash=content_hash,
                hierarchy=hierarchy,
                limitations=limitations
                or "Hierarchy is a label, not a truth verdict. Primary sources can be false.",
                confidence=0.2 if hierarchy == "general_reporting" else 0.3,
                primary_document_available=bool(content_hash),
            )
        )
    return {
        "id": sid,
        "investigation_id": investigation_id,
        "url": url,
        "title": title,
        "publisher": publisher,
        "hierarchy": hierarchy,
        "content_hash": content_hash,
    }


def list_sources(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(SourceRow)
            .filter(SourceRow.investigation_id == investigation_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "title": r.title,
                "publisher": r.publisher,
                "url": r.url,
                "source_type": r.source_type,
                "hierarchy": r.hierarchy,
                "content_hash": r.content_hash,
                "confidence": r.confidence,
                "limitations": r.limitations,
                "retrieved_at": r.retrieved_at.isoformat(),
            }
            for r in rows
        ]
