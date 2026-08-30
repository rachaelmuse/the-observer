import json
import uuid

from observer.contradictions import detect_pair, list_contradictions, scan_investigation
from observer.core import ClaimStatus, InvestigationStatus, now
from observer.db import session_scope
from observer.ledger import add_evidence, list_evidence
from observer.models import ClaimRow, InvestigationRow
from observer.sources import register_source


def test_detect_pair_finds_negation_polarity():
    hit = detect_pair(
        "Organization X secretly controls Organization Y.",
        "Organization X does not control Organization Y.",
    )
    assert hit is not None
    assert hit["kind"] == "negation_polarity"
    assert "organization" in hit["overlap"] or "control" in hit["overlap"]


def test_detect_pair_ignores_unrelated_and_restatements():
    assert detect_pair("It rained in March.", "They never arrived on time.") is None
    assert detect_pair("The board resigned today.", "The board resigned today.") is None


def _inv_with_claims(claim_a: str, claim_b: str, pub_a: str, pub_b: str) -> str:
    iid = f"inv_{uuid.uuid4().hex[:10]}"
    stamp = now()
    with session_scope() as session:
        session.add(
            InvestigationRow(
                id=iid,
                question="Does X control Y?",
                status=InvestigationStatus.EVIDENCE_COLLECTION.value,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    with session_scope() as session:
        session.add(
            ClaimRow(
                id=f"{iid}_a",
                investigation_id=iid,
                text=claim_a,
                status=ClaimStatus.UNVERIFIED.value,
                source_ids="[]",
                contradictions="[]",
                epistemic_kind="unknown",
                confidence=0.2,
            )
        )
        session.add(
            ClaimRow(
                id=f"{iid}_b",
                investigation_id=iid,
                text=claim_b,
                status=ClaimStatus.UNVERIFIED.value,
                source_ids="[]",
                contradictions="[]",
                epistemic_kind="unknown",
                confidence=0.2,
            )
        )
    src_a = register_source(
        iid, url="https://alpha.example/a", title="A", publisher=pub_a, content_hash="ha"
    )
    src_b = register_source(
        iid, url="https://beta.example/b", title="B", publisher=pub_b, content_hash="hb"
    )
    add_evidence(
        iid, source_id=src_a["id"], claim_id=f"{iid}_a", description=claim_a, content_hash="ha"
    )
    add_evidence(
        iid, source_id=src_b["id"], claim_id=f"{iid}_b", description=claim_b, content_hash="hb"
    )
    with session_scope() as session:
        a = session.get(ClaimRow, f"{iid}_a")
        b = session.get(ClaimRow, f"{iid}_b")
        a.source_ids = json.dumps([src_a["id"]])
        b.source_ids = json.dumps([src_b["id"]])
    return iid


def test_scan_records_independent_contradiction(db):
    iid = _inv_with_claims(
        "Organization X controls Organization Y.",
        "Organization X does not control Organization Y.",
        "Alpha",
        "Beta",
    )
    found = scan_investigation(iid)
    assert len(found) == 1
    assert found[0]["independent"] is True
    assert found[0]["same_publisher"] is False
    stored = list_contradictions(iid)
    assert stored[0]["claim_a_id"] in {f"{iid}_a", f"{iid}_b"}
    with session_scope() as session:
        a = session.get(ClaimRow, f"{iid}_a")
        b = session.get(ClaimRow, f"{iid}_b")
        assert a.status == ClaimStatus.CONTRADICTED.value
        assert b.status == ClaimStatus.CONTRADICTED.value
    ev = list_evidence(iid)
    assert any(e["contradictions"] for e in ev)


def test_same_publisher_contradiction_is_not_independent(db):
    iid = _inv_with_claims(
        "The merger was completed in June.",
        "The merger was not completed in June.",
        "SamePub",
        "SamePub",
    )
    found = scan_investigation(iid)
    assert len(found) == 1
    assert found[0]["independent"] is False
    assert found[0]["same_publisher"] is True
