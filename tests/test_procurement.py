from unittest.mock import patch

import httpx

from observer.research.procurement import ProcurementAdapter, _award_url, _parse_awards
from tests.http_mock import _RealClient

SAMPLE = {
    "results": [
        {
            "Award ID": "CONT_AWD_EXAMPLE",
            "Recipient Name": "Example Contractor LLC",
            "Award Amount": 1200000,
            "Awarding Agency": "Department of Example",
            "Description": "Public contract for example services",
            "generated_internal_id": "CONT_AWD_EXAMPLE_ID",
        },
        {"Recipient Name": "missing id"},
    ]
}


def test_award_url_is_usaspending():
    url = _award_url({"generated_internal_id": "CONT_AWD_EXAMPLE_ID"})
    assert url == "https://www.usaspending.gov/award/CONT_AWD_EXAMPLE_ID/"


def test_parse_awards_skips_malformed():
    hits = _parse_awards(SAMPLE, limit=5)
    assert len(hits) == 1
    assert hits[0]["failed"] is False
    assert hits[0]["source_type"] == "government_record"
    assert "award is not proof" in hits[0]["limitations"].lower() or "not proof" in hits[0]["limitations"].lower()


def test_empty_query_is_honest_failure():
    hits = ProcurementAdapter().search("  ")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_free_text_question_is_honest_failure():
    hits = ProcurementAdapter().search("What actually happened yesterday?")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""


def test_search_returns_award_hit(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SAMPLE, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = ProcurementAdapter()
    with patch("observer.research.procurement.httpx.Client", factory):
        hits = adapter.search("Example Contractor LLC contract")
    assert hits[0]["failed"] is False
    assert "usaspending.gov" in hits[0]["url"]


def test_search_honest_when_blocked(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="nope", request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = ProcurementAdapter()
    with patch("observer.research.procurement.httpx.Client", factory):
        hits = adapter.search("Example Contractor LLC contract")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
