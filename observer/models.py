from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InvestigationRow(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="intake")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchRecordRow(Base):
    __tablename__ = "research_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    query: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, default="")
    publisher: Mapped[str] = mapped_column(String(255), default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    facts_json: Mapped[str] = mapped_column(Text, default="[]")
    claims_json: Mapped[str] = mapped_column(Text, default="[]")
    entities_json: Mapped[str] = mapped_column(Text, default="[]")
    relationships_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    verification_state: Mapped[str] = mapped_column(String(40), default="unreviewed")
    archive_path: Mapped[str] = mapped_column(Text, default="")


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    source_identity: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(80), default="general_reporting")
    publication_date: Mapped[str] = mapped_column(String(40), default="")
    original_source: Mapped[str] = mapped_column(Text, default="")
    secondary_source: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    known_affiliations: Mapped[str] = mapped_column(Text, default="")
    financial_interests: Mapped[str] = mapped_column(Text, default="")
    historical_accuracy: Mapped[str] = mapped_column(Text, default="")
    corroboration: Mapped[str] = mapped_column(Text, default="")
    contradictions: Mapped[str] = mapped_column(Text, default="")
    primary_document_available: Mapped[bool] = mapped_column(Boolean, default=False)
    source_reputation: Mapped[str] = mapped_column(String(80), default="unassessed")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    limitations: Mapped[str] = mapped_column(Text, default="")
    hierarchy: Mapped[str] = mapped_column(String(80), default="general_reporting")
    title: Mapped[str] = mapped_column(Text, default="")
    publisher: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), default="")


class ClaimRow(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="unknown")
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ids: Mapped[str] = mapped_column(Text, default="[]")
    contradictions: Mapped[str] = mapped_column(Text, default="[]")
    epistemic_kind: Mapped[str] = mapped_column(String(40), default="unknown")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    claim_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(80), default="excerpt")
    description: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    reliability: Mapped[float] = mapped_column(Float, default=0.0)
    corroboration_count: Mapped[int] = mapped_column(Integer, default=0)
    contradictions: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="unreviewed")


class EntityRow(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), default="organization")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[str] = mapped_column(Text, default="[]")


class RelationshipRow(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    from_entity: Mapped[str] = mapped_column(ForeignKey("entities.id"), nullable=False)
    to_entity: Mapped[str] = mapped_column(ForeignKey("entities.id"), nullable=False)
    rel_type: Mapped[str] = mapped_column(String(80), nullable=False)
    provenance_source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inferred: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class HypothesisRow(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    contradictory_evidence: Mapped[str] = mapped_column(Text, default="[]")
    missing_evidence: Mapped[str] = mapped_column(Text, default="[]")
    predictions: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    falsification_conditions: Mapped[str] = mapped_column(Text, default="[]")
    is_counter: Mapped[bool] = mapped_column(Boolean, default=False)


class ConclusionRow(Base):
    __tablename__ = "conclusions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditRow(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    checklist_json: Mapped[str] = mapped_column(Text, default="{}")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EditorialNoteRow(Base):
    __tablename__ = "editorial_notes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    author: Mapped[str] = mapped_column(String(80), default="human_editor")
    kind: Mapped[str] = mapped_column(String(40), default="dissent")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NoImmunityRow(Base):
    __tablename__ = "no_immunity"

    category: Mapped[str] = mapped_column(String(80), primary_key=True)
    notes: Mapped[str] = mapped_column(Text, default="Eligible for investigation. Not presumed guilty.")


class CapabilityRegistryRow(Base):
    __tablename__ = "capability_registry"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    last_proven_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ContradictionRow(Base):
    __tablename__ = "contradictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    claim_a_id: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_b_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_a_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_b_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(80), default="negation_polarity")
    reason: Mapped[str] = mapped_column(Text, default="")
    overlap: Mapped[str] = mapped_column(Text, default="[]")
    independent: Mapped[bool] = mapped_column(Boolean, default=False)
    same_publisher: Mapped[bool] = mapped_column(Boolean, default=False)
    publisher_a: Mapped[str] = mapped_column(String(255), default="")
    publisher_b: Mapped[str] = mapped_column(String(255), default="")


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), default="observer")
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target: Mapped[str] = mapped_column(String(80), default="")
    detail: Mapped[str] = mapped_column(Text, default="")


class PublicSubmissionRow(Base):
    """Phase IV intake. Submission is not verified evidence."""

    __tablename__ = "public_submissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classification: Mapped[str] = mapped_column(String(40), default="UNKNOWN")
    status: Mapped[str] = mapped_column(String(40), default="UNREVIEWED")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    investigation_id: Mapped[str] = mapped_column(String(64), default="")
    kind: Mapped[str] = mapped_column(String(40), default="submission")
