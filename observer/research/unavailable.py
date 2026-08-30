"""Unavailable research adapters. Interfaces exist. They do not fetch."""

from __future__ import annotations

from observer.core import RegistryStatus


class UnavailableAdapter:
    def __init__(self, adapter_id: str, reason: str) -> None:
        self.adapter_id = adapter_id
        self.status = RegistryStatus.UNAVAILABLE.value
        self.reason = reason

    def search(self, query: str, *, limit: int = 5) -> list[dict]:
        return [
            {
                "url": "",
                "title": "",
                "snippet": "",
                "adapter": self.adapter_id,
                "failed": True,
                "reason": self.reason,
                "status": self.status,
            }
        ]

    def fetch(self, url: str) -> dict:
        raise RuntimeError(
            f"{self.adapter_id} is UNAVAILABLE: {self.reason}. Do not treat this as a fetch."
        )


four_reviewers = UnavailableAdapter("four_reviewers", "independent model reviewers not seated")

UNAVAILABLE_ADAPTERS = [
    four_reviewers,
]
