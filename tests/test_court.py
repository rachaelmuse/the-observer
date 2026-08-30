from unittest.mock import patch

import httpx

from observer.research.court import CourtRecordsAdapter, _parse_search
from tests.http_mock import _RealClient

SAMPLE = {
    "count": 1,
    "results": [
        {
            "absolute_url": "/opinion/6613686/foo-v-foo/",
            "caseName": "Foo v. Foo",
            "court": "Hawaii Intermediate Court of Appeals",
            "dateFiled": "2003-01-10",
            "opinions": [{"snippet": "Affirmed in part."}],
        },
        {
            "absolute_url": "https://pacer.gov/doc/1",
            "caseName": "Secret PACER",
            "court": "somewhere",
        },
    ],
}


def test_parse_search_builds_public_opinion_urls():
    hits = _parse_search(SAMPLE, limit=5)
    assert len(hits) == 1
    assert hits[0]["failed"] is False
    assert hits[0]["url"] == "https://www.courtlistener.com/opinion/6613686/foo-v-foo/"
    assert hits[0]["source_type"] == "court_record"
    assert "PACER" in hits[0]["limitations"]


def test_parse_search_empty_is_empty():
    assert _parse_search({"results": []}, limit=3) == []


def test_empty_query_is_honest_failure():
    hits = CourtRecordsAdapter().search("  ")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_search_returns_opinion_hit(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SAMPLE, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = CourtRecordsAdapter()
    with patch("observer.research.court.httpx.Client", factory):
        hits = adapter.search("Foo v. Foo")
    assert hits[0]["failed"] is False
    assert "courtlistener.com/opinion/" in hits[0]["url"]


def test_search_honest_when_blocked(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="nope", request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = CourtRecordsAdapter()
    with patch("observer.research.court.httpx.Client", factory):
        hits = adapter.search("anything")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
