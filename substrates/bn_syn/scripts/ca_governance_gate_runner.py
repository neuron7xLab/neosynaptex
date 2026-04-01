from __future__ import annotations

import json
from pathlib import Path

from scripts.ca_arb_adjudicator import load_arbitration_log
from scripts.ca_cognitive_ir_compile import compile_ir
from scripts.ca_drift_detector import assert_zero_drift
from scripts.ca_policy_load import load_policy_config

REPO_ROOT = Path(__file__).resolve().parents[1]
QUALITY_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "06_quality" / "governance_quality.json"


def run_governance_gates() -> dict[str, object]:
    _ = load_policy_config()
    _ = compile_ir()
    drift = assert_zero_drift()
    _ = load_arbitration_log()

    quality = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    if not isinstance(quality, dict):
        msg = "governance_quality.json must be a JSON object"
        raise ValueError(msg)
    verdict = quality.get("verdict")
    contradictions = quality.get("contradictions")
    if verdict != "PASS" or contradictions != 0:
        msg = f"Governance gate failed: verdict={verdict!r}, contradictions={contradictions!r}"
        raise ValueError(msg)
    if drift.get("status") != "PASS":
        msg = "Drift report status must be PASS"
        raise ValueError(msg)
    return quality


if __name__ == "__main__":
    run_governance_gates()
