"""The Observer HTTP API. No Mythos supervisor channel."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from observer import audit as audit_mod
from observer.audit import latest_audit, list_events
from observer.contradictions import list_contradictions
from observer.core import InvestigationStatus, now
from observer.db import init_db, session_scope
from observer.federation_desk import audit_federation_desk
from observer.graph import entity_panel, list_entities, list_relationships
from observer.hypotheses import list_conclusions, list_hypotheses
from observer.identity import identity
from observer.ledger import list_evidence
from observer.models import ClaimRow, EditorialNoteRow, InvestigationRow
from observer.pipeline import create_investigation, run_investigation
from observer.public import list_submissions
from observer.public import submit as submit_public
from observer.registry import list_no_immunity, list_registry, seed_registry
from observer.reports import build_report
from observer.sources import list_sources

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_registry()
    # Ollama extractor seat: only proven live if a real probe succeeds NOW.
    # (docs/unavailable/README.md: 'unproven unless configured and tested')
    try:
        from observer.research.ollama_extractor import probe
        from observer.registry import mark_connected
        import os
        p = probe()
        if p["status"] == "CONNECTED":
            mark_connected(
                "ollama_extractor",
                f"live probe passed: {p.get('reason','')} (OLLAMA_MODEL set)",
            )
    except Exception:
        pass  # stays UNAVAILABLE - never fake it
    yield


app = FastAPI(
    title="The Observer",
    description="Independent investigative intelligence system",
    version="0.1.0",
    lifespan=lifespan,
)


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=800)


class RunRequest(BaseModel):
    question: str = Field(min_length=3, max_length=800)
    urls: list[str] = Field(default_factory=list)
    search: bool = True


class EditorialNoteRequest(BaseModel):
    author: str = "human_editor"
    kind: str = "dissent"
    body: str = Field(min_length=1, max_length=4000)


class HaltRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class PublicSubmissionRequest(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    classification: str = "UNKNOWN"
    url: str = ""
    investigation_id: str = ""
    kind: str = "submission"


@app.get("/health")
def health() -> dict:
    ident = identity()
    return {
        "status": "operational",
        "entity": ident["name"],
        "principle": ident["principle"],
        "never_merge": ident["never_merge"],
    }


@app.get("/registry")
def registry() -> dict:
    return {"capabilities": list_registry(), "no_immunity": list_no_immunity()}


@app.get("/audit")
def audit_history() -> dict:
    return {"events": list_events()}


@app.get("/federation/audit")
def federation_audit() -> dict:
    """Read D:\\Court\\federation. Observer does not own the family."""
    report = audit_federation_desk()
    if not report.get("ok"):
        raise HTTPException(status_code=404, detail=report)
    audit_mod.record(
        "federation_desk",
        actor="the_observer",
        target="federation",
        detail="read-only audit; no ownership",
    )
    return report


@app.post("/investigations")
def post_investigation(request: InvestigationRequest) -> dict:
    return create_investigation(request.question)


@app.post("/investigations/run")
def post_run(request: RunRequest) -> dict:
    return run_investigation(request.question, urls=request.urls, search=request.search)


@app.get("/investigations")
def get_investigations() -> dict:
    with session_scope() as session:
        rows = session.query(InvestigationRow).order_by(InvestigationRow.created_at.desc()).all()
        return {
            "investigations": [
                {
                    "id": r.id,
                    "question": r.question,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in rows
            ]
        }


def _require_inv(investigation_id: str) -> InvestigationRow:
    with session_scope() as session:
        inv = session.get(InvestigationRow, investigation_id)
        if inv is None:
            raise HTTPException(404, "unknown investigation")
        return inv


@app.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: str) -> dict:
    inv = _require_inv(investigation_id)
    with session_scope() as session:
        claims = session.query(ClaimRow).filter(ClaimRow.investigation_id == investigation_id).all()
        claim_payload = [
            {
                "id": c.id,
                "text": c.text,
                "status": c.status,
                "epistemic_kind": c.epistemic_kind,
                "source_ids": json.loads(c.source_ids or "[]"),
                "confidence": c.confidence,
            }
            for c in claims
        ]
    return {
        "id": inv.id,
        "question": inv.question,
        "status": inv.status,
        "created_at": inv.created_at.isoformat(),
        "claims": claim_payload,
        "sources": list_sources(investigation_id),
        "evidence": list_evidence(investigation_id),
        "entities": list_entities(investigation_id),
        "relationships": list_relationships(investigation_id),
        "hypotheses": list_hypotheses(investigation_id),
        "conclusions": list_conclusions(investigation_id),
        "contradictions": list_contradictions(investigation_id),
        "audit": latest_audit(investigation_id),
    }


@app.get("/investigations/{investigation_id}/report")
def get_report(investigation_id: str) -> dict:
    _require_inv(investigation_id)
    return build_report(investigation_id)


@app.get("/investigations/{investigation_id}/entities/{entity_id}")
def get_entity(investigation_id: str, entity_id: str) -> dict:
    _require_inv(investigation_id)
    panel = entity_panel(investigation_id, entity_id)
    if panel.get("error"):
        raise HTTPException(404, panel["error"])
    return panel


@app.post("/investigations/{investigation_id}/editorial_notes")
def post_note(investigation_id: str, request: EditorialNoteRequest) -> dict:
    _require_inv(investigation_id)
    note_id = f"ed_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            EditorialNoteRow(
                id=note_id,
                investigation_id=investigation_id,
                author=request.author,
                kind=request.kind,
                body=request.body,
                created_at=now(),
            )
        )
    audit_mod.record("editorial_note", actor=request.author, target=investigation_id, detail=request.kind)
    return {"id": note_id, "kind": request.kind}


@app.post("/investigations/{investigation_id}/halt")
def post_halt(investigation_id: str, request: HaltRequest) -> dict:
    with session_scope() as session:
        inv = session.get(InvestigationRow, investigation_id)
        if inv is None:
            raise HTTPException(404, "unknown investigation")
        if inv.status == InvestigationStatus.PUBLISHED.value:
            inv.status = InvestigationStatus.RETRACTED.value
        else:
            inv.status = InvestigationStatus.EDITORIAL_REVIEW.value
        inv.updated_at = now()
    audit_mod.record("halt", actor="human_editor", target=investigation_id, detail=request.reason)
    return {"id": investigation_id, "halted": True, "reason": request.reason}


@app.get("/public/submissions")
def get_public_submissions() -> dict:
    return {"submissions": list_submissions(), "note": "UNREVIEWED is not verified evidence."}


@app.post("/public/submissions")
def post_public_submission(request: PublicSubmissionRequest) -> dict:
    try:
        return submit_public(
            request.body,
            classification=request.classification,
            url=request.url,
            investigation_id=request.investigation_id,
            kind=request.kind,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/investigations/{investigation_id}/publish")
def post_publish(investigation_id: str) -> dict:
    _require_inv(investigation_id)
    raise HTTPException(
        403,
        "auto_publish is DISABLED. A human editor cannot publish through this API in slice 1.",
    )


if DASHBOARD.is_dir():
    app.mount("/static", StaticFiles(directory=str(DASHBOARD)), name="static")

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(DASHBOARD / "index.html")
