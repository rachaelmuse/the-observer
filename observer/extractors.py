"""Heuristic extraction. Optional LLM extractor is UNAVAILABLE unless proven."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlparse

from observer.salvage import salvage

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
PROPER_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z]+)+)\b")
ORG_HINTS = (
    "Inc",
    "Corp",
    "Corporation",
    "LLC",
    "Ltd",
    "Company",
    "Commission",
    "Department",
    "Ministry",
    "University",
    "Agency",
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        return WS_RE.sub(" ", " ".join(self._chunks)).strip()


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return WS_RE.sub(" ", TAG_RE.sub(" ", html)).strip()
    return parser.text()


def extract_title(html: str, url: str) -> str:
    match = TITLE_RE.search(html or "")
    if match:
        return WS_RE.sub(" ", TAG_RE.sub("", match.group(1))).strip()[:300]
    host = urlparse(url).hostname or "unknown source"
    return host


def extract_publisher(url: str) -> str:
    return urlparse(url).hostname or "unknown"


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 40][:12]


def extract_entities(text: str) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    for match in PROPER_RE.finditer(text):
        name = match.group(1).strip()
        if name.lower() in seen or len(name) < 4:
            continue
        seen.add(name.lower())
        entity_type = "organization" if any(h in name for h in ORG_HINTS) else "person"
        found.append({"name": name, "entity_type": entity_type})
        if len(found) >= 12:
            break
    return found


def extract_from_document(html: str, url: str) -> dict:
    title = extract_title(html, url)
    text = html_to_text(html)
    excerpt = text[:1200]
    claim_texts = sentences(text)[:8]
    if not claim_texts and excerpt:
        claim_texts = [excerpt[:400]]
    claims = []
    for raw in claim_texts:
        for atom in salvage(raw):
            claims.append(atom)
    entities = extract_entities(text)
    relationships: list[dict] = []
    if len(entities) >= 2:
        relationships.append(
            {
                "from_name": entities[0]["name"],
                "to_name": entities[1]["name"],
                "rel_type": "mentioned_with",
                "inferred": True,
                "notes": "Co-occurrence in the same document is not documented control.",
            }
        )
    return {
        "title": title,
        "publisher": extract_publisher(url),
        "excerpt": excerpt,
        "text": text,
        "claims": claims,
        "entities": entities,
        "relationships": relationships,
        "facts": [],
    }


def llm_extractor_available() -> bool:
    """Slice 1: not proven. Do not call as if it ran."""
    from observer.settings import load_settings

    return bool(load_settings().ollama_model.strip())
