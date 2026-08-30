from fastapi.testclient import TestClient

from observer.api import app
from observer.ledger import list_evidence
from observer.public import list_submissions, submit


def test_public_submission_is_unreviewed_not_evidence(db):
    saved = submit(
        "This public filing may have been missed.",
        classification="EVIDENCE",
        url="https://example.com/public-note",
    )
    assert saved["status"] == "UNREVIEWED"
    assert saved["verified"] is False
    assert saved["content_hash"]
    listed = list_submissions()
    assert any(row["id"] == saved["id"] for row in listed)
    assert list_evidence(saved["investigation_id"] or "none") == []


def test_public_submission_via_api(db):
    with TestClient(app) as client:
        created = client.post(
            "/public/submissions",
            json={"body": "Have you checked this timeline?", "classification": "LEAD"},
        ).json()
        assert created["status"] == "UNREVIEWED"
        listed = client.get("/public/submissions").json()
        assert any(row["id"] == created["id"] for row in listed["submissions"])
