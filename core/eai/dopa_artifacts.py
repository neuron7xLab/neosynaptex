from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def claim_artifact_name(route_mode: str, final_status: str) -> str:
    if final_status == "CLOSED":
        return "closure_artifact.json"
    if final_status == "QUARANTINED":
        return "quarantine_artifact.json"
    if final_status == "REJECTED":
        return "rejection_artifact.json"
    if route_mode == "escalate":
        return "escalation_trace.json"
    return "closure_artifact.json"
