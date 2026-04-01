from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_required_checks_manifest_includes_sse_gate() -> None:
    manifest = json.loads((REPO_ROOT / "artifacts" / "sse_sdo" / "04_ci" / "REQUIRED_CHECKS_MANIFEST.json").read_text(encoding="utf-8"))
    assert "sse-sdo-fhe-gate" in manifest["required_checks"]
