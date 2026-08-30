from unittest.mock import patch

import httpx

from observer.research.corporate import CorporateRegistriesAdapter, _parse_lei_records
from tests.http_mock import _RealClient

SAMPLE = {
    "data": [
        {
            "type": "lei-records",
            "id": "HWUPKR0MPOU8FGXBT394",
            "attributes": {
                "lei": "HWUPKR0MPOU8FGXBT394",
                "entity": {
                    "legalName": {"name": "Apple Inc.", "language": "en"},
                    "jurisdiction": "US-CA",
                    "status": "ACTIVE",
                    "registeredAs": "806592",
                },
            },
        }
    ]
}


def test_parse_lei_records_builds_public_json_url():
    hits = _parse_lei_records(SAMPLE, limit=3)
    assert len(hits) == 1
    assert hits[0]["failed"] is False
    assert hits[0]["url"] == "https://api.gleif.org/api/v1/lei-records/HWUPKR0MPOU8FGXBT394"
    assert hits[0]["source_type"] == "corporate_filing"
    assert "beneficial" in hits[0]["limitations"].lower() or "not a secretary" in hits[0]["limitations"].lower()


def test_parse_empty_is_empty():
    assert _parse_lei_records({"data": []}, limit=2) == []


def test_empty_query_is_honest_failure():
    hits = CorporateRegistriesAdapter().search("  ")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_free_text_question_is_honest_failure():
    hits = CorporateRegistriesAdapter().search("What actually happened yesterday?")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
    assert "LEI" in hits[0]["reason"] or "legal entity" in hits[0]["reason"].lower()


def test_search_returns_lei_hit(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SAMPLE, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = CorporateRegistriesAdapter()
    with patch("observer.research.corporate.httpx.Client", factory):
        hits = adapter.search("Apple Inc.")
    assert hits[0]["failed"] is False
    assert "HWUPKR0MPOU8FGXBT394" in hits[0]["url"]


def test_search_honest_when_blocked(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="nope", request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = CorporateRegistriesAdapter()
    with patch("observer.research.corporate.httpx.Client", factory):
        hits = adapter.search("Apple Inc.")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
