from observer.audit import adversarial_review
from observer.core import InvestigationStatus, now
from observer.db import session_scope
from observer.hypotheses import build_competing_hypotheses, list_hypotheses
from observer.models import InvestigationRow
from observer.reports import REQUIRED_SECTIONS, build_report


def _inv(question: str = "Is the pattern coordinated?") -> str:
    iid = "inv_hyp1"
    stamp = now()
    with session_scope() as session:
        session.add(
            InvestigationRow(
                id=iid,
                question=question,
                status=InvestigationStatus.HYPOTHESIS_FORMATION.value,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    return iid


def test_competing_hypotheses_include_counter_and_falsification(db):
    iid = _inv()
    created = build_competing_hypotheses(iid, "Is the pattern coordinated?")
    assert len(created) >= 4
    assert any(h["is_counter"] for h in created)
    assert all(h["falsification_conditions"] for h in created)
    stored = list_hypotheses(iid)
    assert len(stored) == len(created)


def test_adversarial_review_blocks_empty_evidence(db):
    iid = _inv()
    build_competing_hypotheses(iid, "empty case")
    review = adversarial_review(iid)
    assert any("No evidence has been collected" in w for w in review["warnings"])
    assert len(review["answers"]) == 12


def test_report_has_required_sections(db):
    iid = _inv()
    build_competing_hypotheses(iid, "report case")
    adversarial_review(iid)
    report = build_report(iid)
    for key in REQUIRED_SECTIONS:
        assert key in report
    assert report["conclusion"] == "Insufficient evidence."
    assert report["publish_status"] == "disabled"
