from __future__ import annotations

from unittest.mock import patch

from observer.core import content_hash
from observer.db import session_scope
from observer.models import ResearchRecordRow
from observer.pipeline import run_investigation
from observer.reports import REQUIRED_SECTIONS
from observer.sources import list_sources
from tests.http_mock import mock_client_factory

HTML = """<html><title>Example Domain</title><body>
<p>The Example Organization published this page about Example Domain together with Beta Institute.</p>
<p>Independent actors may be responding to ordinary market demand rather than secret control.</p>
</body></html>"""


def test_pipeline_end_to_end_with_url_intake(db):
    search_hits = [
        {
            "url": "https://example.com/",
            "title": "Example",
            "snippet": "",
            "adapter": "duckduckgo_lite",
            "failed": False,
        }
    ]
    with (
        patch("observer.pipeline.searcher.search", return_value=search_hits),
        patch("observer.pipeline.courts.search", return_value=[]),
        patch("observer.pipeline.corporates.search", return_value=[]),
        patch("observer.pipeline.filings.search", return_value=[]),
        patch("observer.pipeline.patents.search", return_value=[]),
        patch("observer.pipeline.procurement.search", return_value=[]),
        patch("observer.pipeline.archiver.search", return_value=[]),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(HTML)),
    ):
        result = run_investigation(
            "What is Example Domain?",
            urls=["https://example.com/"],
            search=True,
        )
    report = result["report"]
    assert result["ingested"]
    assert result["hypotheses"]
    assert any(h["is_counter"] for h in result["hypotheses"])
    assert result["audit"]["warnings"] is not None
    for key in REQUIRED_SECTIONS:
        assert key in report
    iid = report["investigation_id"]
    with session_scope() as session:
        recs = (
            session.query(ResearchRecordRow)
            .filter(ResearchRecordRow.investigation_id == iid)
            .all()
        )
        assert recs
        rec = recs[0]
        blob = rec.archive_path
        assert blob
        data = open(blob, "rb").read()
        assert rec.content_hash == content_hash(data)
    assert report["evidence"]
    assert report["status"] == "fact_check"
    assert report["publish_status"] == "disabled"


def test_pipeline_ingests_wayback_snapshot(db):
    html = "<html><title>Archived Example</title><body><p>The Example Organization archived this page.</p></body></html>"
    snap = "https://web.archive.org/web/20200101000000/https://example.com/"
    with (
        patch("observer.pipeline.searcher.search", return_value=[]),
        patch("observer.pipeline.courts.search", return_value=[]),
        patch("observer.pipeline.corporates.search", return_value=[]),
        patch("observer.pipeline.filings.search", return_value=[]),
        patch("observer.pipeline.patents.search", return_value=[]),
        patch("observer.pipeline.procurement.search", return_value=[]),
        patch(
            "observer.pipeline.archiver.search",
            return_value=[
                {
                    "url": snap,
                    "title": "Wayback 20200101000000",
                    "adapter": "wayback",
                    "failed": False,
                    "archival": True,
                }
            ],
        ),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(html)),
    ):
        result = run_investigation(
            "Was this page archived?",
            urls=["https://example.com/"],
            search=False,
        )
    urls = [item.get("url") for item in result["ingested"] if item.get("url")]
    assert any("web.archive.org" in (u or "") for u in urls)
    assert any(item.get("archival") for item in result["ingested"])
    sources = list_sources(result["report"]["investigation_id"])
    assert any(s.get("source_type") == "archived_webpage" for s in sources)


def test_pipeline_ingests_courtlistener_opinion(db):
    html = (
        "<html><title>Foo v. Foo</title><body>"
        "<p>The Example Court published this opinion about Foo versus Foo.</p>"
        "</body></html>"
    )
    opinion = "https://www.courtlistener.com/opinion/6613686/foo-v-foo/"
    with (
        patch("observer.pipeline.searcher.search", return_value=[]),
        patch(
            "observer.pipeline.courts.search",
            return_value=[
                {
                    "url": opinion,
                    "title": "Foo v. Foo",
                    "adapter": "court_records",
                    "failed": False,
                    "source_type": "court_record",
                    "limitations": "CourtListener public opinion page. Not PACER.",
                }
            ],
        ),
        patch("observer.pipeline.corporates.search", return_value=[]),
        patch("observer.pipeline.filings.search", return_value=[]),
        patch("observer.pipeline.patents.search", return_value=[]),
        patch("observer.pipeline.procurement.search", return_value=[]),
        patch("observer.pipeline.archiver.search", return_value=[]),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(html)),
    ):
        result = run_investigation("Did Foo v. Foo exist?", search=True)
    assert any("courtlistener.com" in (u or "") for u in [i.get("url") for i in result["ingested"]])
    sources = list_sources(result["report"]["investigation_id"])
    assert any(s.get("source_type") == "court_record" for s in sources)


def test_pipeline_ingests_gleif_lei_record(db):
    body = '{"data":{"type":"lei-records","id":"HWUPKR0MPOU8FGXBT394"},"legalName":"Apple Inc."}'
    url = "https://api.gleif.org/api/v1/lei-records/HWUPKR0MPOU8FGXBT394"
    with (
        patch("observer.pipeline.searcher.search", return_value=[]),
        patch("observer.pipeline.courts.search", return_value=[]),
        patch(
            "observer.pipeline.corporates.search",
            return_value=[
                {
                    "url": url,
                    "title": "Apple Inc.",
                    "adapter": "corporate_registries",
                    "failed": False,
                    "source_type": "corporate_filing",
                    "limitations": "GLEIF LEI record. Not a secretary-of-state filing.",
                }
            ],
        ),
        patch("observer.pipeline.filings.search", return_value=[]),
        patch("observer.pipeline.patents.search", return_value=[]),
        patch("observer.pipeline.procurement.search", return_value=[]),
        patch("observer.pipeline.archiver.search", return_value=[]),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(body)),
    ):
        result = run_investigation("Who is Apple Inc. registered as?", search=True)
    assert any("gleif.org" in (u or "") for u in [i.get("url") for i in result["ingested"]])
    sources = list_sources(result["report"]["investigation_id"])
    assert any(s.get("source_type") == "corporate_filing" for s in sources)


def test_pipeline_ingests_sec_edgar_filing(db):
    html = (
        "<html><title>Apple Inc. 10-K</title><body>"
        "<p>Apple Inc. filed this annual report with the Commission.</p>"
        "</body></html>"
    )
    filing = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000069/aapl-20240928.htm"
    with (
        patch("observer.pipeline.searcher.search", return_value=[]),
        patch("observer.pipeline.courts.search", return_value=[]),
        patch("observer.pipeline.corporates.search", return_value=[]),
        patch(
            "observer.pipeline.filings.search",
            return_value=[
                {
                    "url": filing,
                    "title": "Apple Inc. (AAPL)",
                    "adapter": "sec_filings",
                    "failed": False,
                    "source_type": "financial_record",
                    "limitations": "SEC EDGAR public filing copy. A filing is a statement by the filer.",
                }
            ],
        ),
        patch("observer.pipeline.patents.search", return_value=[]),
        patch("observer.pipeline.procurement.search", return_value=[]),
        patch("observer.pipeline.archiver.search", return_value=[]),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(html)),
    ):
        result = run_investigation("Apple Inc. 10-K", search=True)
    assert any("sec.gov/Archives/edgar" in (u or "") for u in [i.get("url") for i in result["ingested"]])
    sources = list_sources(result["report"]["investigation_id"])
    assert any(s.get("source_type") == "financial_record" for s in sources)


def test_pipeline_ingests_uspto_patent(db):
    html = (
        "<html><title>US 10000000</title><body>"
        "<p>The United States Patent and Trademark Office published this grant.</p>"
        "</body></html>"
    )
    url = "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10000000"
    with (
        patch("observer.pipeline.searcher.search", return_value=[]),
        patch("observer.pipeline.courts.search", return_value=[]),
        patch("observer.pipeline.corporates.search", return_value=[]),
        patch("observer.pipeline.filings.search", return_value=[]),
        patch(
            "observer.pipeline.patents.search",
            return_value=[
                {
                    "url": url,
                    "title": "Example patent",
                    "adapter": "patents",
                    "failed": False,
                    "source_type": "government_record",
                    "limitations": "A grant is not proof of use.",
                }
            ],
        ),
        patch("observer.pipeline.procurement.search", return_value=[]),
        patch("observer.pipeline.archiver.search", return_value=[]),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(html)),
    ):
        result = run_investigation("US patent 10000000", search=True)
    assert any("uspto.gov" in (u or "") for u in [i.get("url") for i in result["ingested"]])
    sources = list_sources(result["report"]["investigation_id"])
    assert any(s.get("source_type") == "government_record" for s in sources)


def test_pipeline_ingests_usaspending_award(db):
    html = (
        "<html><title>Example Contractor LLC</title><body>"
        "<p>The Department of Example published this award to Example Contractor LLC.</p>"
        "</body></html>"
    )
    url = "https://www.usaspending.gov/award/CONT_AWD_EXAMPLE_ID/"
    with (
        patch("observer.pipeline.searcher.search", return_value=[]),
        patch("observer.pipeline.courts.search", return_value=[]),
        patch("observer.pipeline.corporates.search", return_value=[]),
        patch("observer.pipeline.filings.search", return_value=[]),
        patch("observer.pipeline.patents.search", return_value=[]),
        patch(
            "observer.pipeline.procurement.search",
            return_value=[
                {
                    "url": url,
                    "title": "Example Contractor LLC",
                    "adapter": "procurement",
                    "failed": False,
                    "source_type": "government_record",
                    "limitations": "An award is not proof of misconduct.",
                }
            ],
        ),
        patch("observer.pipeline.archiver.search", return_value=[]),
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(html)),
    ):
        result = run_investigation("Example Contractor LLC contract", search=True)
    assert any("usaspending.gov" in (u or "") for u in [i.get("url") for i in result["ingested"]])
    sources = list_sources(result["report"]["investigation_id"])
    assert any(s.get("source_type") == "government_record" for s in sources)
