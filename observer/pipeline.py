"""Vertical-slice orchestrator: question → search → source → claims → graph → hypotheses → audit → report."""

from __future__ import annotations

import json
import uuid

from observer import audit as audit_mod
from observer.contradictions import scan_investigation
from observer.core import ClaimStatus, InvestigationStatus, now
from observer.db import session_scope
from observer.extractors import extract_from_document
from observer.graph import add_relationship, upsert_entity
from observer.hypotheses import append_conclusion, build_competing_hypotheses
from observer.ledger import add_evidence
from observer.models import ClaimRow, InvestigationRow, ResearchRecordRow
from observer.policy import PolicyDenied
from observer.questions import generate_questions
from observer.reports import build_report
from observer.research.corporate import CorporateRegistriesAdapter
from observer.research.court import CourtRecordsAdapter
from observer.research.http_fetch import HttpFetchAdapter
from observer.research.patents import PatentsAdapter
from observer.research.procurement import ProcurementAdapter
from observer.research.sec import SecFilingsAdapter
from observer.research.url_intake import UrlIntakeAdapter
from observer.research.wayback import WaybackAdapter, _is_archive_host
from observer.research.web_search import WebSearchAdapter
from observer.salvage import salvage
from observer.sources import register_source

fetcher = HttpFetchAdapter()
searcher = WebSearchAdapter()
intake = UrlIntakeAdapter()
archiver = WaybackAdapter()
courts = CourtRecordsAdapter()
corporates = CorporateRegistriesAdapter()
filings = SecFilingsAdapter()
patents = PatentsAdapter()
procurement = ProcurementAdapter()


def create_investigation(question: str) -> dict:
    iid = f"inv_{uuid.uuid4().hex[:12]}"
    stamp = now()
    with session_scope() as session:
        session.add(
            InvestigationRow(
                id=iid,
                question=(question or "").strip()[:800],
                status=InvestigationStatus.INTAKE.value,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    audit_mod.record("investigation_started", target=iid, detail=question[:500])
    return {
        "id": iid,
        "question": (question or "").strip()[:800],
        "status": InvestigationStatus.INTAKE.value,
        "created_at": stamp.isoformat(),
        "questions": generate_questions(question),
    }


def _set_status(investigation_id: str, status: InvestigationStatus) -> None:
    with session_scope() as session:
        inv = session.get(InvestigationRow, investigation_id)
        if inv is None:
            raise KeyError(investigation_id)
        inv.status = status.value
        inv.updated_at = now()


def _add_claim(investigation_id: str, text: str, source_id: str | None, status: str) -> str:
    atoms = salvage(text)
    first_id = ""
    parent_id = None
    with session_scope() as session:
        for atom in atoms:
            cid = f"cl_{uuid.uuid4().hex[:12]}"
            if not first_id:
                first_id = cid
            session.add(
                ClaimRow(
                    id=cid,
                    investigation_id=investigation_id,
                    text=atom["text"],
                    status=atom.get("status") or status,
                    parent_id=parent_id,
                    source_ids=json.dumps([source_id] if source_id else []),
                    contradictions="[]",
                    epistemic_kind=atom.get("epistemic_kind") or "unknown",
                    confidence=0.2,
                )
            )
            parent_id = first_id if len(atoms) > 1 else None
    return first_id


def _archive_record(investigation_id: str, query: str, fetched: dict, extracted: dict, source_id: str) -> str:
    rid = f"rr_{uuid.uuid4().hex[:12]}"
    stamp = now()
    with session_scope() as session:
        session.add(
            ResearchRecordRow(
                id=rid,
                investigation_id=investigation_id,
                timestamp=stamp,
                query=query,
                url=fetched["url"],
                title=extracted.get("title") or "",
                publisher=extracted.get("publisher") or "",
                content_hash=fetched["content_hash"],
                retrieval_date=stamp,
                excerpt=extracted.get("excerpt") or "",
                facts_json=json.dumps(extracted.get("facts") or []),
                claims_json=json.dumps(extracted.get("claims") or []),
                entities_json=json.dumps(extracted.get("entities") or []),
                relationships_json=json.dumps(extracted.get("relationships") or []),
                confidence=0.2,
                verification_state="unreviewed",
                archive_path=fetched.get("archive_path") or "",
            )
        )
    audit_mod.record("research_record", target=rid, detail=fetched["url"])
    return rid


def _ingest_url(
    investigation_id: str,
    url: str,
    query: str,
    *,
    source_type: str = "general_reporting",
    limitations: str = "",
) -> dict | None:
    try:
        fetched = fetcher.fetch(url)
    except PolicyDenied as exc:
        audit_mod.record("fetch_denied", target=investigation_id, detail=str(exc))
        return {"url": url, "denied": True, "reason": str(exc)}
    except Exception as exc:
        audit_mod.record("fetch_failed", target=investigation_id, detail=str(exc))
        return {"url": url, "failed": True, "reason": str(exc)}

    extracted = extract_from_document(fetched["text"], fetched["url"])
    archival = "web.archive.org" in (fetched["url"] or "")
    stype = source_type if not archival else "archived_webpage"
    limits = limitations
    if archival and not limits:
        limits = (
            "Archival copy from the Internet Archive. "
            "A snapshot is not proof the original is unchanged, and archive.org is not the speaker."
        )
    source = register_source(
        investigation_id,
        url=fetched["url"],
        title=extracted["title"],
        publisher=extracted["publisher"],
        content_hash=fetched["content_hash"],
        source_type=stype,
        limitations=limits,
    )
    _archive_record(investigation_id, query, fetched, extracted, source["id"])
    claim_id = None
    for atom in extracted["claims"][:8]:
        claim_id = _add_claim(
            investigation_id,
            atom["text"],
            source["id"],
            atom.get("status") or ClaimStatus.UNVERIFIED.value,
        )
        add_evidence(
            investigation_id,
            source_id=source["id"],
            claim_id=claim_id,
            description=atom["text"][:500],
            content_hash=fetched["content_hash"],
        )
    name_to_id: dict[str, str] = {}
    for ent in extracted["entities"]:
        saved = upsert_entity(investigation_id, ent["name"], ent["entity_type"])
        name_to_id[ent["name"]] = saved["id"]
    for rel in extracted["relationships"]:
        a = name_to_id.get(rel["from_name"])
        b = name_to_id.get(rel["to_name"])
        if a and b:
            add_relationship(
                investigation_id,
                from_entity=a,
                to_entity=b,
                rel_type=rel["rel_type"],
                provenance_source_id=source["id"],
                inferred=bool(rel.get("inferred")),
                notes=rel.get("notes") or "",
            )
    return {"url": fetched["url"], "source_id": source["id"], "content_hash": fetched["content_hash"]}


def run_investigation(
    question: str,
    *,
    urls: list[str] | None = None,
    search: bool = True,
    investigation_id: str | None = None,
) -> dict:
    created = None
    if investigation_id:
        iid = investigation_id
    else:
        created = create_investigation(question)
        iid = created["id"]

    _set_status(iid, InvestigationStatus.RESEARCH)
    search_hits: list[dict] = []
    court_hits: list[dict] = []
    corporate_hits: list[dict] = []
    filing_hits: list[dict] = []
    patent_hits: list[dict] = []
    procurement_hits: list[dict] = []
    if search:
        search_hits = searcher.search(question, limit=3)
        audit_mod.record("web_search", target=iid, detail=json.dumps(search_hits)[:1500])
        court_hits = courts.search(question, limit=2)
        audit_mod.record("court_search", target=iid, detail=json.dumps(court_hits)[:1500])
        corporate_hits = corporates.search(question, limit=1)
        audit_mod.record("corporate_search", target=iid, detail=json.dumps(corporate_hits)[:1500])
        filing_hits = filings.search(question, limit=1)
        audit_mod.record("sec_search", target=iid, detail=json.dumps(filing_hits)[:1500])
        patent_hits = patents.search(question, limit=1)
        audit_mod.record("patent_search", target=iid, detail=json.dumps(patent_hits)[:1500])
        procurement_hits = procurement.search(question, limit=1)
        audit_mod.record("procurement_search", target=iid, detail=json.dumps(procurement_hits)[:1500])

    candidate_urls: list[str] = []
    url_meta: dict[str, dict] = {}
    if urls:
        try:
            candidate_urls.extend(intake.intake(urls))
        except PolicyDenied as exc:
            audit_mod.record("url_intake_denied", target=iid, detail=str(exc))
    for hit in search_hits:
        if hit.get("failed") or not hit.get("url"):
            continue
        candidate_urls.append(hit["url"])
    for hit in court_hits:
        if hit.get("failed") or not hit.get("url"):
            continue
        candidate_urls.append(hit["url"])
        url_meta[hit["url"]] = {
            "source_type": hit.get("source_type") or "court_record",
            "limitations": hit.get("limitations") or "",
        }
    for hit in corporate_hits:
        if hit.get("failed") or not hit.get("url"):
            continue
        candidate_urls.append(hit["url"])
        url_meta[hit["url"]] = {
            "source_type": hit.get("source_type") or "corporate_filing",
            "limitations": hit.get("limitations") or "",
        }
    for hit in filing_hits:
        if hit.get("failed") or not hit.get("url"):
            continue
        candidate_urls.append(hit["url"])
        url_meta[hit["url"]] = {
            "source_type": hit.get("source_type") or "financial_record",
            "limitations": hit.get("limitations") or "",
        }
    for hit in patent_hits:
        if hit.get("failed") or not hit.get("url"):
            continue
        candidate_urls.append(hit["url"])
        url_meta[hit["url"]] = {
            "source_type": hit.get("source_type") or "government_record",
            "limitations": hit.get("limitations") or "",
        }
    for hit in procurement_hits:
        if hit.get("failed") or not hit.get("url"):
            continue
        candidate_urls.append(hit["url"])
        url_meta[hit["url"]] = {
            "source_type": hit.get("source_type") or "government_record",
            "limitations": hit.get("limitations") or "",
        }

    # Deduplicate, keep order, cap fetches.
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in candidate_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
        if len(unique_urls) >= 10:
            break

    ingested = []
    _set_status(iid, InvestigationStatus.EVIDENCE_COLLECTION)
    for url in unique_urls:
        meta = url_meta.get(url) or {}
        result = _ingest_url(
            iid,
            url,
            question,
            source_type=meta.get("source_type") or "general_reporting",
            limitations=meta.get("limitations") or "",
        )
        if result:
            ingested.append(result)
        if _is_archive_host(url):
            continue
        archive_hits = archiver.search(url, limit=1)
        audit_mod.record("wayback_lookup", target=iid, detail=json.dumps(archive_hits)[:1500])
        for hit in archive_hits:
            if hit.get("failed") or not hit.get("url"):
                continue
            snap = hit["url"]
            if snap in seen:
                continue
            seen.add(snap)
            archived = _ingest_url(iid, snap, question)
            if archived:
                archived["archival"] = True
                ingested.append(archived)

    _set_status(iid, InvestigationStatus.ENTITY_RESOLUTION)
    _set_status(iid, InvestigationStatus.RELATIONSHIP_MAPPING)
    _set_status(iid, InvestigationStatus.HYPOTHESIS_FORMATION)
    hyps = build_competing_hypotheses(iid, question)
    contradictions = scan_investigation(iid)
    _set_status(iid, InvestigationStatus.ADVERSARIAL_REVIEW)
    review = audit_mod.adversarial_review(iid)

    thin = not any(item.get("source_id") for item in ingested)
    conclusion = "Insufficient evidence." if thin else (
        "Sources were retrieved and competing hypotheses recorded. "
        "The evidence does not establish a coordinated conclusion."
    )
    append_conclusion(iid, conclusion)
    _set_status(iid, InvestigationStatus.FACT_CHECK)
    report = build_report(iid)
    audit_mod.record("pipeline_complete", target=iid, detail=conclusion)
    return {
        "investigation": created or {"id": iid, "question": question},
        "search_hits": search_hits,
        "court_hits": court_hits,
        "corporate_hits": corporate_hits,
        "filing_hits": filing_hits,
        "patent_hits": patent_hits,
        "procurement_hits": procurement_hits,
        "ingested": ingested,
        "hypotheses": hyps,
        "contradictions": contradictions,
        "audit": review,
        "report": report,
    }
