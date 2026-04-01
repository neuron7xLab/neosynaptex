from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _full_gates() -> dict[str, dict[str, str]]:
    return {
        "G1_active_spiking": {"status": "PASS"},
        "G2_rate_in_bounds": {"status": "PASS"},
        "G3_sigma_in_range": {"status": "PASS"},
        "G4_core_artifacts_complete": {"status": "PASS"},
        "G5_manifest_valid": {"status": "PASS"},
        "G6_determinism_replay": {"status": "INCONCLUSIVE"},
        "G7_avalanche_evidence_sufficient": {"status": "INCONCLUSIVE"},
        "G8_reproducibility_envelope": {"status": "INCONCLUSIVE"},
        "G9_metrics_trace_consistency": {"status": "PASS"},
    }


def test_proof_report_schema_accepts_full_payload() -> None:
    schema = _load_json(ROOT / "schemas" / "proof-report.schema.json")
    payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-export-proof",
        "export_proof": True,
        "verdict": "INCONCLUSIVE",
        "verdict_code": 1,
        "timestamp_utc": "1970-01-01T00:00:00Z",
        "seed": 42,
        "gates": _full_gates(),
        "metrics": {},
        "recomputed_metrics": {},
        "summary_metrics_snapshot": {},
        "recompute_sources": {"rate_mean_hz": "population_rate_trace.npy", "sigma_mean": "sigma_trace.npy", "spike_events": "traces.npz", "spike_events_source": "raw_npz"},
        "metric_consistency": {"spike_events": {"status": "PASS", "tolerance": 0.0, "policy": "exact_match", "summary_source": "summary_metrics.json", "source": "traces.npz", "summary": 10, "recomputed": 10, "delta": 0.0}, "rate_mean_hz": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "population_rate_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}, "sigma_mean": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "sigma_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}},
        "artifacts_verified": ["summary_metrics.json"],
        "failure_reasons": ["G6_determinism_replay unresolved"],
    }
    jsonschema.validate(instance=payload, schema=schema)


def test_proof_report_schema_accepts_gate_errors_payload() -> None:
    schema = _load_json(ROOT / "schemas" / "proof-report.schema.json")
    gates = _full_gates()
    gates["G5_manifest_valid"] = {"status": "FAIL", "errors": ["summary_metrics.json hash mismatch"]}
    payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-export-proof",
        "export_proof": True,
        "verdict": "FAIL",
        "verdict_code": 2,
        "timestamp_utc": "1970-01-01T00:00:00Z",
        "seed": 42,
        "gates": gates,
        "metrics": {},
        "recomputed_metrics": {},
        "summary_metrics_snapshot": {},
        "recompute_sources": {"rate_mean_hz": "population_rate_trace.npy", "sigma_mean": "sigma_trace.npy", "spike_events": "traces.npz", "spike_events_source": "raw_npz"},
        "metric_consistency": {"spike_events": {"status": "PASS", "tolerance": 0.0, "policy": "exact_match", "summary_source": "summary_metrics.json", "source": "traces.npz", "summary": 10, "recomputed": 10, "delta": 0.0}, "rate_mean_hz": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "population_rate_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}, "sigma_mean": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "sigma_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}},
        "artifacts_verified": ["summary_metrics.json"],
        "failure_reasons": ["G5_manifest_valid failed"],
    }
    jsonschema.validate(instance=payload, schema=schema)


def test_proof_report_schema_rejects_invalid_gates_shape() -> None:
    schema = _load_json(ROOT / "schemas" / "proof-report.schema.json")
    payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-base",
        "export_proof": False,
        "verdict": "PASS",
        "verdict_code": 0,
        "timestamp_utc": "1970-01-01T00:00:00Z",
        "seed": 42,
        "gates": {"G1_active_spiking": {"status": "PASS"}},
        "metrics": {},
        "recomputed_metrics": {},
        "summary_metrics_snapshot": {},
        "recompute_sources": {"rate_mean_hz": "population_rate_trace.npy", "sigma_mean": "sigma_trace.npy", "spike_events": "traces.npz", "spike_events_source": "raw_npz"},
        "metric_consistency": {"spike_events": {"status": "PASS", "tolerance": 0.0, "policy": "exact_match", "summary_source": "summary_metrics.json", "source": "traces.npz", "summary": 10, "recomputed": 10, "delta": 0.0}, "rate_mean_hz": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "population_rate_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}, "sigma_mean": {"status": "PASS", "tolerance": 1e-12, "policy": "abs_delta <= tolerance", "summary_source": "summary_metrics.json", "source": "sigma_trace.npy", "summary": 1.0, "recomputed": 1.0, "delta": 0.0}},
        "artifacts_verified": [],
        "failure_reasons": [],
    }
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema accepted payload without required gates")


def test_run_manifest_schema_accepts_valid_manifest_payload() -> None:
    schema = _load_json(ROOT / "schemas" / "run-manifest.schema.json")
    payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-export-proof",
        "export_proof": True,
        "cmd": "bnsyn run --profile canonical --plot --export-proof",
        "seed": 123,
        "steps": 100,
        "N": 10,
        "dt_ms": 0.1,
        "duration_ms": 10.0,
        "completed_stages": [
            "live_run",
            "summary_reports",
            "avalanche_and_fit",
            "robustness_envelope",
            "manifest",
            "proof_report",
            "product_surface",
        ],
        "artifacts": {
            "summary_metrics.json": "0" * 64,
            "run_manifest.json": "2" * 64,
            "proof_report.json": "1" * 64,
        },
    }
    jsonschema.validate(instance=payload, schema=schema)


def test_run_manifest_schema_accepts_base_manifest_payload() -> None:
    schema = _load_json(ROOT / "schemas" / "run-manifest.schema.json")
    payload = {
        "schema_version": "1.1.0",
        "bundle_contract": "canonical-base",
        "export_proof": False,
        "cmd": "bnsyn run --profile canonical --plot",
        "seed": 123,
        "steps": 100,
        "N": 10,
        "dt_ms": 0.1,
        "duration_ms": 10.0,
        "completed_stages": [
            "live_run",
            "summary_reports",
            "avalanche_and_fit",
            "robustness_envelope",
            "manifest",
            "proof_report",
            "product_surface",
        ],
        "artifacts": {
            "summary_metrics.json": "0" * 64,
            "run_manifest.json": "2" * 64,
        },
    }
    jsonschema.validate(instance=payload, schema=schema)
