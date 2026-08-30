"""Public SEC EDGAR filings. A filing is the filer's statement, not a finding of fact."""

from __future__ import annotations

import re

import httpx

from observer.policy import PolicyDenied, assess_fetch_url
from observer.research.http_fetch import HttpFetchAdapter
from observer.settings import load_settings

SEARCH_API = "https://efts.sec.gov/LATEST/search-index"
LIMITATION = (
    "SEC EDGAR public filing copy. A filing is a statement by the filer, not a finding of fact. "
    "Search matches are not identity resolution."
)
FILING_RE = re.compile(
    r"\b(inc\.?|llc|ltd\.?|plc|corp\.?|corporation|company|"
    r"organization|organisation|gmbh|incorporated|lei|"
    r"sec|edgar|10-k|10k|8-k|8k|20-f|cik)\b",
    re.I,
)


class SecFilingsAdapter:
    adapter_id = "sec_filings"
    status = "connected"

    def __init__(self) -> None:
        self._fetch = HttpFetchAdapter()

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return [_fail("empty query")]
        if not FILING_RE.search(q):
            return [_fail("SEC EDGAR looks up a filer or form type, not a free-text web question.")]
        settings = load_settings()
        headers = {
            "User-Agent": settings.observer_user_agent,
            "Accept": "application/json",
        }
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(
                    SEARCH_API,
                    params={"q": q[:200], "forms": "10-K,8-K,20-F", "dateRange": "all"},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [_fail(f"SEC EDGAR search failed: {exc}")]
        hits = _parse_efts(payload, limit=limit)
        return hits if hits else [_fail("no public EDGAR filing matched")]

    def fetch(self, url: str) -> dict:
        assess_fetch_url(url)
        host = url.lower()
        if "sec.gov" not in host:
            raise PolicyDenied("SEC adapter fetches public sec.gov filing copies only.")
        result = self._fetch.fetch(url)
        result["adapter"] = self.adapter_id
        result["source_type"] = "financial_record"
        return result


def _edgar_document_url(row: dict) -> str:
    source = row.get("_source") or {}
    if not isinstance(source, dict):
        source = {}
    raw_id = str(row.get("_id") or "")
    if ":" not in raw_id:
        return ""
    accession, filename = raw_id.split(":", 1)
    filename = filename.strip().lstrip("/")
    if not accession or not filename or ".." in filename:
        return ""
    ciks = source.get("ciks") or []
    if not isinstance(ciks, list) or not ciks:
        return ""
    cik = str(ciks[0]).strip().lstrip("0") or "0"
    acc = accession.replace("-", "")
    if not acc.isdigit():
        return ""
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{filename}"


def _parse_efts(payload: object, *, limit: int) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    hits_block = (payload.get("hits") or {}).get("hits") or []
    if not isinstance(hits_block, list):
        return []
    hits: list[dict] = []
    for row in hits_block:
        if not isinstance(row, dict):
            continue
        url = _edgar_document_url(row)
        if not url:
            continue
        try:
            assess_fetch_url(url)
        except PolicyDenied:
            continue
        source = row.get("_source") or {}
        names = source.get("display_names") or []
        title = str(names[0] if names else url)[:300]
        forms = source.get("root_forms") or []
        form = str(forms[0] if forms else "")
        filed = str(source.get("file_date") or "")
        snippet = " · ".join(p for p in (form, filed) if p)
        hits.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet[:500],
                "adapter": "sec_filings",
                "failed": False,
                "form": form,
                "source_type": "financial_record",
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
        "adapter": "sec_filings",
        "failed": True,
        "reason": reason,
        "source_type": "financial_record",
        "limitations": LIMITATION,
    }
