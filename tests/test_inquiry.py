"""Observer search must cover who/what/when/where plus possible how/why."""

from __future__ import annotations

import pytest

from observer.core import EpistemicKind
from observer.epistemic import (
    EpistemicDenied,
    INQUIRY_SLOTS,
    build_inquiry_frame,
    inquiry_search_plan,
    refuse_promote_possible_to_fact,
)
from observer.graph import entity_panel, upsert_entity
from observer.questions import generate_questions
from tests.test_ledger_graph import _inv


def test_inquiry_search_plan_covers_six_slots():
    plan = inquiry_search_plan("llama-server crashed")
    assert tuple(plan) == INQUIRY_SLOTS
    assert "Who" in plan["who"]
    assert "possible" in plan["possible_why"].lower() or "Why" in plan["possible_why"]


def test_possible_why_cannot_be_promoted_to_fact():
    with pytest.raises(EpistemicDenied, match="possible_why"):
        refuse_promote_possible_to_fact("possible_why", EpistemicKind.FACT.value)
    with pytest.raises(EpistemicDenied, match="possible_how"):
        build_inquiry_frame(possible_how="OOM", how_kind=EpistemicKind.FACT.value)


def test_empty_inquiry_is_unknown_not_invented():
    frame = build_inquiry_frame(question="what happened")
    for slot in INQUIRY_SLOTS:
        assert frame[slot]["value"] == "UNKNOWN"
        assert frame[slot]["kind"] == EpistemicKind.UNKNOWN.value
    assert frame["possible_why"]["status"] == "UNKNOWN"
    assert "search_plan" in frame


def test_how_and_why_stay_possible_when_filled():
    frame = build_inquiry_frame(
        who="llama-server.exe",
        possible_how="std::bad_alloc during CUDA alloc",
        possible_why="GPU already near capacity",
        how_kind=EpistemicKind.HYPOTHESIS.value,
        why_kind=EpistemicKind.HYPOTHESIS.value,
    )
    assert frame["who"]["status"] == "OBSERVED"
    assert frame["possible_how"]["status"] == "POSSIBLE"
    assert frame["possible_why"]["status"] == "POSSIBLE"
    assert frame["possible_why"]["kind"] == EpistemicKind.HYPOTHESIS.value


def test_question_engine_inquiry_is_search_frame():
    qs = generate_questions("Observer search")
    assert qs["INQUIRY"][0] == "Who?"
    assert any("why remains possible" in item.lower() for item in qs["INQUIRY"])


def test_entity_panel_has_possible_how_and_why(db):
    iid = _inv(db)
    ent = upsert_entity(iid, "Alpha Corp", "organization")
    panel = entity_panel(iid, ent["id"])
    assert panel["WHO"]["name"] == "Alpha Corp"
    assert panel["POSSIBLE_HOW"]["status"] == "POSSIBLE"
    assert panel["POSSIBLE_WHY"]["value"] == "UNKNOWN"
    assert panel["POSSIBLE_WHY"]["kind"] == "hypothesis"
