from observer.human_nature import MECHANISMS, dual_explanations
from observer.questions import CATEGORIES, generate_questions
from observer.salvage import salvage


def test_question_engine_covers_required_categories():
    qs = generate_questions("Who funded the merger?")
    for key in (
        "FACTS",
        "PEOPLE",
        "MONEY",
        "POWER",
        "INCENTIVES",
        "RELATIONSHIPS",
        "TIMELINE",
        "INFORMATION",
        "ALTERNATIVE_EXPLANATIONS",
        "INQUIRY",
        "PLACE",
        "MECHANISM",
        "MOTIVE",
    ):
        assert key in qs
        assert qs[key]
        assert qs[key] == CATEGORIES[key]
    assert qs["INQUIRY"][0] == "Who?"
    assert "Possible why" in qs["INQUIRY"][-1]


def test_human_nature_compares_ordinary_and_manipulation():
    dual = dual_explanations("Why did the board resign?")
    assert "ordinary_explanation" in dual
    assert "manipulation_hypothesis" in dual
    assert "conspiracy" in dual["rule"].lower() or "Suspicion" in dual["rule"]
    assert "fear" in MECHANISMS
    assert "confirmation bias" in MECHANISMS


def test_salvage_splits_compound_claims():
    atoms = salvage(
        "Organization X secretly controls Organization Y; Organization Y owns a newspaper."
    )
    assert len(atoms) >= 2
    assert any(a["status"] == "unverified" for a in atoms)
