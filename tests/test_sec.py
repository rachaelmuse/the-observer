from unittest.mock import patch

import httpx

from observer.research.sec import SecFilingsAdapter, _edgar_document_url, _parse_efts
from tests.http_mock import _RealClient

SAMPLE = {
    "hits": {
        "hits": [
            {
                "_id": "0000320193-24-000069:aapl-20240928.htm",
                "_source": {
                    "ciks": ["0000320193"],
                    "display_names": ["Apple Inc.  (AAPL)  (CIK 0000320193)"],
                    "root_forms": ["10-K"],
                    "file_date": "2024-11-01",
                    "period_ending": "2024-09-28",
                },
            },
            {
                "_id": "bad",
                "_source": {"ciks": ["0000320193"]},
            },
        ]
    }
}


def test_edgar_document_url_from_efts_id():
    url = _edgar_document_url(SAMPLE["hits"]["hits"][0])
    assert url == "https://www.sec.gov/Archives/edgar/data/320193/000032019324000069/aapl-20240928.htm"


def test_parse_efts_skips_malformed():
    hits = _parse_efts(SAMPLE, limit=5)
    assert len(hits) == 1
    assert hits[0]["failed"] is False
    assert hits[0]["source_type"] == "financial_record"
    assert "filer" in hits[0]["limitations"].lower()


def test_empty_query_is_honest_failure():
    hits = SecFilingsAdapter().search("  ")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_free_text_question_is_honest_failure():
    hits = SecFilingsAdapter().search("What actually happened yesterday?")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_search_returns_filing_hit(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SAMPLE, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = SecFilingsAdapter()
    with patch("observer.research.sec.httpx.Client", factory):
        hits = adapter.search("Apple Inc. 10-K")
    assert hits[0]["failed"] is False
    assert "sec.gov/Archives/edgar" in hits[0]["url"]


def test_search_honest_when_blocked(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="nope", request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = SecFilingsAdapter()
    with patch("observer.research.sec.httpx.Client", factory):
        hits = adapter.search("Apple Inc.")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
