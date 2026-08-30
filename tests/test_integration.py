"""Live public-page investigation. Skips if the network is unreachable."""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest

from observer.core import content_hash
from observer.db import session_scope
from observer.models import ResearchRecordRow
from observer.pipeline import run_investigation


@pytest.mark.integration
def test_live_example_com_investigation(db):
    if os.environ.get("OBSERVER_SKIP_LIVE") == "1":
        pytest.skip("live network disabled")
    try:
        httpx.get("https://example.com/", timeout=10.0, follow_redirects=True).raise_for_status()
    except Exception as exc:
        pytest.skip(f"example.com unreachable: {exc}")

    with patch("observer.pipeline.archiver.search", return_value=[]):
        result = run_investigation(
            "What is example.com presenting to the public?",
            urls=["https://example.com/"],
            search=False,
        )
    report = result["report"]
    assert result["ingested"]
    assert result["hypotheses"]
    assert result["audit"]["warnings"] is not None
    assert report["executive_summary"]
    assert report["source_ledger"]
    iid = report["investigation_id"]
    with session_scope() as session:
        rec = (
            session.query(ResearchRecordRow)
            .filter(ResearchRecordRow.investigation_id == iid)
            .first()
        )
        assert rec is not None
        data = open(rec.archive_path, "rb").read()
        assert rec.content_hash == content_hash(data)
