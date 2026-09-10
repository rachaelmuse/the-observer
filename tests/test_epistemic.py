"""Refusal-to-lie / epistemic integrity. Claims preserved; truth status earned."""

from __future__ import annotations

import uuid

import pytest

from observer.audit import adversarial_review
from observer.core import ClaimStatus, EpistemicKind, InvestigationStatus, now
from observer.db import session_scope
from observer.epistemic import (
    EpistemicDenied,
    assess_missing_evidence,
    cherry_pick_audit,
    classify_civil_incident,
    classify_user_media,
    complete_total_report,
    creator_assertion_is_evidence,
    event_temporal_state,
    fringe_source_invalidates,
    investigator_force_examiner_agreement,
    list_claim_history,
    list_errors,
    may_promote,
    model_output_is_evidence,
    official_denial_disproves,
    operational_crime_assistance_allowed,
    political_identity_weights_evidence,
    prestige_substitutes_for_evidence,
    promote_claim,
    public_false_label,
    record_access_failure,
    record_error,
    record_examiner_finding,
    requires_comprehensive_mode,
    search_popularity_raises_status,
)
from observer.hypotheses import append_conclusion, build_competing_hypotheses, list_conclusions
from observer.models import ClaimRow, InvestigationRow
from observer.reports import build_report


def _claim(text: str = "X happened.", status: str = ClaimStatus.UNVERIFIED.value) -> tuple[str, str]:
    iid = f"inv_{uuid.uuid4().hex[:10]}"
    cid = f"cl_{uuid.uuid4().hex[:10]}"
    stamp = now()
    with session_scope() as session:
        session.add(
            InvestigationRow(
                id=iid,
                question=text,
                status=InvestigationStatus.RESEARCH.value,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    with session_scope() as session:
        session.add(
            ClaimRow(
                id=cid,
                investigation_id=iid,
                text=text,
                status=status,
                source_ids="[]",
                contradictions="[]",
                epistemic_kind="unknown",
                confidence=0.1,
            )
        )
    return iid, cid


def test_unverified_is_not_promoted_to_verified():
    ok, reason = may_promote(ClaimStatus.UNVERIFIED.value, ClaimStatus.VERIFIED.value)
    assert ok is False
    assert "VERIFIED" in reason


def test_no_evidence_does_not_become_false():
    result = assess_missing_evidence()
    assert result["status"] == ClaimStatus.INSUFFICIENT_EVIDENCE.value
    assert result["public_false"] is None
    assert public_false_label(ClaimStatus.UNVERIFIED.value) is None
    ok, _ = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.DISPROVEN.value,
        evidence_count=0,
        determination_path=False,
    )
    assert ok is False


def test_missing_evidence_produces_unresolved_not_disproven(db):
    iid, cid = _claim()
    with pytest.raises(EpistemicDenied):
        promote_claim(cid, ClaimStatus.DISPROVEN.value, evidence_ids=[], determination_path=False)
    promote_claim(cid, ClaimStatus.INSUFFICIENT_EVIDENCE.value)
    history = list_claim_history(cid)
    assert history[-1]["new_status"] == ClaimStatus.INSUFFICIENT_EVIDENCE.value
    assert history[-1]["previous_status"] == ClaimStatus.UNVERIFIED.value


def test_one_source_cannot_create_corroborated():
    ok, reason = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.CORROBORATED.value,
        independent_source_count=1,
    )
    assert ok is False
    assert "one source" in reason


def test_copies_of_one_origin_are_not_independent():
    ok, _ = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.CORROBORATED.value,
        independent_source_count=1,
        copies_of_one_origin=10,
    )
    assert ok is False


def test_official_denial_does_not_automatically_disprove():
    assert official_denial_disproves() is False
    ok, reason = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.DISPROVEN.value,
        official_denied=True,
        determination_path=False,
        evidence_count=1,
    )
    assert ok is False
    assert "official denial" in reason


def test_fringe_source_does_not_invalidate():
    assert fringe_source_invalidates() is False


def test_ai_output_is_not_automatically_evidence():
    assert model_output_is_evidence(EpistemicKind.MODEL_GENERATED.value) is False
    assert model_output_is_evidence(EpistemicKind.FACT.value) is True


def test_contradiction_is_preserved_not_discarded():
    ok, note = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.CONTRADICTED.value,
    )
    assert ok is True
    assert "preserved" in note
    ok_v, _ = may_promote(
        ClaimStatus.CONTRADICTED.value,
        ClaimStatus.VERIFIED.value,
        evidence_count=3,
        has_provenance=True,
        functional_test_ran=True,
        examiner_agrees=True,
        unresolved_contradiction=True,
    )
    assert ok_v is False


def test_correction_preserves_original_conclusion(db):
    _iid, cid = _claim(status=ClaimStatus.UNVERIFIED.value)
    promote_claim(
        cid,
        ClaimStatus.DOCUMENTED.value,
        evidence_ids=["ev1"],
        reason="artifact archived",
    )
    promote_claim(
        cid,
        ClaimStatus.INSUFFICIENT_EVIDENCE.value,
        reason="new evidence reopened the file",
    )
    hist = list_claim_history(cid)
    assert [h["new_status"] for h in hist] == [
        ClaimStatus.DOCUMENTED.value,
        ClaimStatus.INSUFFICIENT_EVIDENCE.value,
    ]
    assert hist[0]["previous_status"] == ClaimStatus.UNVERIFIED.value


def test_new_evidence_can_reopen_and_append_conclusion(db):
    iid, _cid = _claim()
    first = append_conclusion(iid, "Insufficient evidence.")
    second = append_conclusion(iid, "Still unresolved after new artifact.")
    versions = list_conclusions(iid)
    assert first["version"] == 1
    assert second["version"] == 2
    assert versions[0]["body"] == "Insufficient evidence."
    assert len(versions) == 2


def test_verified_requires_provenance_and_test():
    ok, reason = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.VERIFIED.value,
        evidence_count=2,
        has_provenance=False,
        functional_test_ran=True,
        examiner_agrees=True,
    )
    assert ok is False
    assert "provenance" in reason
    ok2, reason2 = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.VERIFIED.value,
        evidence_count=2,
        has_provenance=True,
        functional_test_ran=False,
        examiner_agrees=True,
    )
    assert ok2 is False
    assert "test" in reason2.lower()


def test_disproven_requires_determination_path(db):
    _iid, cid = _claim()
    with pytest.raises(EpistemicDenied, match="determination"):
        promote_claim(cid, ClaimStatus.DISPROVEN.value, evidence_ids=["ev1"], determination_path=False)
    promote_claim(
        cid,
        ClaimStatus.DISPROVEN.value,
        evidence_ids=["ev1"],
        determination_path=True,
        reason="primary record refutes the date",
    )
    hist = list_claim_history(cid)
    assert hist[-1]["new_status"] == ClaimStatus.DISPROVEN.value
    assert public_false_label(ClaimStatus.DISPROVEN.value) == "FALSE"


def test_examiner_can_disagree_and_cannot_be_forced(db):
    iid, cid = _claim()
    finding = record_examiner_finding(
        iid,
        claim_id=cid,
        investigator_status=ClaimStatus.VERIFIED.value,
        examiner_status=ClaimStatus.UNRESOLVED.value,
        challenge="Test did not actually test the asserted claim.",
    )
    assert finding["agrees"] is False
    with pytest.raises(EpistemicDenied, match="force"):
        investigator_force_examiner_agreement(finding, ClaimStatus.VERIFIED.value)
    ok, reason = may_promote(
        ClaimStatus.UNVERIFIED.value,
        ClaimStatus.VERIFIED.value,
        evidence_count=4,
        has_provenance=True,
        functional_test_ran=True,
        examiner_agrees=False,
    )
    assert ok is False
    assert "Examiner" in reason


def test_user_assertion_remains_claim_until_investigated():
    ok, _ = may_promote(ClaimStatus.REPORTED.value, ClaimStatus.VERIFIED.value, evidence_count=0)
    assert ok is False


def test_video_is_lead_until_authenticated():
    assert classify_user_media(authenticated=False) == "LEAD"
    assert classify_user_media(authenticated=True) == "EVIDENCE"


def test_search_popularity_and_prestige_and_politics_do_not_weight():
    assert search_popularity_raises_status() is False
    assert political_identity_weights_evidence() is False
    assert prestige_substitutes_for_evidence() is False
    assert creator_assertion_is_evidence() is False


def test_absence_of_reporting_is_not_absence_of_event():
    result = assess_missing_evidence()
    assert result["status"] != ClaimStatus.DISPROVEN.value


def test_peaceful_protest_is_not_riot_and_crime_is_not_unrest():
    assert (
        classify_civil_incident(
            protest_link_evidence=False,
            police_present=True,
            violent_crime=False,
            peaceful_assembly=True,
        )
        == "PEACEFUL_PROTEST"
    )
    assert (
        classify_civil_incident(
            protest_link_evidence=False,
            police_present=False,
            violent_crime=True,
            peaceful_assembly=False,
        )
        == "GENERAL_VIOLENCE"
    )


def test_old_reporting_is_not_automatically_active():
    assert event_temporal_state(article_is_current=False, described_as_active=True) == "UNKNOWN"


def test_comprehensive_mode_refuses_headline_substitution():
    assert requires_comprehensive_mode("How many protests are happening in America today?")
    with pytest.raises(EpistemicDenied, match="headline"):
        complete_total_report(
            question="Give me everything. Complete totals.",
            confirmed=[],
            probable=[],
            unresolved=[],
            headline_only=["story A", "story B", "story C", "story D", "story E"],
            source_classes_searched=["NEWS_MEDIA", "LOCAL_JOURNALISM"],
            complete_total_obtainable=False,
            collection_ended="USER_TERMINATED",
        )
    report = complete_total_report(
        question="How many protests, riots, and active violence are occurring in America today?",
        confirmed=[{"id": "1", "place": "Los Angeles", "category": "PROTEST"}],
        probable=[],
        unresolved=[{"id": "2", "note": "Long Beach shooting — protest link not established"}],
        source_classes_searched=["NEWS_MEDIA", "GOVERNMENT", "LOCAL_JOURNALISM", "VIDEO"],
        complete_total_obtainable=False,
        collection_ended="ACCESS_LIMIT_REACHED",
    )
    assert report["complete_total_obtainable"] is False
    assert report["total_confirmed"] == 1
    assert report["total_unresolved"] == 1
    assert report["we_report_what_we_find"] is True


def test_comprehensive_mainstream_only_is_insufficient():
    with pytest.raises(EpistemicDenied, match="Mainstream-only"):
        complete_total_report(
            question="don't cherry-pick — complete totals",
            confirmed=[{"id": "1"}],
            probable=[],
            unresolved=[],
            source_classes_searched=["NEWS_MEDIA"],
            complete_total_obtainable=False,
            collection_ended="SEARCH_SPACE_EXHAUSTED",
        )


def test_access_failure_does_not_imply_false(db):
    fail = record_access_failure(
        source="FREENET",
        failure_type="UNSUPPORTED_PROTOCOL",
        reason="adapter unavailable",
    )
    assert fail["implies_false"] is False


def test_error_ledger_is_append_only(db):
    record_error(description="missed California incidents", original_statement="five headlines")
    record_error(description="classified unrelated shooting as unrest")
    rows = list_errors()
    assert len(rows) == 2
    assert rows[0]["description"] == "missed California incidents"


def test_cherry_pick_for_narrative_is_failure():
    with pytest.raises(EpistemicDenied, match="narrative"):
        cherry_pick_audit(
            sources_searched=["a"],
            excluded=[{"id": "b"}],
            exclusion_reason="did not fit the narrative",
        )


def test_no_operational_crime_assistance():
    assert operational_crime_assistance_allowed() is False


def test_report_states_we_report_what_we_find(db):
    iid, _cid = _claim("Is the pattern coordinated?")
    build_competing_hypotheses(iid, "Is the pattern coordinated?")
    adversarial_review(iid)
    report = build_report(iid)
    assert report["we_report_what_we_find"] is True
    assert report["conclusion"] == "Insufficient evidence."
    assert "what_would_change_our_conclusion" in report
    assert "inquiry" in report
    for slot in ("who", "what", "when", "where", "possible_how", "possible_why"):
        assert slot in report["inquiry"]
    assert report["inquiry"]["possible_why"]["kind"] != "fact"
    assert report["inquiry"]["possible_why"]["value"] == "UNKNOWN"
