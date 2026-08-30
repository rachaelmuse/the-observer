"""Honest capability registry. CONNECTED only when proven."""

from __future__ import annotations

from observer.core import RegistryStatus, now
from observer.db import session_scope
from observer.models import CapabilityRegistryRow, NoImmunityRow

NO_IMMUNITY_CATEGORIES = [
    "government",
    "intelligence",
    "military",
    "police",
    "courts",
    "political_parties",
    "corporations",
    "banks",
    "investment_firms",
    "media",
    "hollywood",
    "technology_companies",
    "ai_companies",
    "nonprofits",
    "religious_organizations",
    "activist_organizations",
    "universities",
    "scientific_institutions",
    "celebrities",
    "influencers",
    "journalists",
    "conspiracy_theorists",
    "fact_checkers",
    "the_observer",
    "mythos",
    "vesper",
]

SEED: list[tuple[str, str, str]] = [
    ("identity", RegistryStatus.CONNECTED.value, "identity.json-equivalent loads from observer.identity"),
    ("audit_log", RegistryStatus.CONNECTED.value, "append-only audit_events table"),
    ("sqlite_persistence", RegistryStatus.CONNECTED.value, "SQLAlchemy SQLite round-trip"),
    ("investigation_create", RegistryStatus.CONNECTED.value, "POST /investigations persists a row"),
    ("question_engine", RegistryStatus.CONNECTED.value, "FACTS/PEOPLE/MONEY/POWER categories generated"),
    ("human_nature", RegistryStatus.CONNECTED.value, "ordinary vs manipulation pair generated"),
    ("claim_salvage", RegistryStatus.CONNECTED.value, "compound claims split into atomic claims"),
    ("url_intake", RegistryStatus.CONNECTED.value, "user-supplied public URLs accepted"),
    ("http_fetch", RegistryStatus.CONNECTED.value, "public HTTP fetch with hash archive"),
    ("web_search", RegistryStatus.CONNECTED.value, "DuckDuckGo lite; honest fail if blocked"),
    ("source_archive", RegistryStatus.CONNECTED.value, "immutable research_records + blob archive"),
    ("heuristic_extractor", RegistryStatus.CONNECTED.value, "claim/entity/relationship heuristics"),
    ("evidence_ledger", RegistryStatus.CONNECTED.value, "evidence rows with provenance"),
    ("entity_graph", RegistryStatus.CONNECTED.value, "NetworkX over relationships table"),
    ("hypotheses", RegistryStatus.CONNECTED.value, "competing hypotheses plus required counter"),
    ("contradiction_engine", RegistryStatus.CONNECTED.value, "negation-polarity conflicts recorded; same-publisher is not independent"),
    ("adversarial_audit", RegistryStatus.CONNECTED.value, "12-question examiner checklist"),
    ("required_report", RegistryStatus.CONNECTED.value, "required report sections written"),
    ("dashboard", RegistryStatus.CONNECTED.value, "static dashboard served at /"),
    ("no_immunity", RegistryStatus.CONNECTED.value, "eligibility registry; not a guilt list"),
    ("court_records", RegistryStatus.CONNECTED.value, "CourtListener public opinions only; not PACER"),
    ("corporate_registries", RegistryStatus.CONNECTED.value, "GLEIF public LEI records; not a secretary-of-state filing"),
    ("sec_filings", RegistryStatus.CONNECTED.value, "SEC EDGAR public 10-K/8-K/20-F copies; filer statements not findings"),
    ("patents", RegistryStatus.CONNECTED.value, "USPTO public patent PDF via bibliographic lookup; a grant is not proof of use"),
    ("procurement", RegistryStatus.CONNECTED.value, "USAspending public federal awards; an award is not proof of misconduct"),
    ("public_submission", RegistryStatus.CONNECTED.value, "public intake records UNREVIEWED; never auto-verified"),
    ("four_reviewers", RegistryStatus.UNAVAILABLE.value, "independent GPT/Grok/DeepSeek reviewers not seated"),
    ("public_fork", RegistryStatus.UNAVAILABLE.value, "investigation forks not seated"),
    ("malware_screen", RegistryStatus.UNAVAILABLE.value, "submission malware scanning not seated"),
    ("wayback", RegistryStatus.CONNECTED.value, "Internet Archive availability/CDX; public snapshots only"),
    ("neo4j", RegistryStatus.UNAVAILABLE.value, "NetworkX is the slice-1 graph backend"),
    ("postgresql", RegistryStatus.UNAVAILABLE.value, "SQLite is the slice-1 store"),
    ("redis", RegistryStatus.UNAVAILABLE.value, "no queue/cache backend seated"),
    ("faiss_qdrant", RegistryStatus.UNAVAILABLE.value, "no vector index seated"),
    ("ollama_extractor", RegistryStatus.UNAVAILABLE.value, "OLLAMA_MODEL unset or unproven"),
    ("media_desk_scraper", RegistryStatus.UNAVAILABLE.value, "entity types exist; specialized scrapers not seated"),
    ("hollywood_desk_scraper", RegistryStatus.UNAVAILABLE.value, "entity types exist; specialized scrapers not seated"),
    ("documentary_package", RegistryStatus.UNAVAILABLE.value, "cinematic/DaVinci package not seated"),
    ("auto_publish", RegistryStatus.DISABLED.value, "human editor only; AI cannot publish"),
    ("mythos_supervisor", RegistryStatus.DISABLED.value, "no external AI may alter conclusions"),
    ("vesper_supervisor", RegistryStatus.DISABLED.value, "Vesper may request; cannot supervise"),
]


def seed_registry() -> None:
    stamp = now().isoformat()
    with session_scope() as session:
        for cap_id, status, reason in SEED:
            row = session.get(CapabilityRegistryRow, cap_id)
            if row is None:
                session.add(
                    CapabilityRegistryRow(
                        id=cap_id,
                        status=status,
                        reason=reason,
                        last_proven_at=stamp if status == RegistryStatus.CONNECTED.value else None,
                    )
                )
            elif row.status != status or row.reason != reason:
                row.status = status
                row.reason = reason
                if status == RegistryStatus.CONNECTED.value:
                    row.last_proven_at = stamp
        for category in NO_IMMUNITY_CATEGORIES:
            if session.get(NoImmunityRow, category) is None:
                session.add(
                    NoImmunityRow(
                        category=category,
                        notes="Eligible for investigation. Not presumed guilty.",
                    )
                )


def list_registry() -> list[dict]:
    with session_scope() as session:
        rows = session.query(CapabilityRegistryRow).order_by(CapabilityRegistryRow.id).all()
        return [
            {
                "id": r.id,
                "status": r.status,
                "reason": r.reason,
                "last_proven_at": r.last_proven_at,
            }
            for r in rows
        ]


def get_capability(cap_id: str) -> dict | None:
    with session_scope() as session:
        row = session.get(CapabilityRegistryRow, cap_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "status": row.status,
            "reason": row.reason,
            "last_proven_at": row.last_proven_at,
        }


def mark_connected(cap_id: str, reason: str) -> dict:
    """Only for capabilities that actually ran in a test or live fetch."""
    with session_scope() as session:
        row = session.get(CapabilityRegistryRow, cap_id)
        if row is None:
            raise KeyError(cap_id)
        if row.status == RegistryStatus.DISABLED.value:
            raise PermissionError(f"{cap_id} is DISABLED and cannot be marked CONNECTED.")
        row.status = RegistryStatus.CONNECTED.value
        row.reason = reason
        row.last_proven_at = now().isoformat()
        return {"id": row.id, "status": row.status, "reason": row.reason}


def cannot_promote_unavailable_without_proof(cap_id: str) -> None:
    row = get_capability(cap_id)
    if row is None:
        raise KeyError(cap_id)
    if row["status"] != RegistryStatus.CONNECTED.value:
        raise PermissionError(
            f"{cap_id} is {row['status']}. Do not treat it as wired."
        )


def list_no_immunity() -> list[dict]:
    with session_scope() as session:
        rows = session.query(NoImmunityRow).order_by(NoImmunityRow.category).all()
        return [{"category": r.category, "notes": r.notes} for r in rows]
