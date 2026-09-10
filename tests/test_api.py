from fastapi.testclient import TestClient

from observer.api import app
from observer.registry import list_registry


def test_health_and_registry(db):
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["status"] == "operational"
        assert health["entity"] == "The Observer"
        assert "vesper" in health["never_merge"]
        assert "mythos" in health["never_merge"]
        registry = client.get("/registry").json()
        by_id = {c["id"]: c for c in registry["capabilities"]}
        assert by_id["http_fetch"]["status"] == "connected"
        assert by_id["wayback"]["status"] == "connected"
        assert by_id["court_records"]["status"] == "connected"
        assert by_id["corporate_registries"]["status"] == "connected"
        assert by_id["sec_filings"]["status"] == "connected"
        assert by_id["patents"]["status"] == "connected"
        assert by_id["procurement"]["status"] == "connected"
        assert by_id["public_submission"]["status"] == "connected"
        assert by_id["four_reviewers"]["status"] == "unavailable"
        assert by_id["auto_publish"]["status"] == "disabled"
        live = {c["id"]: c["status"] for c in list_registry()}
        assert live["http_fetch"] == by_id["http_fetch"]["status"]


def test_create_investigation_and_dashboard(db):
    with TestClient(app) as client:
        created = client.post("/investigations", json={"question": "Who benefited?"}).json()
        assert created["id"].startswith("inv_")
        assert "FACTS" in created["questions"]
        listed = client.get("/investigations").json()["investigations"]
        assert any(row["id"] == created["id"] for row in listed)
        page = client.get("/")
        assert page.status_code == 200
        assert b"The Observer" in page.content
        forbidden = client.post(f"/investigations/{created['id']}/publish")
        assert forbidden.status_code == 403


def test_run_investigation_via_api(db, monkeypatch):
    from unittest.mock import patch

    from tests.http_mock import mock_client_factory

    html = "<html><title>T</title><body><p>The Example Organization published notes.</p></body></html>"

    with TestClient(app) as client:
        with (
            patch("observer.pipeline.searcher.search", return_value=[]),
            patch("observer.pipeline.courts.search", return_value=[]),
            patch("observer.pipeline.corporates.search", return_value=[]),
            patch("observer.pipeline.filings.search", return_value=[]),
            patch("observer.pipeline.patents.search", return_value=[]),
            patch("observer.pipeline.procurement.search", return_value=[]),
            patch("observer.pipeline.archiver.search", return_value=[]),
            patch("observer.research.http_fetch._robots_allows", return_value=True),
            patch("observer.research.http_fetch.httpx.Client", mock_client_factory(html)),
        ):
            result = client.post(
                "/investigations/run",
                json={"question": "What did they publish?", "urls": ["https://example.com/"], "search": False},
            ).json()
        iid = result["report"]["investigation_id"]
        report = client.get(f"/investigations/{iid}/report").json()
        assert report["executive_summary"]
        detail = client.get(f"/investigations/{iid}").json()
        if detail["entities"]:
            eid = detail["entities"][0]["id"]
            panel = client.get(f"/investigations/{iid}/entities/{eid}").json()
            assert "WHO" in panel
            assert "WHERE" in panel
            assert "POSSIBLE_HOW" in panel
            assert "POSSIBLE_WHY" in panel
