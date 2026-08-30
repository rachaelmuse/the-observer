from observer.core import InvestigationStatus, content_hash, now
from observer.db import session_scope
from observer.models import InvestigationRow


def test_content_hash_stable():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_investigation_round_trip(db):
    iid = "inv_roundtrip1"
    stamp = now()
    with session_scope() as session:
        session.add(
            InvestigationRow(
                id=iid,
                question="Did this persist?",
                status=InvestigationStatus.INTAKE.value,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    with session_scope() as session:
        row = session.get(InvestigationRow, iid)
        assert row is not None
        assert row.question == "Did this persist?"
        assert row.status == "intake"
