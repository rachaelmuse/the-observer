"""DuckDuckGo lite search. Honest failure — never invent URLs."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote_plus, urljoin, urlparse

import httpx

from observer.policy import assess_fetch_url
from observer.settings import load_settings

HREF_RE = re.compile(r'<a[^>]+class="[^"]*result-link[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
HREF_RE_ALT = re.compile(r'<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*class="[^"]*result-link[^"]*"[^>]*>(.*?)</a>', re.I | re.S)
GENERIC_A = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


class WebSearchAdapter:
    adapter_id = "web_search"
    status = "connected"

    def fetch(self, url: str) -> dict:
        raise NotImplementedError("Use HttpFetchAdapter for fetch.")

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        settings = load_settings()
        url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(q)}"
        headers = {"User-Agent": settings.observer_user_agent, "Accept": "text/html"}
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                html = response.text
        except Exception as exc:
            return [_fail(f"search request failed: {exc}")]
        hits = _parse_hits(html, limit=limit)
        if not hits:
            return [_fail("no parseable results (adapter blocked or markup changed)")]
        return hits


def _fail(reason: str) -> dict:
    return {
        "url": "",
        "title": "",
        "snippet": "",
        "adapter": "duckduckgo_lite",
        "failed": True,
        "reason": reason,
    }


def _parse_hits(html: str, *, limit: int) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    patterns = [HREF_RE, HREF_RE_ALT, GENERIC_A]
    for pattern in patterns:
        for match in pattern.finditer(html):
            href = unescape(match.group(1))
            title = TAG_RE.sub("", unescape(match.group(2))).strip()
            href = _clean_ddg_href(href)
            if not href or href in seen:
                continue
            if "duckduckgo.com" in urlparse(href).netloc:
                continue
            try:
                assess_fetch_url(href)
            except Exception:
                continue
            seen.add(href)
            hits.append(
                {
                    "url": href,
                    "title": title[:300] or href,
                    "snippet": "",
                    "adapter": "duckduckgo_lite",
                    "failed": False,
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def _clean_ddg_href(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/"):
        href = urljoin("https://lite.duckduckgo.com", href)
    return href
