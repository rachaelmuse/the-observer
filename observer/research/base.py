"""Research adapter protocol. Implementations must not pretend."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ResearchAdapter(Protocol):
    adapter_id: str
    status: str  # connected | unavailable | disabled

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        """Return hits or a single honest-failure record. Never invent URLs."""

    def fetch(self, url: str) -> dict:
        """Return bytes/text payload or raise."""
