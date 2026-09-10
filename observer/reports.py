"""Required report format. Epistemic labels stay separate."""

from __future__ import annotations

from observer.audit import latest_audit
from observer.contradictions import list_contradictions
from observer.core import EpistemicKind
from observer.db import session_scope
from observer.epistemic import INQUIRY_SLOTS, build_inquiry_frame
from observer.graph import list_entities, list_relationships
from observer.hypotheses import list_conclusions, list_hypotheses
from observer.ledger import list_evidence
from observer.models import ClaimRow, InvestigationRow, ResearchRecordRow
from observer.questions import generate_questions
from observer.sources import list_sources

REQUIRED_SECTIONS = [
    "executive_summary",
    "inquiry",
    "what_we_know",
    "what_we_do_not_know",
    "evidence",
    "timeline",
    "people_and_organizations",
    "money_and_ownership",
    "competing_explanations",
    "evidence_against_primary_hypothesis",
    "evidence_supporting_primary_hypothesis",
    "what_would_change_our_conclusion",
    "conclusion",
    "source_ledger",
]


def build_report(investigation_id: str) -> dict:
    with session_scope() as session:
        inv = session.get(InvestigationRow, investigation_id)
        if inv is None:
            raise KeyError(investigation_id)
        claims = (
            session.query(ClaimRow)
            .filter(ClaimRow.investigation_id == investigation_id)
            .all()
        )
        records = (
            session.query(ResearchRecordRow)
            .filter(ResearchRecordRow.investigation_id == investigation_id)
            .all()
        )
        question = inv.question
        status = inv.status

    evidence = list_evidence(investigation_id)
    sources = list_sources(investigation_id)
    entities = list_entities(investigation_id)
    rels = list_relationships(investigation_id)
    hyps = list_hypotheses(investigation_id)
    audit = latest_audit(investigation_id) or {"warnings": [], "answers": {}}
    contradictions = list_contradictions(investigation_id)
    conclusions = list_conclusions(investigation_id)
    primary = next((h for h in hyps if not h["is_counter"]), hyps[0] if hyps else None)
    counter = next((h for h in hyps if h["is_counter"]), None)

    known = [
        c.text
        for c in claims
        if c.status in {"documented", "corroborated", "verified", "partially_verified"}
    ]
    unknown = [
        "Independent corroboration from a second publisher is missing."
        if evidence
        else "No evidence has been collected."
    ]
    if contradictions:
        unknown.append(
            f"{len(contradictions)} unresolved contradiction(s). Conflict is recorded, not judged."
        )
    if not known:
        known = ["No claim has reached documented/corroborated status."]

    thin = len(evidence) < 2
    conclusion_body = (
        conclusions[-1]["body"]
        if conclusions
        else (
            "Insufficient evidence."
            if thin
            else "The investigation produced sources and hypotheses; it does not establish a coordinated conclusion."
        )
    )

    money_rels = [r for r in rels if r["rel_type"] in {"owns", "funds", "invests_in", "controls", "acquired", "acquired_by"}]
    timeline = [
        {"when": rec.retrieval_date.isoformat(), "what": f"Retrieved {rec.url}", "kind": "research_record"}
        for rec in records
    ]

    who_names = [e.get("name") for e in entities if isinstance(e, dict) and e.get("name")]
    what_known = next((c for c in known if c and c != "No claim has reached documented/corroborated status."), None)
    when_obs = None
    if isinstance(timeline, list) and timeline:
        when_obs = timeline[0].get("when")
    how_hyp = (primary or {}).get("text") if primary else None
    inquiry = build_inquiry_frame(
        who=", ".join(who_names) if who_names else None,
        what=what_known,
        when=when_obs,
        where=None,
        possible_how=how_hyp,
        possible_why=None,
        who_kind=EpistemicKind.FACT.value if who_names else EpistemicKind.UNKNOWN.value,
        what_kind=EpistemicKind.FACT.value if what_known else EpistemicKind.UNKNOWN.value,
        when_kind=EpistemicKind.FACT.value if when_obs else EpistemicKind.UNKNOWN.value,
        where_kind=EpistemicKind.UNKNOWN.value,
        how_kind=EpistemicKind.HYPOTHESIS.value,
        why_kind=EpistemicKind.HYPOTHESIS.value,
        question=question,
    )
    inquiry["questions"] = generate_questions(question).get("INQUIRY") or []
    inquiry["slots_required"] = list(INQUIRY_SLOTS)

    report = {
        "investigation_id": investigation_id,
        "question": question,
        "status": status,
        "inquiry": inquiry,
        "epistemic_note": "FACT, ANALYSIS, INFERENCE, HYPOTHESIS, ALLEGATION, OPINION, and UNKNOWN are not interchangeable. Who/what/when/where may be observed. How and why are possible until a mechanism is established.",
        "executive_summary": (
            f"Investigation of {question!r}. "
            f"{len(sources)} source(s), {len(evidence)} evidence item(s), {len(hyps)} hypotheses. "
            f"Current conclusion: {conclusion_body}"
        ),
        "what_we_know": known,
        "what_we_do_not_know": unknown,
        "evidence": evidence,
        "timeline": timeline or "no dated events recorded",
        "people_and_organizations": entities or "no entities recorded",
        "money_and_ownership": money_rels or "no money/ownership relationships recorded",
        "competing_explanations": hyps,
        "evidence_against_primary_hypothesis": (
            (primary or {}).get("contradictory_evidence") or audit.get("warnings") or []
        ),
        "evidence_supporting_primary_hypothesis": (primary or {}).get("supporting_evidence") or [],
        "what_would_change_our_conclusion": (primary or {}).get("falsification_conditions")
        or ["A second independent publisher corroborating or contradicting the primary source."],
        "conclusion": conclusion_body,
        "source_ledger": sources,
        "counter_hypothesis": counter,
        "contradictions": contradictions,
        "audit_warnings": audit.get("warnings") or [],
        "the_question": question,
        "what_we_think": conclusion_body,
        "limitations": [
            "Heuristic extraction. Specialized desks are used only when the question matches.",
            "Same-publisher copies are not independent corroboration.",
            "Four independent model reviewers are UNAVAILABLE.",
        ],
        "four_reviewers": {
            "status": "unavailable",
            "note": "Independent GPT/Grok/DeepSeek review is not seated. Disagreement cannot be manufactured.",
        },
        "we_report_what_we_find": True,
        "epistemic_standard": "docs/OBSERVER_EPISTEMIC_STANDARD.md",
        "public_challenges": [],
        "reproducibility_package": {
            "source_urls": [s.get("url") for s in sources if s.get("url")],
            "content_hashes": [s.get("content_hash") for s in sources if s.get("content_hash")],
            "investigation_id": investigation_id,
        },
        "publish_status": "disabled",
        "sections": REQUIRED_SECTIONS,
    }
    return report
