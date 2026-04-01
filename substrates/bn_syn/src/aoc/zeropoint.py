from __future__ import annotations

import hashlib
import json
from typing import cast
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import TaskContract


class ZeroPointManager:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir

    def materialize(self, contract: TaskContract) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "task_contract": asdict(contract),
            "invariants": contract.invariants,
            "innovation_band": asdict(contract.innovation_band),
            "delta_weights": asdict(contract.delta_weights),
            "artifact_expectations": {
                "artifact_type": contract.artifact_type,
                "artifact_filename": contract.output["artifact_filename"],
            },
            "generator_configuration": contract.generator,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        zp_path = self.run_dir / "zeropoint.json"
        if zp_path.exists():
            existing = cast(dict[str, Any], json.loads(zp_path.read_text(encoding="utf-8")))
            if existing.get("hash") != payload["hash"]:
                raise RuntimeError("zeropoint immutable violation: existing hash mismatch")
            return existing
        zp_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        return payload
