"""Public US federal award records via USAspending. An award is not proof of misconduct."""

from __future__ import annotations

import re

import httpx

from observer.policy import PolicyDenied, assess_fetch_url
from observer.research.http_fetch import HttpFetchAdapter
from observer.settings import load_settings

SEARCH_API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
AWARD_PAGE = "https://www.usaspending.gov/award/{award_id}/"
LIMITATION = (
    "USAspending.gov public award record. An award is not proof of misconduct, "
    "control, or complete spending history. Search matches are not identity resolution."
)
PROCURE_RE = re.compile(
    r"\b(contract|procurement|award|usaspending|sam\.gov|contractor|"
    r"federal contract|grant award)\b",
    re.I,
)


class ProcurementAdapter:
    adapter_id = "procurement"
    status = "connected"

    def __init__(self) -> None:
        self._fetch = HttpFetchAdapter()

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        if not PROCURE_RE.search(q):
            return [
                _fail(
                    "USAspending looks up a public federal award or contractor query, "
                    "not a free-text web question."
                )
            ]
        settings = load_settings()
        headers = {
            "User-Agent": settings.observer_user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        body = {
            "filters": {
                "keywords": [q[:120]],
                "award_type_codes": ["A", "B", "C", "D"],
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Awarding Agency",
                "Description",
                "generated_internal_id",
            ],
            "limit": max(1, limit),
            "page": 1,
        }
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.post(SEARCH_API, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [_fail(f"USAspending search failed: {exc}")]
        hits = _parse_awards(payload, limit=limit)
        return hits if hits else [_fail("no public federal award matched")]

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        if "usaspending.gov" not in url.lower():
            raise PolicyDenied("Procurement adapter fetches public usaspending.gov copies only.")
        result = self._fetch.fetch(url)
        result["adapter"] = self.adapter_id
        result["source_type"] = "government_record"
        return result


def _award_url(row: dict) -> str:
    award_id = str(row.get("generated_internal_id") or row.get("Award ID") or "").strip()
    if not award_id or "/" in award_id or ".." in award_id:
        return ""
    return AWARD_PAGE.format(award_id=award_id)


def _parse_awards(payload: object, *, limit: int) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results") or []
    if not isinstance(rows, list):
        return []
    hits: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = _award_url(row)
        if not url:
            continue
        try:
            assess_fetch_url(url)
        except PolicyDenied:
            continue
        title = str(row.get("Recipient Name") or row.get("Award ID") or url)[:300]
        amount = row.get("Award Amount")
        agency = str(row.get("Awarding Agency") or "")
        desc = str(row.get("Description") or "")
        snippet = " · ".join(p for p in (agency, f"${amount}" if amount is not None else "", desc) if p)
        hits.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet[:500],
                "adapter": "procurement",
                "failed": False,
                "source_type": "government_record",
                "limitations": LIMITATION,
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
        "adapter": "procurement",
        "failed": True,
        "reason": reason,
        "source_type": "government_record",
        "limitations": LIMITATION,
    }
