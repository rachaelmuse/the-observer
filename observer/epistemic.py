"""Epistemic integrity: claims preserved; truth status earned. Not a soft server."""

from __future__ import annotations

import json
import re
import uuid

from observer import audit as audit_mod
from observer.core import ClaimStatus, EpistemicKind, now
from observer.db import session_scope
from observer.models import (
    AccessFailureRow,
    BlindSpotRow,
    ClaimRow,
    ClaimStatusHistoryRow,
    ExaminerFindingRow,
    ObserverErrorRow,
)

CERTAIN = frozenset(
    {
        ClaimStatus.VERIFIED.value,
        ClaimStatus.CORROBORATED.value,
        ClaimStatus.DISPROVEN.value,
    }
)

OPEN_STATES = frozenset(
    {
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.UNKNOWN.value,
        ClaimStatus.REPORTED.value,
        ClaimStatus.SPECULATIVE.value,
        ClaimStatus.PLAUSIBLE.value,
        ClaimStatus.INSUFFICIENT_EVIDENCE.value,
        ClaimStatus.UNRESOLVED.value,
        ClaimStatus.DISPUTED.value,
        ClaimStatus.CONTRADICTED.value,
    }
)

COMPREHENSIVE_MARKERS = re.compile(
    r"\b(how many|everything|complete totals?|all sources|don't leave|"
    r"do not leave|don't cherry|what is happening|give me everything|"
    r"complete picture|don't forget)\b",
    re.I,
)


class EpistemicDenied(ValueError):
    """Raised when a status change would lie."""


def public_false_label(status: str) -> str | None:
    """FALSE is a publication classification only after DISPROVEN."""
    if status == ClaimStatus.DISPROVEN.value:
        return "FALSE"
    return None


def absence_of_evidence_status() -> str:
    return ClaimStatus.INSUFFICIENT_EVIDENCE.value


def model_output_kind() -> str:
    return EpistemicKind.MODEL_GENERATED.value


def model_output_is_evidence(kind: str) -> bool:
    return False if kind == EpistemicKind.MODEL_GENERATED.value else kind == EpistemicKind.FACT.value


def official_denial_disproves() -> bool:
    return False


def fringe_source_invalidates() -> bool:
    return False


def search_popularity_raises_status() -> bool:
    return False


def political_identity_weights_evidence() -> bool:
    return False


def prestige_substitutes_for_evidence() -> bool:
    return False


def creator_assertion_is_evidence() -> bool:
    return False


def may_promote(
    current: str,
    target: str,
    *,
    evidence_count: int = 0,
    independent_source_count: int = 0,
    has_provenance: bool = False,
    functional_test_ran: bool = False,
    determination_path: bool = False,
    examiner_agrees: bool | None = None,
    unresolved_contradiction: bool = False,
    inferred_only: bool = False,
    official_denied: bool = False,
    copies_of_one_origin: int = 0,
) -> tuple[bool, str]:
    """Machine gate. Preserve the claim either way; do not earn truth by assertion."""
    current = current or ClaimStatus.UNKNOWN.value
    target = (target or "").lower()

    if target in {ClaimStatus.UNVERIFIED.value, ClaimStatus.REPORTED.value, ClaimStatus.UNKNOWN.value}:
        return True, "claim retained without promotion"

    if target in {ClaimStatus.INSUFFICIENT_EVIDENCE.value, ClaimStatus.UNRESOLVED.value}:
        return True, "uncertainty preserved"

    if target == ClaimStatus.CORROBORATED.value:
        if independent_source_count < 2:
            return False, "one source (or copies of one origin) cannot create CORROBORATED"
        if copies_of_one_origin and independent_source_count < 2:
            return False, "copies are distribution, not independent corroboration"
        return True, "independent sources corroborate"

    if target == ClaimStatus.VERIFIED.value:
        if unresolved_contradiction:
            return False, "unresolved material contradiction blocks VERIFIED"
        if inferred_only:
            return False, "inference from another system is not VERIFIED"
        if not has_provenance:
            return False, "missing provenance prevents VERIFIED"
        if not functional_test_ran:
            return False, "functional test did not run; do not mark VERIFIED"
        if evidence_count < 1:
            return False, "unverified claim is not promoted to VERIFIED"
        if examiner_agrees is not True:
            return False, "Examiner must challenge before VERIFIED; Investigator cannot skip or force agreement"
        return True, "provenance + test + no blocking examiner dissent"

    if target == ClaimStatus.DISPROVEN.value:
        if evidence_count < 1 and not determination_path:
            return False, "no evidence does not become FALSE / DISPROVEN"
        if official_denied and not determination_path:
            return False, "official denial does not automatically disprove a claim"
        if not determination_path:
            return False, "PROVEN_FALSE / DISPROVEN requires a determination path"
        return True, "determination path recorded"

    if target == ClaimStatus.CONTRADICTED.value:
        return True, "contradiction preserved"

    if target in {
        ClaimStatus.DOCUMENTED.value,
        ClaimStatus.PARTIALLY_VERIFIED.value,
        ClaimStatus.DISPUTED.value,
        ClaimStatus.PLAUSIBLE.value,
        ClaimStatus.SPECULATIVE.value,
    }:
        if target == ClaimStatus.DOCUMENTED.value and evidence_count < 1:
            return False, "documented requires at least one artifact"
        return True, "intermediate state"

    return False, f"unknown or forbidden target {target!r}"


def assess_missing_evidence() -> dict:
    status = absence_of_evidence_status()
    return {
        "status": status,
        "public_false": public_false_label(status),
        "note": "Absence of evidence is not evidence of falsehood. Claim is retained.",
    }


def requires_comprehensive_mode(question: str) -> bool:
    return bool(COMPREHENSIVE_MARKERS.search(question or ""))


def complete_total_report(
    *,
    question: str,
    confirmed: list,
    probable: list,
    unresolved: list,
    headline_only: list | None = None,
    source_classes_searched: list[str] | None = None,
    networks_searched: list[str] | None = None,
    complete_total_obtainable: bool,
    collection_ended: str,
) -> dict:
    """Never substitute a handful of headlines for an auditable count."""
    comprehensive = requires_comprehensive_mode(question)
    headlines = headline_only or []
    classes = source_classes_searched or []
    if comprehensive and headlines and not confirmed and not probable and not unresolved:
        raise EpistemicDenied(
            "Comprehensive mode cannot terminate after a predetermined number of headline stories."
        )
    if comprehensive and "NEWS_MEDIA" in classes and len(classes) == 1:
        raise EpistemicDenied("Mainstream-only search is insufficient for COMPREHENSIVE mode.")
    return {
        "mode": "COMPREHENSIVE" if comprehensive else "BOUNDED",
        "confirmed": list(confirmed),
        "probable": list(probable),
        "unresolved": list(unresolved),
        "total_confirmed": len(confirmed),
        "total_probable": len(probable),
        "total_unresolved": len(unresolved),
        "complete_total_obtainable": complete_total_obtainable,
        "collection_ended": collection_ended,
        "note": (
            None
            if complete_total_obtainable
            else "No authoritative complete total is obtainable. This is an auditable partial ledger, not the picture."
        ),
        "we_report_what_we_find": True,
    }


def classify_civil_incident(
    *,
    protest_link_evidence: bool,
    police_present: bool,
    violent_crime: bool,
    peaceful_assembly: bool,
) -> str:
    if violent_crime and not protest_link_evidence:
        return "GENERAL_VIOLENCE"
    if peaceful_assembly and police_present and not protest_link_evidence:
        return "PEACEFUL_PROTEST"
    if protest_link_evidence and violent_crime:
        return "PROTEST_RELATED_VIOLENCE"
    if protest_link_evidence:
        return "PROTEST"
    return "UNCLASSIFIED"


def classify_user_media(*, authenticated: bool) -> str:
    return "EVIDENCE" if authenticated else "LEAD"


def event_temporal_state(*, article_is_current: bool, described_as_active: bool) -> str:
    if described_as_active and not article_is_current:
        return "UNKNOWN"
    if described_as_active:
        return "ACTIVE"
    return "CONCLUDED" if article_is_current else "UNKNOWN"


def operational_crime_assistance_allowed() -> bool:
    return False


def _history(claim_id: str, investigation_id: str, previous: str, new: str, reason: str, refs: list[str], actor: str) -> None:
    with session_scope() as session:
        session.add(
            ClaimStatusHistoryRow(
                id=f"csh_{uuid.uuid4().hex[:12]}",
                claim_id=claim_id,
                investigation_id=investigation_id,
                previous_status=previous,
                new_status=new,
                reason=reason,
                evidence_refs=json.dumps(refs),
                actor=actor,
                created_at=now(),
            )
        )


def promote_claim(
    claim_id: str,
    target: str,
    *,
    evidence_ids: list[str] | None = None,
    independent_source_count: int = 0,
    has_provenance: bool = False,
    functional_test_ran: bool = False,
    determination_path: bool = False,
    examiner_agrees: bool | None = None,
    unresolved_contradiction: bool = False,
    inferred_only: bool = False,
    official_denied: bool = False,
    copies_of_one_origin: int = 0,
    reason: str = "",
    actor: str = "observer",
) -> dict:
    refs = list(evidence_ids or [])
    with session_scope() as session:
        claim = session.get(ClaimRow, claim_id)
        if claim is None:
            raise KeyError(claim_id)
        current = claim.status
        ok, note = may_promote(
            current,
            target,
            evidence_count=len(refs),
            independent_source_count=independent_source_count,
            has_provenance=has_provenance,
            functional_test_ran=functional_test_ran,
            determination_path=determination_path,
            examiner_agrees=examiner_agrees,
            unresolved_contradiction=unresolved_contradiction,
            inferred_only=inferred_only,
            official_denied=official_denied,
            copies_of_one_origin=copies_of_one_origin,
        )
        if not ok:
            raise EpistemicDenied(note)
        claim.status = target
        investigation_id = claim.investigation_id
    _history(claim_id, investigation_id, current, target, reason or note, refs, actor)
    audit_mod.record("claim_status_change", target=claim_id, detail=f"{current}->{target}: {reason or note}")
    return {"claim_id": claim_id, "previous": current, "status": target, "reason": reason or note}


def list_claim_history(claim_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(ClaimStatusHistoryRow)
            .filter(ClaimStatusHistoryRow.claim_id == claim_id)
            .order_by(ClaimStatusHistoryRow.created_at)
            .all()
        )
        return [
            {
                "id": r.id,
                "previous_status": r.previous_status,
                "new_status": r.new_status,
                "reason": r.reason,
                "evidence_refs": json.loads(r.evidence_refs or "[]"),
                "actor": r.actor,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


def record_examiner_finding(
    investigation_id: str,
    *,
    claim_id: str,
    investigator_status: str,
    examiner_status: str,
    challenge: str,
) -> dict:
    agrees = examiner_status == investigator_status
    fid = f"ex_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            ExaminerFindingRow(
                id=fid,
                investigation_id=investigation_id,
                claim_id=claim_id,
                investigator_status=investigator_status,
                examiner_status=examiner_status,
                agrees=agrees,
                challenge=challenge,
                created_at=now(),
            )
        )
    return {
        "id": fid,
        "agrees": agrees,
        "examiner_status": examiner_status,
        "investigator_status": investigator_status,
    }


def investigator_force_examiner_agreement(finding: dict, forced_status: str) -> dict:
    if finding.get("agrees") is False and forced_status != finding.get("examiner_status"):
        raise EpistemicDenied("Investigator cannot force Examiner agreement.")
    return finding


def record_error(
    *,
    investigation_id: str = "",
    description: str,
    original_statement: str = "",
    correct_information: str = "",
    cause: str = "",
) -> dict:
    eid = f"err_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            ObserverErrorRow(
                id=eid,
                investigation_id=investigation_id,
                description=description,
                original_statement=original_statement,
                correct_information=correct_information,
                cause=cause,
                created_at=now(),
            )
        )
    return {"id": eid, "description": description}


def list_errors(investigation_id: str = "") -> list[dict]:
    with session_scope() as session:
        q = session.query(ObserverErrorRow)
        if investigation_id:
            q = q.filter(ObserverErrorRow.investigation_id == investigation_id)
        rows = q.order_by(ObserverErrorRow.created_at).all()
        return [
            {
                "id": r.id,
                "investigation_id": r.investigation_id,
                "description": r.description,
                "original_statement": r.original_statement,
                "correct_information": r.correct_information,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


def record_blind_spot(*, investigation_id: str = "", kind: str, detail: str) -> dict:
    bid = f"bs_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            BlindSpotRow(
                id=bid,
                investigation_id=investigation_id,
                kind=kind,
                detail=detail,
                created_at=now(),
            )
        )
    return {"id": bid, "kind": kind, "detail": detail}


def record_access_failure(
    *,
    investigation_id: str = "",
    source: str,
    failure_type: str,
    reason: str = "",
) -> dict:
    aid = f"af_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            AccessFailureRow(
                id=aid,
                investigation_id=investigation_id,
                source=source,
                failure_type=failure_type,
                reason=reason,
                created_at=now(),
            )
        )
    # Access failure is not DISPROVEN.
    record_blind_spot(
        investigation_id=investigation_id,
        kind="access_failure",
        detail=f"{source}: {failure_type}",
    )
    return {"id": aid, "failure_type": failure_type, "implies_false": False}


def cherry_pick_audit(
    *,
    sources_searched: list[str],
    excluded: list[dict],
    exclusion_reason: str,
) -> dict:
    if exclusion_reason.lower() in {"did not fit the narrative", "narrative"}:
        raise EpistemicDenied("Excluding evidence because it did not fit the narrative is a system failure.")
    return {
        "sources_searched": list(sources_searched),
        "excluded": list(excluded),
        "exclusion_reason": exclusion_reason,
    }


INQUIRY_SLOTS = ("who", "what", "when", "where", "possible_how", "possible_why")
MECHANISM_SLOTS = frozenset({"possible_how", "possible_why"})
INQUIRY_RULE = (
    "Search must cover who, what, when, where, possible how, and possible why. "
    "How and why are possible in many cases. Do not promote possible why to FACT "
    "unless a mechanism is independently established."
)


def inquiry_search_plan(question: str) -> dict[str, str]:
    """Directed search questions. Answers are not invented here."""
    q = (question or "").strip() or "the incident"
    return {
        "who": f"Who is involved in: {q}",
        "what": f"What happened: {q}",
        "when": f"When did it occur: {q}",
        "where": f"Where did it occur: {q}",
        "possible_how": f"How is this possible (mechanism, not fact): {q}",
        "possible_why": f"Why might this have happened (possible, often unproven): {q}",
    }


def refuse_promote_possible_to_fact(slot: str, kind: str) -> None:
    if slot in MECHANISM_SLOTS and (kind or "").lower() == EpistemicKind.FACT.value:
        raise EpistemicDenied(
            "possible_how and possible_why stay POSSIBLE/HYPOTHESIS unless a mechanism is independently established."
        )


def _inquiry_slot(value: str | None, *, status: str, kind: str, refs: list[str] | None = None) -> dict:
    text = (value or "").strip()
    return {
        "value": text if text else "UNKNOWN",
        "status": status if text else "UNKNOWN",
        "kind": kind if text else EpistemicKind.UNKNOWN.value,
        "evidence_refs": list(refs or []),
    }


def build_inquiry_frame(
    *,
    who: str | None = None,
    what: str | None = None,
    when: str | None = None,
    where: str | None = None,
    possible_how: str | None = None,
    possible_why: str | None = None,
    who_kind: str = EpistemicKind.FACT.value,
    what_kind: str = EpistemicKind.FACT.value,
    when_kind: str = EpistemicKind.FACT.value,
    where_kind: str = EpistemicKind.FACT.value,
    how_kind: str = EpistemicKind.HYPOTHESIS.value,
    why_kind: str = EpistemicKind.HYPOTHESIS.value,
    who_refs: list[str] | None = None,
    what_refs: list[str] | None = None,
    when_refs: list[str] | None = None,
    where_refs: list[str] | None = None,
    how_refs: list[str] | None = None,
    why_refs: list[str] | None = None,
    question: str = "",
) -> dict:
    refuse_promote_possible_to_fact("possible_how", how_kind)
    refuse_promote_possible_to_fact("possible_why", why_kind)
    how_status = "POSSIBLE" if (possible_how or "").strip() else "UNKNOWN"
    why_status = "POSSIBLE" if (possible_why or "").strip() else "UNKNOWN"
    return {
        "who": _inquiry_slot(who, status="OBSERVED", kind=who_kind, refs=who_refs),
        "what": _inquiry_slot(what, status="OBSERVED", kind=what_kind, refs=what_refs),
        "when": _inquiry_slot(when, status="OBSERVED", kind=when_kind, refs=when_refs),
        "where": _inquiry_slot(where, status="OBSERVED", kind=where_kind, refs=where_refs),
        "possible_how": _inquiry_slot(
            possible_how, status=how_status, kind=how_kind, refs=how_refs
        ),
        "possible_why": _inquiry_slot(
            possible_why, status=why_status, kind=why_kind, refs=why_refs
        ),
        "search_plan": inquiry_search_plan(question),
        "rule": INQUIRY_RULE,
        "slots": list(INQUIRY_SLOTS),
    }
