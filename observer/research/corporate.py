"""Public legal-entity records via GLEIF. Not a secretary-of-state filing."""

from __future__ import annotations

import re

import httpx

from observer.policy import PolicyDenied, assess_fetch_url
from observer.research.http_fetch import HttpFetchAdapter
from observer.settings import load_settings

SEARCH_API = "https://api.gleif.org/api/v1/lei-records"
RECORD_URL = "https://api.gleif.org/api/v1/lei-records/{lei}"
LIMITATION = (
    "GLEIF LEI record. Not a secretary-of-state filing. "
    "Not beneficial ownership. Not proof of control."
)
LEI_RE = re.compile(r"^[A-Z0-9]{20}$")
ENTITY_RE = re.compile(
    r"\b(inc\.?|llc|ltd\.?|plc|corp\.?|corporation|company|"
    r"organization|organisation|gmbh|incorporated|lei)\b",
    re.I,
)


class CorporateRegistriesAdapter:
    adapter_id = "corporate_registries"
    status = "connected"

    def __init__(self) -> None:
        self._fetch = HttpFetchAdapter()

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        if not _looks_like_entity_query(q):
            return [
                _fail(
                    "GLEIF looks up a legal entity name or LEI, not a free-text web question."
                )
            ]
        settings = load_settings()
        headers = {
            "User-Agent": settings.observer_user_agent,
            "Accept": "application/vnd.api+json, application/json",
        }
        params: dict[str, str] = {"page[size]": str(max(1, limit))}
        compact = re.sub(r"\s+", "", q).upper()
        if LEI_RE.match(compact):
            params["filter[lei]"] = compact
        else:
            params["filter[entity.legalName]"] = q[:200]
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(SEARCH_API, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [_fail(f"GLEIF search failed: {exc}")]
        hits = _parse_lei_records(payload, limit=limit)
        return hits if hits else [_fail("no GLEIF LEI record matched")]

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        result = self._fetch.fetch(url)
        result["adapter"] = self.adapter_id
        result["source_type"] = "corporate_filing"
        return result


def _looks_like_entity_query(query: str) -> bool:
    compact = re.sub(r"\s+", "", query).upper()
    if LEI_RE.match(compact):
        return True
    return bool(ENTITY_RE.search(query))


def _parse_lei_records(payload: object, *, limit: int) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data") or []
    if not isinstance(rows, list):
        return []
    hits: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        attrs = row.get("attributes") or {}
        if not isinstance(attrs, dict):
            attrs = {}
        lei = str(attrs.get("lei") or row.get("id") or "").strip().upper()
        if not LEI_RE.match(lei):
            continue
        url = RECORD_URL.format(lei=lei)
        try:
            assess_fetch_url(url)
        except PolicyDenied:
            continue
        entity = attrs.get("entity") or {}
        if not isinstance(entity, dict):
            entity = {}
        name = _legal_name(entity)
        jurisdiction = str(entity.get("jurisdiction") or "")
        status = str(entity.get("status") or "")
        registered = str(entity.get("registeredAs") or "")
        title = name or lei
        snippet = " · ".join(p for p in (lei, jurisdiction, status, registered) if p)
        hits.append(
            {
                "url": url,
                "title": title[:300],
                "snippet": snippet[:500],
                "adapter": "corporate_registries",
                "failed": False,
                "lei": lei,
                "source_type": "corporate_filing",
                "limitations": LIMITATION,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def _legal_name(entity: dict) -> str:
    raw = entity.get("legalName")
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    return str(raw or "").strip()


def _fail(reason: str) -> dict:
    return {
        "url": "",
        "title": "",
        "snippet": "",
        "adapter": "corporate_registries",
        "failed": True,
        "reason": reason,
        "source_type": "corporate_filing",
        "limitations": LIMITATION,
    }
