from unittest.mock import patch

import httpx

from observer.research.wayback import WaybackAdapter, _parse_available, _parse_cdx
from tests.http_mock import _RealClient


def test_parse_available_snapshot():
    payload = {
        "archived_snapshots": {
            "closest": {
                "available": True,
                "url": "http://web.archive.org/web/20200101000000/https://example.com/",
                "timestamp": "20200101000000",
                "status": "200",
            }
        }
    }
    hits = _parse_available(payload, limit=3)
    assert len(hits) == 1
    assert hits[0]["failed"] is False
    assert hits[0]["archival"] is True
    assert "web.archive.org/web/20200101000000" in hits[0]["url"]


def test_parse_available_missing_is_empty():
    assert _parse_available({"archived_snapshots": {}}, limit=1) == []


def test_parse_cdx_builds_snapshot_urls():
    payload = [
        ["timestamp", "original"],
        ["20200101000000", "https://example.com/"],
        ["20210101000000", "https://example.com/page"],
    ]
    hits = _parse_cdx(payload, limit=2)
    assert [h["url"] for h in hits] == [
        "https://web.archive.org/web/20200101000000/https://example.com/",
        "https://web.archive.org/web/20210101000000/https://example.com/page",
    ]


def test_keyword_search_is_honest_failure():
    adapter = WaybackAdapter()
    hits = adapter.search("who funded the merger")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
    assert "URL" in hits[0]["reason"]


def test_url_search_returns_snapshot(db):
    body = {
        "archived_snapshots": {
            "closest": {
                "available": True,
                "url": "https://web.archive.org/web/20200101000000/https://example.com/",
                "timestamp": "20200101000000",
                "status": "200",
            }
        }
    }

    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=body, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = WaybackAdapter()
    with patch("observer.research.wayback.httpx.Client", factory):
        hits = adapter.search("https://example.com/")
    assert hits[0]["failed"] is False
    assert hits[0]["url"].startswith("https://web.archive.org/web/")


def test_url_search_honest_when_empty(db):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"archived_snapshots": {}}, request=request)

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    adapter = WaybackAdapter()
    with patch("observer.research.wayback.httpx.Client", factory):
        hits = adapter.search("https://example.com/never-archived-zzz")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
