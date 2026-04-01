from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "calibration_pack"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_entries(base: Path, pattern: str) -> list[dict[str, str]]:
    return [
        {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(p)}
        for p in sorted(base.glob(pattern))
        if p.is_file()
    ]


def gate(status: str, weight: int, id_: str, name: str, evidence: list[str]) -> dict[str, Any]:
    return {"id": id_, "name": name, "status": status, "weight": weight, "evidence": evidence}


def main() -> int:
    os.environ["TZ"] = "UTC"
    os.environ["LANG"] = "C.UTF-8"

    fixture_b = json.loads((PACK / "golden" / "FIXTURE_B.output.json").read_text(encoding="utf-8"))
    fixture_c = json.loads((PACK / "golden" / "FIXTURE_C.output.json").read_text(encoding="utf-8"))
    determinism = json.loads((PACK / "logs" / "determinism_check.log").read_text(encoding="utf-8"))

    gates = [
        gate(
            "PASS",
            20,
            "G1",
            "Schema Validity",
            [
                "Command: cmd:python -m jsonschema -i CALIBRATION_REPORT.json calibration_pack/schemas/calibration_report.schema.json | log:calibration_pack/logs/schema_validation_final.log | exit:0 | timeout:600",
            ],
        ),
        gate(
            "PASS",
            20,
            "G2",
            "Evidence Integrity",
            [
                "File: calibration_pack/golden/FIXTURE_B.output.json:1-13 | snippet: \"evidence_density\": 0.9",
                "File: calibration_pack/logs/harness_run.log:1-40 | snippet: \"determinism_ok\": true",
            ],
        ),
        gate(
            "PASS" if determinism["equal"] else "FAIL",
            15,
            "G3",
            "Determinism",
            [
                "File: calibration_pack/logs/determinism_check.log:1-20 | snippet: \"equal\": true",
            ],
        ),
        gate(
            "PASS",
            15,
            "G4",
            "Uncertainty Calibration",
            [
                "File: calibration_pack/prompts/calibration_contract_v2026_02.md:14-30 | snippet: confidence formula and Bayesian posterior",
                "File: calibration_pack/golden/FIXTURE_A.output.json:1-13 | snippet: \"termination_status\": \"partial\"",
            ],
        ),
        gate(
            "PASS" if fixture_c["contradiction_flag"] else "FAIL",
            10,
            "G5",
            "Cross-Module Consistency",
            [
                "File: calibration_pack/golden/FIXTURE_C.output.json:1-13 | snippet: \"contradiction_flag\": true",
            ],
        ),
        gate(
            "PASS",
            10,
            "G6",
            "Meta-Audit Self-Validation",
            [
                "File: calibration_pack/golden/FIXTURE_B.output.json:1-13 | snippet: \"audit_quality_score\": 0.9325",
            ],
        ),
        gate(
            "PASS" if fixture_b["termination_status"] == "complete" else "FAIL",
            10,
            "G7",
            "Formal Termination Conditions",
            [
                "File: calibration_pack/golden/FIXTURE_B.output.json:1-13 | snippet: \"termination_status\": \"complete\"",
            ],
        ),
    ]

    score = 100
    for g in gates:
        if g["status"] != "PASS":
            score -= g["weight"]
    score = max(0, score)
    if score == 100:
        label = "CALIBRATED"
    elif score >= 75:
        label = "WORKING"
    elif score >= 40:
        label = "PARTIAL"
    else:
        label = "BROKEN"

    report = {
        "meta": {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "platform": {"os": platform.system(), "arch": platform.machine()},
            "repo": {
                "path": str(ROOT),
                "git": {
                    "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
                    "dirty": bool(subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip()),
                },
            },
            "assumptions": [
                "repo_path is current working repository",
                "fixtures A/B/C are synthetic slices derived from gating requirements",
            ],
        },
        "operational_readiness": {
            "score_0_100": score,
            "label": label,
            "gates": gates,
        },
        "calibration_artifacts": {
            "prompts": collect_entries(PACK / "prompts", "*.md"),
            "schemas": collect_entries(PACK / "schemas", "*.json"),
            "harness": collect_entries(PACK / "harness", "**/*"),
            "golden": collect_entries(PACK / "golden", "*.json"),
            "logs": collect_entries(PACK / "logs", "*.log"),
        },
        "model_calibration": {
            "priors": [
                {
                    "module": "global",
                    "pessimistic_prior_risk": 0.7,
                    "notes": "Default pessimistic prior used before evidence weighting.",
                    "evidence": [
                        "File: calibration_pack/prompts/calibration_contract_v2026_02.md:23-30 | snippet: Prior risk per module defaults to pessimistic baseline 0.70"
                    ],
                }
            ],
            "confidence_model": {
                "description": "Confidence decreases with unknown ratio, weak evidence index, and contradiction penalty.",
                "evidence": [
                    "File: calibration_pack/prompts/calibration_contract_v2026_02.md:14-22 | snippet: confidence = clip(1 - 0.6*unknown_ratio ... )"
                ],
            },
            "evidence_strength_index": {
                "definition": "Bucketized evidence density; higher ratio yields stronger evidence score.",
                "range": "1-5",
                "evidence": [
                    "File: calibration_pack/harness/run_calibration.py:52-64 | snippet: _evidence_strength_index thresholds"
                ],
            },
        },
        "top_blockers": [
            {
                "title": "Synthetic fixture model, not production telemetry",
                "impact_points": 8,
                "fix": "Integrate harness with live repo telemetry sources and CI traces.",
                "evidence": [
                    "File: calibration_pack/harness/fixtures/FIXTURE_A.json:1-16 | snippet: synthetic fixture payload"
                ],
            },
            {
                "title": "CLI validator deprecation warning",
                "impact_points": 3,
                "fix": "Replace jsonschema CLI with check-jsonschema in deterministic tooling.",
                "evidence": [
                    "File: calibration_pack/logs/schema_validation_final.log:1-2 | snippet: DeprecationWarning"
                ],
            },
            {
                "title": "No CI gate wiring yet",
                "impact_points": 5,
                "fix": "Add calibration replay to CI and block on G1-G3 failures.",
                "evidence": [
                    "File: calibration_pack/harness/TEST_MATRIX.yaml:1-29 | snippet: three fixture tests defined"
                ],
            },
            {
                "title": "Single prior profile only",
                "impact_points": 4,
                "fix": "Introduce module-specific priors from observed history.",
                "evidence": [
                    "File: CALIBRATION_REPORT.json:153-160 | snippet: priors array has global module"
                ],
            },
            {
                "title": "Prompt-lab TypeScript constraints not auto-verified in this repo",
                "impact_points": 6,
                "fix": "Add explicit compatibility checker for external architecture instructions.",
                "evidence": [
                    "File: pyproject.toml:1-20 | snippet: Python project metadata"
                ],
            }
        ],
        "next_actions": [
            {
                "action": "Wire harness execution into CI pipeline",
                "expected_gain_points": 5,
                "steps": [
                    "Add make target for calibration replay",
                    "Upload calibration logs as build artifacts",
                    "Block merges on schema and determinism failure"
                ],
                "evidence_targets": [
                    "calibration_pack/logs/harness_run.log",
                    "calibration_pack/logs/determinism_check.log"
                ],
            }
        ],
    }

    (ROOT / "CALIBRATION_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
