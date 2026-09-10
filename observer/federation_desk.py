"""Read the federation desk. Observer audits; she does not own participants."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from observer.identity import identity
from observer.settings import load_settings, resolve_path


def _ensure_living_home() -> None:
    root = resolve_path(load_settings().living_home_root)
    loc = str(root)
    if loc not in sys.path:
        sys.path.insert(0, loc)


def audit_federation_desk() -> dict[str, Any]:
    settings = load_settings()
    data_root = resolve_path(settings.federation_root)
    _ensure_living_home()
    from federation.audit import inspect

    report = inspect(data_root)
    report["auditor"] = identity()["id"]
    report["audited_at"] = datetime.now(timezone.utc).isoformat()
    if report.get("ok"):
        artifact = data_root / "OBSERVER_AUDIT.json"
        artifact.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        report["artifact"] = str(artifact)
    return report
