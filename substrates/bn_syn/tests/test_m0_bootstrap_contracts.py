from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str((ROOT / "src").resolve())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{existing}" if existing else src_path
    return env


def test_milestone_state_contract() -> None:
    payload = _load_json(ROOT / "ci" / "milestone_state.json")
    assert payload["schema_version"] == "1.1.0"
    assert payload["track"] == "canonical_foundation"
    milestones = payload["milestones"]
    expected = [f"M{i}" for i in range(12)]
    assert list(milestones.keys()) == expected
    for entry in milestones.values():
        assert entry == {"closed": False, "commit": None, "ci_run": None}


def test_statistical_power_config_shape_matches_canonical_stub() -> None:
    payload = _load_json(ROOT / "ci" / "statistical_power_config.json")
    assert payload["schema_version"] == "1.2.0"
    assert payload["policy_scope"] == "canonical_avalanche_admission_stub"
    assert payload["enforcement_status"] == "planned"

    policy = payload["avalanche_admission"]
    required_keys = {
        "N_min",
        "duration_min_ms",
        "bin_width_ms",
        "min_avalanche_count",
        "min_tail_count",
        "p_value_threshold",
        "ks_max",
        "monte_carlo_simulations",
    }
    assert set(policy.keys()) == required_keys
    assert policy["N_min"] >= 1
    assert 0.0 < policy["p_value_threshold"] <= 1.0
    assert policy["monte_carlo_simulations"] >= 1


def test_validation_gate_registry_contract() -> None:
    payload = _load_json(ROOT / "ci" / "validation_gates.json")
    assert payload["schema_version"] == "1.4.0"
    gates = payload["registry"]
    gate_ids = [gate["id"] for gate in gates]
    assert gate_ids == [
        "G1_active_spiking",
        "G2_rate_in_bounds",
        "G3_sigma_in_range",
        "G4_core_artifacts_complete",
        "G5_manifest_valid",
        "G6_determinism_replay",
        "G7_avalanche_evidence_sufficient",
        "G8_reproducibility_envelope",
        "G9_metrics_trace_consistency",
    ]

    by_id = {gate["id"]: gate for gate in gates}
    assert by_id["G1_active_spiking"]["threshold"]["metric"] == "spike_events"
    assert by_id["G2_rate_in_bounds"]["threshold"]["metric"] == "rate_mean_hz"
    assert by_id["G3_sigma_in_range"]["threshold"]["metric"] == "sigma_mean"

    required_by_mode = by_id["G4_core_artifacts_complete"]["threshold"]["required_artifacts_by_mode"]
    assert required_by_mode["canonical-base"] == ["emergence_plot.png", "summary_metrics.json", "criticality_report.json", "avalanche_report.json", "phase_space_report.json", "avalanche_fit_report.json", "robustness_report.json", "envelope_report.json", "run_manifest.json"]
    assert required_by_mode["canonical-export-proof"] == ["emergence_plot.png", "summary_metrics.json", "criticality_report.json", "avalanche_report.json", "phase_space_report.json", "avalanche_fit_report.json", "robustness_report.json", "envelope_report.json", "run_manifest.json", "proof_report.json"]

    assert by_id["G5_manifest_valid"]["threshold"]["schema_ref"] != "schemas/proof-report.schema.json"

    serialized = json.dumps(payload, sort_keys=True)
    assert "canonical_proof_plot.png" not in serialized
    assert "canonical_summary_metrics.json" not in serialized
    assert "canonical_manifest.json" not in serialized
    assert "spike_rate_hz_mean" not in serialized

    wired = {gate_id for gate_id, gate in by_id.items() if gate["status"] == "wired"}
    assert wired == set(gate_ids)


def test_proof_report_schema_accepts_minimal_valid_payload() -> None:
    schema = _load_json(ROOT / "schemas" / "proof-report.schema.json")
    payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-export-proof",
        "export_proof": True,
        "timestamp_utc": "1970-01-01T00:00:00Z",
        "seed": 123,
        "verdict": "INCONCLUSIVE",
        "verdict_code": 1001,
        "gates": {
            "G1_active_spiking": {"status": "PASS"},
            "G2_rate_in_bounds": {"status": "PASS"},
            "G3_sigma_in_range": {"status": "PASS"},
            "G4_core_artifacts_complete": {"status": "PASS"},
            "G5_manifest_valid": {"status": "PASS"},
            "G6_determinism_replay": {"status": "INCONCLUSIVE", "details": "planned gate"},
            "G7_avalanche_evidence_sufficient": {"status": "INCONCLUSIVE"},
            "G8_reproducibility_envelope": {"status": "INCONCLUSIVE"},
            "G9_metrics_trace_consistency": {"status": "PASS"},
        },
        "metrics": {},
        "recomputed_metrics": {},
        "summary_metrics_snapshot": {},
        "recompute_sources": {"rate_mean_hz": "population_rate_trace.npy", "sigma_mean": "sigma_trace.npy", "spike_events": "traces.npz", "spike_events_source": "raw_npz"},
        "metric_consistency": {"spike_events": {"status": "PASS", "tolerance": 0.0, "policy": "exact_match", "summary_source": "summary_metrics.json", "source": "traces.npz", "summary": 10, "recomputed": 10, "delta": 0.0}, "rate_mean_hz": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "population_rate_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}, "sigma_mean": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "sigma_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}},
        "artifacts_verified": [],
        "failure_reasons": ["Gate G6_determinism_replay is planned but not wired"],
    }
    jsonschema.validate(instance=payload, schema=schema)


def test_proof_report_schema_rejects_invalid_verdict_code_type() -> None:
    schema = _load_json(ROOT / "schemas" / "proof-report.schema.json")
    invalid_payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-export-proof",
        "export_proof": True,
        "timestamp_utc": "1970-01-01T00:00:00Z",
        "seed": 123,
        "verdict": "FAIL",
        "verdict_code": "not-integer",
        "gates": {
            "G1_active_spiking": {"status": "PASS"},
            "G2_rate_in_bounds": {"status": "PASS"},
            "G3_sigma_in_range": {"status": "PASS"},
            "G4_core_artifacts_complete": {"status": "PASS"},
            "G5_manifest_valid": {"status": "PASS"},
            "G6_determinism_replay": {"status": "INCONCLUSIVE"},
            "G7_avalanche_evidence_sufficient": {"status": "INCONCLUSIVE"},
            "G8_reproducibility_envelope": {"status": "INCONCLUSIVE"},
            "G9_metrics_trace_consistency": {"status": "PASS"},
        },
        "metrics": {},
        "recomputed_metrics": {},
        "summary_metrics_snapshot": {},
        "recompute_sources": {"rate_mean_hz": "population_rate_trace.npy", "sigma_mean": "sigma_trace.npy", "spike_events": "traces.npz", "spike_events_source": "raw_npz"},
        "metric_consistency": {"spike_events": {"status": "PASS", "tolerance": 0.0, "policy": "exact_match", "summary_source": "summary_metrics.json", "source": "traces.npz", "summary": 10, "recomputed": 10, "delta": 0.0}, "rate_mean_hz": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "population_rate_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}, "sigma_mean": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "sigma_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}},
        "artifacts_verified": [],
        "failure_reasons": ["bad code type"],
    }
    try:
        jsonschema.validate(instance=invalid_payload, schema=schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("invalid verdict_code type was accepted")


def test_run_without_config_or_profile_fails() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "run",
        ],
        capture_output=True,
        text=True,
        env=_cli_env(),
        cwd=ROOT,
    )
    assert proc.returncode == 2
    assert "provide CONFIG or --profile canonical" in proc.stderr


def test_run_profile_canonical_executes_bootstrap_config(tmp_path: Path) -> None:
    output_dir = tmp_path / "canonical_run"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "run",
            "--profile",
            "canonical",
            "--plot",
            "--export-proof",
            "--output",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    summary_path = output_dir / "summary_metrics.json"
    criticality_path = output_dir / "criticality_report.json"
    avalanche_path = output_dir / "avalanche_report.json"
    phase_space_path = output_dir / "phase_space_report.json"
    assert summary_path.exists()
    assert criticality_path.exists()
    assert avalanche_path.exists()
    assert phase_space_path.exists()
    payload = _load_json(summary_path)
    criticality = _load_json(criticality_path)
    assert payload["spike_events"] > 0
    assert criticality["sigma_mean"] == payload["sigma_mean"]
