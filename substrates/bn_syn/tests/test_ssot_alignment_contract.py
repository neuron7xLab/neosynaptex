from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ssot_alignment_contract_has_runner_commands() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "sse-sdo-fhe-gate.yml").read_text(encoding="utf-8")
    assert "python scripts/sse_gate_runner.py" in workflow
    assert "python scripts/sse_proof_index.py" in workflow
    assert "scripts/xrun \"python -V\"" in workflow
