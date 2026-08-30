from unittest.mock import patch

import httpx

from observer.research.patents import PatentsAdapter, _parse_uspto, _patent_public_url
from tests.http_mock import _RealClient

SAMPLE = {
    "response": {
        "docs": [
            {
                "patentNumber": "10000000",
                "inventionTitle": "Coherent LADAR using intra-pixel quadrature detection",
                "assigneeEntityName": ["The United States of America as Represented by the Administrator of NASA"],
                "publicationDate": "2018-06-19",
            },
            {
                "inventionTitle": "missing number",
            },
        ]
    }
}


def test_patent_public_url_is_uspto():
    url = _patent_public_url("US10000000B2")
    assert url == "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10000000"
    assert "google.com" not in url


def test_parse_uspto_skips_malformed():
    hits = _parse_uspto(SAMPLE, limit=5)
    assert len(hits) == 1
    assert hits[0]["failed"] is False
    assert hits[0]["source_type"] == "government_record"
    assert "grant is not proof" in hits[0]["limitations"].lower() or "not proof" in hits[0]["limitations"].lower()
    assert "10000000" in hits[0]["url"]


def test_empty_query_is_honest_failure():
    hits = PatentsAdapter().search("  ")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_free_text_question_is_honest_failure():
    hits = PatentsAdapter().search("What actually happened yesterday?")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_search_returns_patent_hit(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SAMPLE, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = PatentsAdapter()
    with patch("observer.research.patents.httpx.Client", factory):
        hits = adapter.search("US patent 10000000")
    assert hits[0]["failed"] is False
    assert "uspto.gov" in hits[0]["url"]


def test_search_honest_when_blocked(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="nope", request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = PatentsAdapter()
    with patch("observer.research.patents.httpx.Client", factory):
        hits = adapter.search("US patent solar")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
