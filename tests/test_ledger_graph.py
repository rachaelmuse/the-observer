from observer.core import now
from observer.db import session_scope
from observer.graph import add_relationship, build_graph, entity_panel, upsert_entity
from observer.ledger import add_evidence, list_evidence
from observer.models import InvestigationRow
from observer.sources import register_source


def _inv(db):
    from observer.core import InvestigationStatus

    iid = "inv_ledger1"
    stamp = now()
    with session_scope() as session:
        session.add(
            InvestigationRow(
                id=iid,
                question="Who owns whom?",
                status=InvestigationStatus.RESEARCH.value,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    return iid


def test_same_publisher_is_not_independent_corroboration(db):
    iid = _inv(db)
    a = register_source(
        iid, url="https://news.example/a", title="A", publisher="SamePub", content_hash="h1"
    )
    b = register_source(
        iid, url="https://news.example/b", title="B", publisher="SamePub", content_hash="h2"
    )
    add_evidence(iid, source_id=a["id"], claim_id="cl_1", description="one", content_hash="h1")
    add_evidence(iid, source_id=b["id"], claim_id="cl_1", description="two", content_hash="h2")
    rows = [e for e in list_evidence(iid) if e["claim_id"] == "cl_1"]
    assert rows
    assert all(e["corroboration_count"] == 0 for e in rows)


def test_different_publishers_count_as_independent(db):
    iid = _inv(db)
    a = register_source(
        iid, url="https://alpha.example/a", title="A", publisher="Alpha", content_hash="h1"
    )
    b = register_source(
        iid, url="https://beta.example/b", title="B", publisher="Beta", content_hash="h2"
    )
    add_evidence(iid, source_id=a["id"], claim_id="cl_2", description="one", content_hash="h1")
    add_evidence(iid, source_id=b["id"], claim_id="cl_2", description="two", content_hash="h2")
    rows = [e for e in list_evidence(iid) if e["claim_id"] == "cl_2"]
    assert all(e["corroboration_count"] == 1 for e in rows)


def test_inferred_relationship_is_labeled(db):
    iid = _inv(db)
    x = upsert_entity(iid, "Alpha Corp", "organization")
    y = upsert_entity(iid, "Beta Trust", "trust")
    rel = add_relationship(
        iid,
        from_entity=x["id"],
        to_entity=y["id"],
        rel_type="owns",
        provenance_source_id=None,
        inferred=False,
    )
    assert rel["inferred"] is True
    graph = build_graph(iid)
    assert graph.has_node(x["id"])
    edges = list(graph.edges(data=True))
    assert edges
    assert edges[0][2]["inferred"] is True
    panel = entity_panel(iid, x["id"])
    assert panel["WHO"]["name"] == "Alpha Corp"
    assert panel["MONEY"] != []
