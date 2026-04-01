from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import sse_policy_load  # noqa: E402


def test_sse_policy_schema_contract_loads_strictly() -> None:
    payload = sse_policy_load.load_and_validate(REPO_ROOT / ".github" / "sse_sdo_fhe.yml")
    assert payload["protocol"] == "SSE-SDO-FHE-2026.06"
    assert payload["policy"]["law_without_police_forbidden"] is True


def test_sse_policy_schema_rejects_unknown_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yml"
    bad.write_text((REPO_ROOT / ".github" / "sse_sdo_fhe.yml").read_text(encoding="utf-8") + "\nextra_key: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown keys"):
        sse_policy_load.load_and_validate(bad)
