"""User-supplied public URLs. Always CONNECTED."""

from __future__ import annotations

from observer.policy import PolicyDenied, assess_fetch_url


class UrlIntakeAdapter:
    adapter_id = "url_intake"
    status = "connected"

    def intake(self, urls: list[str]) -> list[str]:
        accepted: list[str] = []
        for raw in urls:
            url = (raw or "").strip()
            if not url:
                continue
            assess_fetch_url(url)
            accepted.append(url)
        if not accepted and urls:
            raise PolicyDenied("No allowed public URLs in intake.")
        return accepted

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        return []

    def fetch(self, url: str) -> dict:
        raise NotImplementedError("Use HttpFetchAdapter for fetch.")
