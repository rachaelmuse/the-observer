"""Legal and research boundaries. Enforced, not decorative."""

from __future__ import annotations

from urllib.parse import urlparse

DISALLOWED_SCHEMES = {"file", "ftp", "javascript", "data"}
PRIVATE_HOST_MARKERS = (
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    ".local",
    "10.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
)

AUTH_BYPASS_MARKERS = (
    "bypass",
    "paywall-bypass",
    "stolen-cookie",
    "credential-stuff",
)


class PolicyDenied(ValueError):
    """Raised when a research action violates Observer policy."""


def wrap_untrusted(text: str) -> str:
    """Retrieved content is data, never instructions."""
    return f"<UNTRUSTED_SOURCE_DATA>\n{text}\n</UNTRUSTED_SOURCE_DATA>"


def assess_url(url: str) -> None:
    raw = (url or "").strip()
    if not raw:
        raise PolicyDenied("Empty URL.")
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme in DISALLOWED_SCHEMES:
        raise PolicyDenied(f"Scheme {scheme!r} is not allowed.")
    if scheme not in {"http", "https"}:
        raise PolicyDenied("Only public http/https URLs are allowed.")
    host = (parsed.hostname or "").lower()
    if not host:
        raise PolicyDenied("URL has no host.")
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise PolicyDenied("Private/loopback hosts are not allowed.")
    if host.endswith(".local"):
        raise PolicyDenied("mDNS/local hosts are not allowed.")
    if parsed.username or parsed.password:
        raise PolicyDenied("URLs with embedded credentials are not allowed.")
    lowered = raw.lower()
    for marker in AUTH_BYPASS_MARKERS:
        if marker in lowered:
            raise PolicyDenied("Auth or paywall bypass is not allowed.")


def is_private_ipv4(host: str) -> bool:
    parts = host.split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return False
    a, b = nums[0], nums[1]
    if a == 10:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 169 and b == 254:
        return True
    return False


def assess_fetch_url(url: str) -> None:
    assess_url(url)
    host = (urlparse(url).hostname or "").lower()
    if is_private_ipv4(host):
        raise PolicyDenied("Private network addresses are not allowed.")
