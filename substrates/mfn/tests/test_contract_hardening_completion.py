from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mycelium_fractal_net.core.compare import compare
from mycelium_fractal_net.core.simulate import simulate_scenario


def test_comparison_result_has_mandatory_topology_output() -> None:
    result = compare(
        simulate_scenario("synthetic_morphology"),
        simulate_scenario("regime_transition"),
    )
    payload = result.to_dict()
    assert payload["topology_label"] in {
        "nominal",
        "flattened-hierarchy",
        "pathological-drift",
        "reorganized",
    }
    assert set(payload["topology_summary"]) == {
        "connectivity_divergence",
        "hierarchy_flattening",
        "modularity_shift",
        "noise_discrimination",
    }


def test_docs_drift_check_script_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "docs_drift_check.py")],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(
        (root / "artifacts" / "evidence" / "wave_8" / "docs_drift_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["ok"] is True


def test_ci_workflow_contains_showcase_generation_and_attestation_chain() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci-reusable.yml").read_text(encoding="utf-8")
    assert "name: SHOWCASE_GENERATION" in workflow
    assert "name: NEUROCHEM_CONTRACTS" in workflow
    assert "name: SCIENTIFIC_CONTROLS" in workflow
    assert "name: OPENAPI_EXPORT" in workflow
    assert "name: ARTIFACT_ATTESTATION" in workflow
    assert (
        "needs: [showcase_generation, baseline_parity, neurochem_contracts, scientific_controls, openapi_export, docs_drift]"
        in workflow
    )


def test_release_manifest_carries_provenance_reference() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "showcase_run.py")],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads(
        (root / "artifacts" / "release" / "release_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["release_assets"]["attestation"] == "attestation.json"
    assert manifest["provenance"]["attestation_path"] == "attestation.json"
    assert "lock_sha256" in manifest["provenance"]
