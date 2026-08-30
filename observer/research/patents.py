"""Public USPTO patent records. A grant is not proof of use or infringement."""

from __future__ import annotations

import json
import re

import httpx

from observer.policy import PolicyDenied, assess_fetch_url
from observer.research.http_fetch import HttpFetchAdapter
from observer.settings import load_settings

PUBCHEM_SDQ = "https://pubchem.ncbi.nlm.nih.gov/sdq/sdqagent.cgi"
PDF_URL = "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{digits}"
LIMITATION = (
    "USPTO public patent PDF identified from a public bibliographic record. "
    "A grant is not proof of commercial use, control, or infringement. "
    "Search matches are not identity resolution."
)
PATENT_RE = re.compile(
    r"\b(patent|uspto|inventor|assignee|utility model|publication number|"
    r"us[- ]?\d{6,}|wo[- ]?\d{4,})\b",
    re.I,
)


class PatentsAdapter:
    adapter_id = "patents"
    status = "connected"

    def __init__(self) -> None:
        self._fetch = HttpFetchAdapter()

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        if not PATENT_RE.search(q):
            return [_fail("USPTO looks up a patent number or patent-related query, not a free-text web question.")]
        settings = load_settings()
        headers = {
            "User-Agent": settings.observer_user_agent,
            "Accept": "application/json",
        }
        sdq = {
            "download": "*",
            "collection": "patent",
            "where": {"ands": [{"*": q[:120]}]},
            "order": ["relevancescore,desc"],
            "start": 1,
            "limit": max(1, limit),
        }
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(
                    PUBCHEM_SDQ,
                    params={"infmt": "json", "outfmt": "json", "query": json.dumps(sdq)},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [_fail(f"patent search failed: {exc}")]
        hits = _parse_uspto(payload, limit=limit)
        return hits if hits else [_fail("no public patent record matched")]

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        if "uspto.gov" not in url.lower():
            raise PolicyDenied("Patents adapter fetches public uspto.gov copies only.")
        result = self._fetch.fetch(url)
        result["adapter"] = self.adapter_id
        result["source_type"] = "government_record"
        return result


def _patent_public_url(patent_number: str) -> str:
    cleaned = re.sub(r"^(US|WO|EP|JP|CN)", "", (patent_number or "").upper())
    cleaned = re.sub(r"[A-Z]\d*$", "", cleaned)
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return ""
    return PDF_URL.format(digits=digits)


def _parse_uspto(payload: object, *, limit: int) -> list[dict]:
    rows: list[object]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = (
            ((payload.get("response") or {}) if isinstance(payload.get("response"), dict) else {}).get("docs")
            or payload.get("data")
            or []
        )
        if not isinstance(rows, list):
            rows = []
    else:
        return []
    hits: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        number = str(
            row.get("patentNumber")
            or row.get("publicationnumber")
            or row.get("publicationNumber")
            or ""
        ).strip()
        url = _patent_public_url(number)
        if not url:
            continue
        try:
            assess_fetch_url(url)
        except PolicyDenied:
            continue
        title = str(row.get("inventionTitle") or row.get("title") or number)[:300]
        assignees = row.get("assigneeEntityName") or []
        assignee = assignees[0] if isinstance(assignees, list) and assignees else ""
        filed = str(row.get("publicationDate") or "")
        snippet = " · ".join(p for p in (number, str(assignee), filed) if p)
        hits.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet[:500],
                "adapter": "patents",
                "failed": False,
                "patent_number": number,
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
        "adapter": "patents",
        "failed": True,
        "reason": reason,
        "source_type": "government_record",
        "limitations": LIMITATION,
    }
