"""External reviewers. Interface exists. Nothing is sent until a real adapter is proven."""

from __future__ import annotations

from typing import Any, Protocol

from observer.core import RegistryStatus


class ReviewerAdapter(Protocol):
    def identity(self) -> dict[str, Any]: ...
    def capabilities(self) -> list[str]: ...
    def availability(self) -> dict[str, Any]: ...
    def submit_review(self, evidence_package: dict[str, Any]) -> dict[str, Any]: ...
    def receive_result(self, review_id: str) -> dict[str, Any]: ...
    def health_check(self) -> dict[str, Any]: ...


class UnavailableReviewer:
    def __init__(self, reviewer_id: str, reason: str) -> None:
        self.reviewer_id = reviewer_id
        self.reason = reason
        self.status = RegistryStatus.UNAVAILABLE.value

    def identity(self) -> dict[str, Any]:
        return {
            "id": self.reviewer_id,
            "name": self.reviewer_id,
            "type": "external_reviewer",
            "owns_family": False,
        }

    def capabilities(self) -> list[str]:
        return []

    def availability(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer_id,
            "status": "UNAVAILABLE",
            "adapter": "NOT CONFIGURED",
            "credentials": "NOT PRESENT",
            "last_verified": "NEVER",
            "reason": self.reason,
        }

    def submit_review(self, evidence_package: dict[str, Any]) -> dict[str, Any]:
        return {
            "review_id": None,
            "reviewer_identity": self.reviewer_id,
            "request_id": None,
            "evidence_package_hash": None,
            "status": "UNAVAILABLE",
            "adapter": "NOT CONFIGURED",
            "credentials": "NOT PRESENT",
            "last_verified": "NEVER",
            "limitations": self.reason,
        }

    def receive_result(self, review_id: str) -> dict[str, Any]:
        raise RuntimeError(
            f"{self.reviewer_id} is UNAVAILABLE: {self.reason}. No review {review_id!r}."
        )

    def health_check(self) -> dict[str, Any]:
        return self.availability()


gpt_reviewer = UnavailableReviewer("gpt", "independent GPT reviewer not seated")
grok_reviewer = UnavailableReviewer("grok", "independent Grok reviewer not seated")
deepseek_reviewer = UnavailableReviewer("deepseek", "independent DeepSeek reviewer not seated")
human_reviewer = UnavailableReviewer("human", "independent human reviewer desk not seated")
