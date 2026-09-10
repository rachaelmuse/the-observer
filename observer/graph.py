"""NetworkX graph over persisted relationships. Inferred edges stay labeled inferred."""

from __future__ import annotations

import json
import uuid

import networkx as nx

from observer.core import RelType
from observer.db import session_scope
from observer.models import EntityRow, RelationshipRow

MONEY_REL_TYPES = {
    RelType.OWNS.value,
    RelType.CONTROLS.value,
    RelType.FUNDS.value,
    RelType.INVESTS_IN.value,
    RelType.ACQUIRED.value,
    RelType.ACQUIRED_BY.value,
}


def upsert_entity(investigation_id: str, name: str, entity_type: str = "organization") -> dict:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("entity name required")
    with session_scope() as session:
        existing = (
            session.query(EntityRow)
            .filter(
                EntityRow.investigation_id == investigation_id,
                EntityRow.name == cleaned,
            )
            .first()
        )
        if existing:
            return {"id": existing.id, "name": existing.name, "entity_type": existing.entity_type}
        eid = f"ent_{uuid.uuid4().hex[:12]}"
        session.add(
            EntityRow(
                id=eid,
                investigation_id=investigation_id,
                entity_type=entity_type,
                name=cleaned,
                aliases="[]",
            )
        )
        return {"id": eid, "name": cleaned, "entity_type": entity_type}


def add_relationship(
    investigation_id: str,
    *,
    from_entity: str,
    to_entity: str,
    rel_type: str,
    provenance_source_id: str | None,
    inferred: bool = False,
    notes: str = "",
) -> dict:
    if not inferred and not provenance_source_id:
        inferred = True
        notes = (notes + " Inferred: no source provenance.").strip()
    rid = f"rel_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            RelationshipRow(
                id=rid,
                investigation_id=investigation_id,
                from_entity=from_entity,
                to_entity=to_entity,
                rel_type=rel_type,
                provenance_source_id=provenance_source_id,
                inferred=inferred,
                notes=notes,
            )
        )
    return {
        "id": rid,
        "from_entity": from_entity,
        "to_entity": to_entity,
        "rel_type": rel_type,
        "inferred": inferred,
        "provenance_source_id": provenance_source_id,
    }


def list_entities(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(EntityRow)
            .filter(EntityRow.investigation_id == investigation_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "entity_type": r.entity_type,
                "aliases": json.loads(r.aliases or "[]"),
            }
            for r in rows
        ]


def list_relationships(investigation_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(RelationshipRow)
            .filter(RelationshipRow.investigation_id == investigation_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "from_entity": r.from_entity,
                "to_entity": r.to_entity,
                "rel_type": r.rel_type,
                "provenance_source_id": r.provenance_source_id,
                "inferred": r.inferred,
                "notes": r.notes,
            }
            for r in rows
        ]


def build_graph(investigation_id: str) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for ent in list_entities(investigation_id):
        graph.add_node(ent["id"], **ent)
    for rel in list_relationships(investigation_id):
        graph.add_edge(
            rel["from_entity"],
            rel["to_entity"],
            key=rel["id"],
            rel_type=rel["rel_type"],
            inferred=rel["inferred"],
            provenance_source_id=rel["provenance_source_id"],
        )
    return graph


def entity_panel(investigation_id: str, entity_id: str) -> dict:
    with session_scope() as session:
        ent = session.get(EntityRow, entity_id)
        if ent is None or ent.investigation_id != investigation_id:
            return {"error": "unknown entity"}
        rels = [
            r
            for r in list_relationships(investigation_id)
            if r["from_entity"] == entity_id or r["to_entity"] == entity_id
        ]
        money = [r for r in rels if r["rel_type"] in MONEY_REL_TYPES]
        return {
            "WHO": {"id": ent.id, "name": ent.name, "entity_type": ent.entity_type},
            "WHAT": ent.entity_type,
            "WHEN": "no dated events recorded" if not rels else "see relationships",
            "WHERE": "not recorded",
            "POSSIBLE_HOW": {
                "value": "UNKNOWN",
                "status": "POSSIBLE",
                "kind": "hypothesis",
                "note": "mechanism not established",
            },
            "POSSIBLE_WHY": {
                "value": "UNKNOWN",
                "status": "POSSIBLE",
                "kind": "hypothesis",
                "note": "in many cases why remains possible, not proven",
            },
            "MONEY": money or "no money relationships recorded",
            "RELATIONSHIPS": rels or "no relationships recorded",
            "DOCUMENTS": "see sources on investigation",
            "CLAIMS": "see claims on investigation",
            "CONTRADICTIONS": "see audit warnings",
            "SOURCE_HISTORY": [r.get("provenance_source_id") for r in rels if r.get("provenance_source_id")],
        }
