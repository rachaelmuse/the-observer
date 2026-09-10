from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256


class ClaimStatus(str, Enum):
    DOCUMENTED = "documented"
    CORROBORATED = "corroborated"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    PLAUSIBLE = "plausible"
    UNVERIFIED = "unverified"
    REPORTED = "reported"
    CONTRADICTED = "contradicted"
    DISPUTED = "disputed"
    DISPROVEN = "disproven"
    SPECULATIVE = "speculative"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    CORROBORATED = "corroborated"
    CONTESTED = "contested"
    CONTRADICTED = "contradicted"
    DISPROVEN = "disproven"
    INCONCLUSIVE = "inconclusive"


class InvestigationStatus(str, Enum):
    IDEA = "idea"
    INTAKE = "intake"
    SCOPING = "scoping"
    RESEARCH = "research"
    EVIDENCE_COLLECTION = "evidence_collection"
    ENTITY_RESOLUTION = "entity_resolution"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    HYPOTHESIS_FORMATION = "hypothesis_formation"
    ADVERSARIAL_REVIEW = "adversarial_review"
    FACT_CHECK = "fact_check"
    EDITORIAL_REVIEW = "editorial_review"
    PUBLISHABLE = "publishable"
    PUBLISHED = "published"
    UPDATED = "updated"
    RETRACTED = "retracted"


class EpistemicKind(str, Enum):
    FACT = "fact"
    ANALYSIS = "analysis"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    ALLEGATION = "allegation"
    OPINION = "opinion"
    MODEL_GENERATED = "model_generated"
    UNKNOWN = "unknown"


class RegistryStatus(str, Enum):
    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class RelType(str, Enum):
    OWNS = "owns"
    CONTROLS = "controls"
    DIRECTS = "directs"
    FUNDS = "funds"
    INVESTS_IN = "invests_in"
    EMPLOYS = "employs"
    CONTRACTS_WITH = "contracts_with"
    SUED_BY = "sued_by"
    SUED = "sued"
    ACQUIRED = "acquired"
    ACQUIRED_BY = "acquired_by"
    PARTNERED_WITH = "partnered_with"
    LICENSED_TO = "licensed_to"
    LICENSED_FROM = "licensed_from"
    ADVERTISES_WITH = "advertises_with"
    SERVICES = "services"
    SITS_ON_BOARD = "sits_on_board"
    SHARES_ADDRESS = "shares_address"
    SHARES_DIRECTOR = "shares_director"
    REPORTS_ON = "reports_on"
    CITES = "cites"
    AMPLIFIES = "amplifies"
    CONTRADICTS = "contradicts"
    MENTIONED_WITH = "mentioned_with"


@dataclass
class Source:
    source_id: str
    title: str
    publisher: str
    url: str
    source_type: str
    retrieved_at: datetime
    content_hash: str
    notes: str = ""


@dataclass
class Claim:
    claim_id: str
    investigation_id: str
    text: str
    status: ClaimStatus = ClaimStatus.UNKNOWN
    confidence: float = 0.0
    source_ids: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    evidence_id: str
    investigation_id: str
    claim_id: str
    source_id: str
    description: str
    status: EvidenceStatus = EvidenceStatus.UNREVIEWED
    reliability: float = 0.0
    relevance: float = 0.0


@dataclass
class Hypothesis:
    hypothesis_id: str
    investigation_id: str
    text: str
    supporting_evidence: list[str] = field(default_factory=list)
    contradictory_evidence: list[str] = field(default_factory=list)
    falsification_conditions: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class Investigation:
    investigation_id: str
    question: str
    created_at: datetime
    status: str = InvestigationStatus.IDEA.value
    claims: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)


def content_hash(content: str | bytes) -> str:
    if isinstance(content, str):
        payload = content.encode("utf-8")
    else:
        payload = content
    return sha256(payload).hexdigest()


def now() -> datetime:
    return datetime.now(UTC)
