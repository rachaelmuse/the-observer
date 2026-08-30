"""Public HTTP fetch with robots, size, and rate limits."""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from observer.core import content_hash, now
from observer.policy import PolicyDenied, assess_fetch_url, wrap_untrusted
from observer.settings import load_settings, resolve_path

_last_fetch_at = 0.0
_robots_cache: dict[str, RobotFileParser | None] = {}


class HttpFetchAdapter:
    adapter_id = "http_fetch"
    status = "connected"

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        return []

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        settings = load_settings()
        _respect_rate_limit(settings.observer_rate_limit_seconds)
        if not _robots_allows(url, settings.observer_user_agent):
            raise PolicyDenied(f"robots.txt disallows fetch of {url}")
        headers = {"User-Agent": settings.observer_user_agent, "Accept": "text/html,application/xhtml+xml,*/*"}
        with httpx.Client(follow_redirects=True, timeout=20.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.content[: settings.observer_max_fetch_bytes]
        digest = content_hash(data)
        archive_dir = resolve_path(settings.observer_archive_dir)
        archive_dir.mkdir(parents=True, exist_ok=True)
        blob = archive_dir / digest
        if not blob.exists():
            blob.write_bytes(data)
        text = data.decode(response.encoding or "utf-8", errors="replace")
        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_hash": digest,
            "archive_path": str(blob),
            "bytes": data,
            "text": text,
            "untrusted": wrap_untrusted(text[:8000]),
            "retrieved_at": now().isoformat(),
        }


def _respect_rate_limit(seconds: float) -> None:
    global _last_fetch_at
    wait = seconds - (time.time() - _last_fetch_at)
    if wait > 0:
        time.sleep(wait)
    _last_fetch_at = time.time()


def _robots_allows(url: str, user_agent: str) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(origin + "/", "robots.txt")
    if origin not in _robots_cache:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
            _robots_cache[origin] = parser
        except Exception:
            _robots_cache[origin] = None
    parser = _robots_cache[origin]
    if parser is None:
        return True
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True
