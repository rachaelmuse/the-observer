from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from observer.policy import PolicyDenied
from observer.research.http_fetch import HttpFetchAdapter
from observer.research.url_intake import UrlIntakeAdapter
from observer.research.web_search import WebSearchAdapter, _parse_hits
from tests.http_mock import mock_client_factory

HTML = """<html><title>Example Domain</title><body>
<p>The Example Organization published this page about Example Domain in 2024.</p>
</body></html>"""


def test_url_intake_accepts_public_and_rejects_private():
    adapter = UrlIntakeAdapter()
    assert adapter.intake(["https://example.com/a"]) == ["https://example.com/a"]
    with pytest.raises(PolicyDenied):
        adapter.intake(["http://127.0.0.1/secret"])


def test_http_fetch_archives_hash(db, tmp_path, monkeypatch):
    monkeypatch.setenv("OBSERVER_ARCHIVE_DIR", str(tmp_path / "archive"))
    adapter = HttpFetchAdapter()
    with (
        patch("observer.research.http_fetch._robots_allows", return_value=True),
        patch("observer.research.http_fetch.httpx.Client", mock_client_factory(HTML)),
    ):
        result = adapter.fetch("https://example.com/")
    assert result["content_hash"]
    blob = Path(result["archive_path"])
    assert blob.is_file()
    assert blob.read_bytes() == result["bytes"]
    assert result["untrusted"].startswith("<UNTRUSTED_SOURCE_DATA>")


def test_http_fetch_respects_robots_denial(db):
    adapter = HttpFetchAdapter()
    with patch("observer.research.http_fetch._robots_allows", return_value=False):
        with pytest.raises(PolicyDenied):
            adapter.fetch("https://example.com/hidden")


def test_search_parser_extracts_real_hrefs():
    html = """
    <a class="result-link" href="https://example.com/alpha">Alpha Title</a>
    <a class="result-link" href="https://example.org/beta">Beta Title</a>
    """
    hits = _parse_hits(html, limit=5)
    assert [h["url"] for h in hits] == ["https://example.com/alpha", "https://example.org/beta"]
    assert all(h["failed"] is False for h in hits)


def test_search_honest_failure_on_empty_markup():
    adapter = WebSearchAdapter()
    with patch(
        "observer.research.web_search.httpx.Client",
        mock_client_factory("<html><body>no results</body></html>"),
    ):
        hits = adapter.search("obscure query")
    assert hits[0]["failed"] is True
    assert hits[0]["url"] == ""
