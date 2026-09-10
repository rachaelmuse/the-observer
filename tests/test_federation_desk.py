"""Observer HTTP reads D:\\Court\\federation. She does not own Aster."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from observer.api import app
from observer.registry import list_registry


def _seed(root: Path) -> None:
    (root / "participants").mkdir(parents=True)
    (root / "capabilities").mkdir(parents=True)
    (root / "bus" / "archive").mkdir(parents=True)
    (root / "participants" / "aster.json").write_text(
        json.dumps(
            {
                "agent_id": "aster",
                "name": "Aster",
                "version": "1.0",
                "role": "weaver",
                "house": "hearth_lab",
                "capabilities": [],
                "tools": [],
                "runtime": {},
                "protocol_version": "1",
                "requested_permissions": [],
                "declared_status": "DECLARED",
                "identity_root": r"D:\Mythos_Hearth\ASTER",
                "manifest_version": "1",
            }
        ),
        encoding="utf-8",
    )
    (root / "capabilities" / "aster.hearth_snapshot.json").write_text(
        json.dumps(
            {
                "capability_id": "aster.hearth_snapshot",
                "agent_id": "aster",
                "name": "Hearth snapshot read",
                "state": "VERIFIED",
                "honest_status": "VERIFIED",
                "provenance": {
                    "declared_by": "aster",
                    "adapter": "aster_hearth_bridge",
                    "artifact": str(root / "evidence" / "aster.hearth_snapshot.json"),
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "bus" / "archive" / "msg1.json").write_text(
        json.dumps(
            {
                "message_id": "fb33fd44test",
                "sender": "aster",
                "recipient": "hearth",
                "status": "acknowledged",
                "message_type": "capability_query",
            }
        ),
        encoding="utf-8",
    )


def test_federation_audit_http_does_not_own_aster(db, monkeypatch, tmp_path: Path):
    root = tmp_path / "federation"
    _seed(root)
    monkeypatch.setenv("FEDERATION_ROOT", str(root))
    from observer import settings as settings_mod

    settings_mod.load_settings.cache_clear() if hasattr(settings_mod.load_settings, "cache_clear") else None

    with TestClient(app) as client:
        res = client.get("/federation/audit")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert body["auditor"] == "the_observer"
        assert body["observer_owns_aster"] is False
        assert body["owned_by"] is None
        ids = {a["agent_id"] for a in body["agents"]}
        assert "aster" in ids
        assert any(c["verified"] for c in body["capabilities"])
        assert any(m["message_id"] == "fb33fd44test" for m in body["communications"])
        assert body["gemini_spoke"] is False
        saved = json.loads((root / "OBSERVER_AUDIT.json").read_text(encoding="utf-8"))
        assert saved["observer_owns_aster"] is False

    by_id = {c["id"]: c for c in list_registry()}
    assert "aster" not in by_id


def test_federation_audit_http_missing_store_is_honest(db, monkeypatch, tmp_path: Path):
    missing = tmp_path / "no_store"
    monkeypatch.setenv("FEDERATION_ROOT", str(missing))
    with TestClient(app) as client:
        res = client.get("/federation/audit")
        assert res.status_code == 404
        body = res.json()
        detail = body.get("detail") or body
        if isinstance(detail, dict):
            assert detail.get("ok") is False
            assert detail.get("observer_owns_aster") is False
        else:
            assert "federation" in str(detail).lower() or "missing" in str(detail).lower()
    assert not missing.exists()
