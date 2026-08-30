"""Internet Archive Wayback lookup. Public snapshots only — not a paywall bypass."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from observer.policy import PolicyDenied, assess_fetch_url
from observer.research.http_fetch import HttpFetchAdapter
from observer.settings import load_settings

AVAILABLE_API = "https://archive.org/wayback/available"
CDX_API = "https://web.archive.org/cdx/search/cdx"


class WaybackAdapter:
    adapter_id = "wayback"
    status = "connected"

    def __init__(self) -> None:
        self._fetch = HttpFetchAdapter()

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        if not _looks_like_url(q):
            return [
                _fail(
                    "Wayback looks up archived copies of a URL, not keyword web search."
                )
            ]
        try:
            assess_fetch_url(q)
        except PolicyDenied as exc:
            return [_fail(str(exc))]
        settings = load_settings()
        headers = {"User-Agent": settings.observer_user_agent, "Accept": "application/json"}
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(
                    AVAILABLE_API,
                    params={"url": q},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [_fail(f"wayback availability request failed: {exc}")]
        hits = _parse_available(payload, limit=limit)
        if hits:
            return hits
        cdx_hits = self._cdx(q, limit=limit, headers=headers)
        return cdx_hits if cdx_hits else [_fail("no archived snapshot available")]

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        target = url
        if not _is_archive_host(url):
            hits = self.search(url, limit=1)
            if not hits or hits[0].get("failed") or not hits[0].get("url"):
                raise RuntimeError(hits[0].get("reason") if hits else "no archived snapshot")
            target = hits[0]["url"]
        result = self._fetch.fetch(target)
        result["adapter"] = self.adapter_id
        result["original_url"] = _original_from_archive(target) or url
        result["archival"] = True
        return result

    def _cdx(self, url: str, *, limit: int, headers: dict) -> list[dict]:
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(
                    CDX_API,
                    params={
                        "url": url,
                        "output": "json",
                        "fl": "timestamp,original,statuscode,mimetype",
                        "filter": "statuscode:200",
                        "limit": str(max(1, limit)),
                    },
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []
        return _parse_cdx(payload, limit=limit)


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_archive_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"web.archive.org", "archive.org"}


def _original_from_archive(url: str) -> str:
    marker = "/web/"
    if "web.archive.org" not in url or marker not in url:
        return ""
    rest = url.split(marker, 1)[1]
    parts = rest.split("/", 1)
    if len(parts) != 2:
        return ""
    original = parts[1]
    if original.startswith("http"):
        return original
    return ""


def _parse_available(payload: object, *, limit: int) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    closest = ((payload.get("archived_snapshots") or {}) or {}).get("closest") or {}
    if not closest.get("available"):
        return []
    snap = str(closest.get("url") or "")
    if not snap:
        return []
    try:
        assess_fetch_url(snap.replace("http://", "https://", 1) if snap.startswith("http://") else snap)
    except PolicyDenied:
        return []
    normalized = snap.replace("http://web.archive.org", "https://web.archive.org", 1)
    return [
        {
            "url": normalized,
            "title": f"Wayback {closest.get('timestamp') or ''}".strip(),
            "snippet": _original_from_archive(normalized),
            "adapter": "wayback",
            "failed": False,
            "timestamp": str(closest.get("timestamp") or ""),
            "archival": True,
        }
    ][:limit]


def _parse_cdx(payload: object, *, limit: int) -> list[dict]:
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    rows = payload[1:]
    hits: list[dict] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        timestamp, original = str(row[0]), str(row[1])
        snap = f"https://web.archive.org/web/{timestamp}/{original}"
        try:
            assess_fetch_url(snap)
        except PolicyDenied:
            continue
        hits.append(
            {
                "url": snap,
                "title": f"Wayback {timestamp}",
                "snippet": original,
                "adapter": "wayback",
                "failed": False,
                "timestamp": timestamp,
                "archival": True,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def _fail(reason: str) -> dict:
    return {
        "url": "",
        "title": "",
        "snippet": "",
        "adapter": "wayback",
        "failed": True,
        "reason": reason,
        "archival": True,
    }
