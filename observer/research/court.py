"""Public court opinions via CourtListener. Not PACER. Not a complete docket."""

from __future__ import annotations

from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

from observer.policy import PolicyDenied, assess_fetch_url
from observer.research.http_fetch import HttpFetchAdapter
from observer.settings import load_settings

SEARCH_API = "https://www.courtlistener.com/api/rest/v4/search/"
COURTLISTENER = "https://www.courtlistener.com"
LIMITATION = (
    "CourtListener public opinion page. Not PACER. Not a complete docket. "
    "Republication can lag or omit. The court file is the original."
)
PACER_HOST_MARKERS = ("pacer.gov", "uscourts.gov")


class CourtRecordsAdapter:
    adapter_id = "court_records"
    status = "connected"

    def __init__(self) -> None:
        self._fetch = HttpFetchAdapter()

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        settings = load_settings()
        headers = {
            "User-Agent": settings.observer_user_agent,
            "Accept": "application/json",
        }
        token = (getattr(settings, "courtlistener_token", "") or "").strip()
        if token:
            headers["Authorization"] = f"Token {token}"
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(
                    SEARCH_API,
                    params={"q": q, "type": "o"},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [_fail(f"courtlistener search failed: {exc}")]
        hits = _parse_search(payload, limit=limit)
        return hits if hits else [_fail("no public CourtListener opinions matched")]

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        if _is_pacer(url):
            raise PolicyDenied("PACER and uscourts.gov authenticated dockets are not fetched.")
        result = self._fetch.fetch(url)
        result["adapter"] = self.adapter_id
        result["source_type"] = "court_record"
        return result


def _parse_search(payload: object, *, limit: int) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    results = payload.get("results") or []
    if not isinstance(results, list):
        return []
    hits: list[dict] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        url = _opinion_url(row)
        if not url or _is_pacer(url):
            continue
        try:
            assess_fetch_url(url)
        except PolicyDenied:
            continue
        title = str(row.get("caseName") or row.get("caseNameFull") or url)[:300]
        court = str(row.get("court") or "")
        filed = str(row.get("dateFiled") or "")
        snippet = _snippet(row)
        hits.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
                "adapter": "court_records",
                "failed": False,
                "court": court,
                "date_filed": filed,
                "source_type": "court_record",
                "limitations": LIMITATION,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def _opinion_url(row: dict) -> str:
    raw = str(row.get("absolute_url") or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return urljoin(COURTLISTENER, raw)


def _snippet(row: dict) -> str:
    opinions = row.get("opinions") or []
    if isinstance(opinions, list) and opinions:
        first = opinions[0] if isinstance(opinions[0], dict) else {}
        text = unescape(str(first.get("snippet") or ""))
        return text.strip()[:500]
    return unescape(str(row.get("snippet") or "")).strip()[:500]


def _is_pacer(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == m or host.endswith("." + m) for m in PACER_HOST_MARKERS)


def _fail(reason: str) -> dict:
    return {
        "url": "",
        "title": "",
        "snippet": "",
        "adapter": "court_records",
        "failed": True,
        "reason": reason,
        "source_type": "court_record",
        "limitations": LIMITATION,
    }
