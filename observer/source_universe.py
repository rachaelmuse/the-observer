"""Source universe: searchable environments, not an approved-news whitelist."""

from __future__ import annotations

from urllib.parse import urlparse

# Discovery environments. None of these is a truth verdict.
SOURCE_NETWORKS = (
    "PUBLIC_WEB",
    "OPEN_GOVERNMENT_DATA",
    "COURT_RECORDS",
    "PUBLIC_RECORDS",
    "ACADEMIC",
    "SCIENTIFIC_REPOSITORY",
    "OPEN_DATASET",
    "PUBLIC_ARCHIVE",
    "DIGITAL_LIBRARY",
    "INDEPENDENT_JOURNALISM",
    "LOCAL_JOURNALISM",
    "INVESTIGATIVE_JOURNALISM",
    "WHISTLEBLOWER",
    "NONPROFIT_RESEARCH",
    "TECHNICAL_DOCUMENTATION",
    "OSINT",
    "SOCIAL_MEDIA",
    "PUBLIC_FORUM",
    "PUBLIC_VIDEO",
    "PUBLIC_AUDIO",
    "MIRROR",
    "CENSORSHIP_RESISTANT",
    "DECENTRALIZED",
    "FREENET",
    "I2P",
    "TOR_PUBLIC",
    "IPFS",
    "PUBLIC_GIT",
    "YOUTUBE",
    "OTHER_LAWFUL_PUBLIC",
)

SOURCE_CLASSES = (
    "NEWS_MEDIA",
    "GOVERNMENT",
    "COURT",
    "ACADEMIC",
    "TECHNICAL",
    "CITIZEN",
    "SOCIAL",
    "VIDEO",
    "AUDIO",
    "ARCHIVE",
    "DECENTRALIZED",
    "ANONYMOUS",
    "CORPORATE",
    "NONPROFIT",
    "PRIMARY_DOCUMENT",
    "SECONDARY_REPORT",
    "USER_SUBMITTED",
    "OTHER",
)

# Live adapters. Types exist even when fetch is UNAVAILABLE.
NETWORK_ADAPTER_STATUS = {
    "PUBLIC_WEB": "connected",
    "FREENET": "unavailable",
    "I2P": "unavailable",
    "TOR_PUBLIC": "unavailable",
    "IPFS": "unavailable",
}


class NewsWhitelistForbidden(ValueError):
    """Raised if an investigation is gated to approved journalism brands."""


def classify_source_network(uri: str) -> str:
    raw = (uri or "").strip().lower()
    if raw.startswith("freenet:") or raw.startswith("chk@") or ".freenet" in raw:
        return "FREENET"
    if raw.startswith("i2p:") or raw.endswith(".i2p") or ".i2p/" in raw:
        return "I2P"
    if ".onion" in raw or raw.startswith("tor:"):
        return "TOR_PUBLIC"
    if raw.startswith("ipfs://") or "/ipfs/" in raw:
        return "IPFS"
    host = (urlparse(raw).hostname or "").lower()
    if host in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}:
        return "YOUTUBE"
    if host in {"github.com", "www.github.com", "gitlab.com", "www.gitlab.com"}:
        return "PUBLIC_GIT"
    if host.endswith(".gov") or ".gov." in host:
        return "OPEN_GOVERNMENT_DATA"
    if any(x in host for x in ("courtlistener.com", "supremecourt.gov", "uscourts.gov")):
        return "COURT_RECORDS"
    if "web.archive.org" in host or "archive.org" in host:
        return "PUBLIC_ARCHIVE"
    if any(x in host for x in ("twitter.com", "x.com", "facebook.com", "reddit.com", "tiktok.com")):
        return "SOCIAL_MEDIA"
    if host.endswith(".onion"):
        return "TOR_PUBLIC"
    scheme = urlparse(raw).scheme
    if scheme in {"http", "https"}:
        return "PUBLIC_WEB"
    return "OTHER_LAWFUL_PUBLIC"


def classify_source_class(uri: str, *, declared: str = "") -> str:
    if declared and declared.upper() in SOURCE_CLASSES:
        return declared.upper()
    network = classify_source_network(uri)
    mapping = {
        "YOUTUBE": "VIDEO",
        "PUBLIC_GIT": "TECHNICAL",
        "OPEN_GOVERNMENT_DATA": "GOVERNMENT",
        "COURT_RECORDS": "COURT",
        "PUBLIC_ARCHIVE": "ARCHIVE",
        "SOCIAL_MEDIA": "SOCIAL",
        "FREENET": "DECENTRALIZED",
        "I2P": "DECENTRALIZED",
        "TOR_PUBLIC": "DECENTRALIZED",
        "IPFS": "DECENTRALIZED",
    }
    return mapping.get(network, "OTHER")


def network_search_status(network: str) -> str:
    """Honest access: UNAVAILABLE is not 'no evidence on that network'."""
    status = NETWORK_ADAPTER_STATUS.get(network, "unavailable")
    if status == "unavailable":
        return f"NOT SEARCHED — adapter unavailable ({network})"
    return "SEARCHABLE"


def refuse_news_only_gate(allowed_source_classes: list[str] | None) -> None:
    if not allowed_source_classes:
        return
    narrowed = {c.upper() for c in allowed_source_classes}
    if narrowed and narrowed <= {"NEWS_MEDIA", "MAINSTREAM_NEWS", "APPROVED_JOURNALISM"}:
        raise NewsWhitelistForbidden(
            "Mainstream-news-only is not an epistemic gate. News is one source class."
        )


def discovery_vs_evidence(
    *,
    discovery_uri: str,
    article_uri: str,
    primary_uri: str,
) -> dict:
    """Search hit, linking article, and underlying document are not three independent sources."""
    return {
        "discovery_source": discovery_uri,
        "secondary_source": article_uri,
        "evidence_source": primary_uri,
        "independent_count": 1 if primary_uri else 0,
        "note": "Discovery mechanism is not corroboration.",
    }


def independence_groups(uris: list[str], *, origin_map: dict[str, str] | None = None) -> dict:
    """Copies / syndications share an origin group. Ten copies remain one source."""
    origin_map = origin_map or {}
    groups: dict[str, list[str]] = {}
    for uri in uris:
        origin = origin_map.get(uri) or classify_source_network(uri) + ":" + (
            urlparse(uri).hostname or uri
        )
        groups.setdefault(origin, []).append(uri)
    independent = len(groups)
    copies = sum(len(v) for v in groups.values()) - independent
    return {
        "groups": groups,
        "independent_count": independent,
        "copy_count": max(0, copies),
        "independent_corroboration": independent >= 2,
    }
