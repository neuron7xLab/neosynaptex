from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_sse_sdo_fhe_config_has_required_fields() -> None:
    config_path = ROOT / ".github" / "sse_sdo_fhe.yml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert payload["protocol"] == "SSE-SDO-FHE-2026.06"
    assert payload["toolchain"]["python"] == "3.11"
    assert payload["determinism"]["seed_required"] is True
    assert payload["evidence"]["required_ratio_P0"] == 1.0
    assert payload["policy"]["law_without_police_forbidden"] is True


def test_sse_sdo_fhe_artifact_tree_minimum_files_exist() -> None:
    required_paths = [
        "artifacts/sse_sdo/00_meta/REPO_FINGERPRINT.json",
        "artifacts/sse_sdo/00_meta/ENV_SNAPSHOT.json",
        "artifacts/sse_sdo/00_meta/RUN_MANIFEST.json",
        "artifacts/sse_sdo/01_scope/SUBSYSTEM_BOUNDARY.md",
        "artifacts/sse_sdo/01_scope/DEP_GRAPH.json",
        "artifacts/sse_sdo/01_scope/INTERFACE_REGISTRY.json",
        "artifacts/sse_sdo/02_contracts/CONTRACTS.md",
        "artifacts/sse_sdo/02_contracts/CONTRACT_TEST_MAP.json",
        "artifacts/sse_sdo/03_flags/FLAGS.md",
        "artifacts/sse_sdo/04_ci/REQUIRED_CHECKS_MANIFEST.json",
        "artifacts/sse_sdo/04_ci/DRIFT_REPORT.json",
        "artifacts/sse_sdo/04_ci/WORKFLOW_GRAPH.json",
        "artifacts/sse_sdo/05_tests/TEST_PLAN.md",
        "artifacts/sse_sdo/06_perf/PERF_REPORT.md",
        "artifacts/sse_sdo/07_quality/quality.json",
        "artifacts/sse_sdo/07_quality/EVIDENCE_INDEX.md",
        "artifacts/sse_sdo/07_quality/CONTRADICTIONS.json",
    ]

    for relpath in required_paths:
        assert (ROOT / relpath).exists(), relpath

    quality = json.loads((ROOT / "artifacts/sse_sdo/07_quality/quality.json").read_text(encoding="utf-8"))
    assert quality["protocol"] == "SSE-SDO-FHE-2026.06"
    assert quality["verdict"] == "PASS"
    assert quality["contradictions"] == 0
