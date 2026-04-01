from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import jsonschema

from bnsyn.experiments.declarative import run_canonical_live_bundle
from bnsyn.proof import evaluate as proof_evaluate
from bnsyn.proof.contracts import (
    BASE_ARTIFACTS,
    CANONICAL_BASE_COMMAND,
    CANONICAL_BASE_CONTRACT,
    CANONICAL_EXPORT_PROOF_COMMAND,
    CANONICAL_EXPORT_PROOF_CONTRACT,
    EXPORT_PROOF_ARTIFACTS,
    ManifestMode,
    artifacts_for_export_proof,
    bundle_contract_for_export_proof,
    command_for_export_proof,
    mode_from_manifest,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _g9_gate_payload(rounding_tolerance: float = 1e-6) -> dict:
    return {
        "threshold": {
            "policy": "summary_is_secondary_snapshot",
            "metrics": {
                "spike_events": {
                    "tolerance": 0.0,
                    "policy": "exact_match",
                    "policy_by_source": {
                        "raw_npz": "exact_match",
                        "rate_trace_reconstruction": "exact_reconstruction_after_integer_check",
                        "unverifiable": "unverifiable_fails_closed",
                        "canonical_raw_npz_malformed": "malformed_raw_fails_closed",
                    },
                },
                "rate_mean_hz": {"tolerance": 1e-12, "policy": "abs_delta <= tolerance"},
                "sigma_mean": {"tolerance": 1e-12, "policy": "abs_delta <= tolerance"},
            },
            "recompute_policy": {
                "spike_events": {
                    "canonical_raw_artifact": "traces.npz",
                    "rounding_tolerance": rounding_tolerance,
                }
            },
        }
    }


def test_contract_helpers_select_mode_specific_constants() -> None:
    assert command_for_export_proof(False) == CANONICAL_BASE_COMMAND
    assert command_for_export_proof(True) == CANONICAL_EXPORT_PROOF_COMMAND
    assert bundle_contract_for_export_proof(False) == CANONICAL_BASE_CONTRACT
    assert bundle_contract_for_export_proof(True) == CANONICAL_EXPORT_PROOF_CONTRACT
    assert artifacts_for_export_proof(False) == BASE_ARTIFACTS
    assert artifacts_for_export_proof(True) == EXPORT_PROOF_ARTIFACTS


def test_mode_from_manifest_validates_types_and_mode_rules() -> None:
    mode, errors = mode_from_manifest({"cmd": 1, "bundle_contract": None, "export_proof": "x", "artifacts": []})
    assert mode is None
    assert "manifest cmd must be string" in errors
    assert "manifest bundle_contract invalid" in errors
    assert "manifest export_proof must be boolean" in errors
    assert "manifest artifacts must be object" in errors

    export_manifest = {
        "cmd": CANONICAL_EXPORT_PROOF_COMMAND,
        "bundle_contract": CANONICAL_EXPORT_PROOF_CONTRACT,
        "export_proof": True,
        "artifacts": {"proof_report.json": "0" * 64},
    }
    mode, errors = mode_from_manifest(export_manifest)
    assert errors == []
    assert mode == ManifestMode(
        bundle_contract=CANONICAL_EXPORT_PROOF_CONTRACT,
        export_proof=True,
        cmd=CANONICAL_EXPORT_PROOF_COMMAND,
    )

    base_manifest = {
        "cmd": CANONICAL_BASE_COMMAND,
        "bundle_contract": CANONICAL_BASE_CONTRACT,
        "export_proof": False,
        "artifacts": {"proof_report.json": "0" * 64},
    }
    mode, errors = mode_from_manifest(base_manifest)
    assert mode is None
    assert "base mode forbids proof_report.json manifest entry" in errors


def test_load_json_and_registry_parsing_fail_closed_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    not_obj = tmp_path / "not_obj.json"
    not_obj.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected JSON object"):
        proof_evaluate._load_json(not_obj)

    missing_registry = tmp_path / "missing_registry.json"
    _write_json(missing_registry, {"schema_version": "1.0.0"})
    monkeypatch.setattr(proof_evaluate, "VALIDATION_GATES_PATH", missing_registry)
    with pytest.raises(ValueError, match="validation gate registry missing"):
        proof_evaluate._load_gate_registry()

    malformed_registry = tmp_path / "malformed_registry.json"
    _write_json(malformed_registry, {"registry": [{"id": 3}]})
    monkeypatch.setattr(proof_evaluate, "VALIDATION_GATES_PATH", malformed_registry)
    with pytest.raises(ValueError, match="malformed gate registry entry"):
        proof_evaluate._load_gate_registry()


def test_required_artifacts_from_registry_fail_closed_paths() -> None:
    mode = ManifestMode(bundle_contract=CANONICAL_BASE_CONTRACT, export_proof=False, cmd=CANONICAL_BASE_COMMAND)
    with pytest.raises(ValueError, match="G4 threshold missing"):
        proof_evaluate._required_artifacts_from_registry({"G4_core_artifacts_complete": {}}, mode)

    with pytest.raises(ValueError, match="G4 required_artifacts_by_mode missing"):
        proof_evaluate._required_artifacts_from_registry(
            {"G4_core_artifacts_complete": {"threshold": {}}},
            mode,
        )

    with pytest.raises(ValueError, match="invalid for canonical-base"):
        proof_evaluate._required_artifacts_from_registry(
            {"G4_core_artifacts_complete": {"threshold": {"required_artifacts_by_mode": {"canonical-base": [1]}}}},
            mode,
        )

    with pytest.raises(ValueError, match="registry/runtime artifact contract drift"):
        proof_evaluate._required_artifacts_from_registry(
            {
                "G4_core_artifacts_complete": {
                    "threshold": {"required_artifacts_by_mode": {"canonical-base": ["summary_metrics.json"]}}
                }
            },
            mode,
        )


def test_numeric_gate_validation_failures() -> None:
    with pytest.raises(ValueError, match="numeric gate threshold missing"):
        proof_evaluate._evaluate_numeric_gate({}, {})
    with pytest.raises(ValueError, match="numeric gate metric missing"):
        proof_evaluate._evaluate_numeric_gate({"threshold": {"op": ">", "value": 1}}, {})
    with pytest.raises(ValueError, match="metric spike_events missing"):
        proof_evaluate._evaluate_numeric_gate({"threshold": {"metric": "spike_events", "op": ">", "value": 1}}, {})
    with pytest.raises(ValueError, match="numeric gate value missing"):
        proof_evaluate._evaluate_numeric_gate({"threshold": {"metric": "spike_events", "op": ">", "value": "x"}}, {"spike_events": 2})
    with pytest.raises(ValueError, match="between gate requires"):
        proof_evaluate._evaluate_numeric_gate(
            {"threshold": {"metric": "spike_events", "op": "between", "value": [1]}},
            {"spike_events": 2},
        )
    with pytest.raises(ValueError, match="unsupported gate op"):
        proof_evaluate._evaluate_numeric_gate(
            {"threshold": {"metric": "spike_events", "op": "<", "value": 3}},
            {"spike_events": 2},
        )


def test_g4_and_g5_error_paths_and_unreadable_proof_report(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir, export_proof=True)

    manifest = _load_json(out_dir / "run_manifest.json")
    g4, verified = proof_evaluate.evaluate_gate_g4_artifact_contract(
        out_dir,
        {"artifacts": []},
        [],
        BASE_ARTIFACTS,
    )
    assert g4["status"] == "FAIL"
    assert verified == []

    g4, verified = proof_evaluate.evaluate_gate_g4_artifact_contract(out_dir, manifest, ["mode bad"], BASE_ARTIFACTS)
    assert g4["status"] == "FAIL"
    assert verified == []

    # unreadable proof report should be fail-closed inside G5 validation details
    (out_dir / "proof_report.json").write_text("{broken-json", encoding="utf-8")
    g5 = proof_evaluate.evaluate_gate_g5_manifest_valid(out_dir, manifest, [])
    assert g5["status"] == "FAIL"
    assert any("proof_report.json unreadable" in e for e in g5["errors"])

    manifest_bad_self = dict(manifest)
    manifest_bad_self["artifacts"] = dict(manifest["artifacts"])
    manifest_bad_self["artifacts"]["run_manifest.json"] = "not-self"
    g5 = proof_evaluate.evaluate_gate_g5_manifest_valid(out_dir, manifest_bad_self, [])
    assert g5["status"] == "FAIL"
    assert "run_manifest.json hash mismatch" in g5["errors"]

    manifest_bad_types = dict(manifest)
    manifest_bad_types["artifacts"] = {"summary_metrics.json": 1}
    g5 = proof_evaluate.evaluate_gate_g5_manifest_valid(out_dir, manifest_bad_types, [])
    assert g5["status"] == "FAIL"
    assert "artifact entries must be string:string" in g5["errors"]

    g5 = proof_evaluate.evaluate_gate_g5_manifest_valid(out_dir, {"artifacts": []}, [])
    assert g5["status"] == "FAIL"
    assert "manifest artifacts is not an object" in g5["errors"]


def test_misc_helpers_and_discover_seed_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid gate status"):
        proof_evaluate._gate_state({"G1": {"status": "bad"}}, "G1")

    verdict, code, reasons = proof_evaluate._compute_verdict(
        {"G1": {"status": "PASS"}},
        {"G1": {"status": "wired"}},
    )
    assert (verdict, code, reasons) == ("PASS", 0, [])

    artifact_dir = tmp_path / "seed"
    artifact_dir.mkdir()
    assert proof_evaluate._discover_seed(artifact_dir) == 0
    _write_json(artifact_dir / "summary_metrics.json", {"seed": -1})
    assert proof_evaluate._discover_seed(artifact_dir) == 0
    _write_json(artifact_dir / "summary_metrics.json", {"seed": 7})
    assert proof_evaluate._discover_seed(artifact_dir) == 7


def test_evaluate_and_emit_non_export_branch_writes_report(tmp_path: Path) -> None:
    out_dir = tmp_path / "base"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir, export_proof=False)
    result = proof_evaluate.evaluate_and_emit(out_dir)
    assert result.report_path == out_dir / "proof_report.json"
    assert result.report["bundle_contract"] == "canonical-base"
    assert (out_dir / "proof_report.json").exists()


def test_update_manifest_proof_hash_requires_artifacts_object(tmp_path: Path) -> None:
    out_dir = tmp_path / "artifact"
    out_dir.mkdir()
    _write_json(out_dir / "run_manifest.json", {"artifacts": []})
    with pytest.raises(ValueError, match="run_manifest artifacts must be object"):
        proof_evaluate._update_manifest_proof_hash(out_dir, "0" * 64)


def test_evaluate_and_emit_stabilizes_on_third_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()
    _write_json(out_dir / "run_manifest.json", {"export_proof": True, "artifacts": {"run_manifest.json": "0" * 64}})

    reports = iter(
        [
            {"k": "first"},
            {"k": "second"},
            {"k": "third"},
            {"k": "third"},
        ]
    )

    def fake_eval(_: Path) -> dict:
        return next(reports)

    monkeypatch.setattr(proof_evaluate, "evaluate_all_gates", fake_eval)
    monkeypatch.setattr(proof_evaluate, "emit_proof_report", lambda result, artifact_dir: Path(artifact_dir) / "proof_report.json")
    monkeypatch.setattr(proof_evaluate, "sha256_file", lambda _: "a" * 64)
    monkeypatch.setattr(proof_evaluate, "_update_manifest_proof_hash", lambda *_args: None)

    result = proof_evaluate.evaluate_and_emit(out_dir)
    assert result.report == {"k": "third"}
    assert result.report_path == out_dir / "proof_report.json"


def test_evaluate_and_emit_raises_if_not_stable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()
    _write_json(out_dir / "run_manifest.json", {"export_proof": True, "artifacts": {"run_manifest.json": "0" * 64}})

    reports = iter(
        [
            {"k": "first"},
            {"k": "second"},
            {"k": "third"},
            {"k": "fourth"},
        ]
    )

    monkeypatch.setattr(proof_evaluate, "evaluate_all_gates", lambda _: next(reports))
    monkeypatch.setattr(proof_evaluate, "emit_proof_report", lambda result, artifact_dir: Path(artifact_dir) / "proof_report.json")
    monkeypatch.setattr(proof_evaluate, "sha256_file", lambda _: "a" * 64)
    monkeypatch.setattr(proof_evaluate, "_update_manifest_proof_hash", lambda *_args: None)

    with pytest.raises(RuntimeError, match="failed to stabilize"):
        proof_evaluate.evaluate_and_emit(out_dir)


def test_load_numeric_trace_validation_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.npy"
    with pytest.raises(ValueError, match="missing required trace artifact"):
        proof_evaluate._load_numeric_trace(missing, metric_name="rate_mean_hz")

    arr_path = tmp_path / "trace.npy"
    np.save(arr_path, np.asarray([], dtype=float))
    with pytest.raises(ValueError, match="is empty"):
        proof_evaluate._load_numeric_trace(arr_path, metric_name="rate_mean_hz")

    np.save(arr_path, np.asarray([1.0, np.nan], dtype=float))
    with pytest.raises(ValueError, match="contains non-finite"):
        proof_evaluate._load_numeric_trace(arr_path, metric_name="rate_mean_hz")

    monkeypatch.setattr(proof_evaluate.np, "load", lambda _: [1.0, 2.0])
    with pytest.raises(ValueError, match="is not a numpy array"):
        proof_evaluate._load_numeric_trace(arr_path, metric_name="rate_mean_hz")


def test_extract_spike_events_from_canonical_raw_npz_edge_paths(tmp_path: Path) -> None:
    bad_npz = tmp_path / "traces.npz"
    np.savez(bad_npz, spike_steps=np.asarray([[1, 2]], dtype=np.int64))
    with pytest.raises(ValueError, match="spike_steps must be 1D"):
        proof_evaluate._extract_spike_events_from_canonical_raw_npz(bad_npz)

    good_npz = tmp_path / "traces.npz"
    np.savez(good_npz, spike_steps=np.asarray([1, 2, 3], dtype=np.int64), spike_neurons=np.asarray([0, 1, 2], dtype=np.int64), dt_ms=np.asarray([0.1]), N=np.asarray([100]))
    events, metadata = proof_evaluate._extract_spike_events_from_canonical_raw_npz(good_npz)
    assert events == 3
    assert metadata["dt_ms"] == 0.1
    assert metadata["N"] == 100.0


def test_recompute_metrics_from_artifacts_unverifiable_paths(tmp_path: Path) -> None:
    np.save(tmp_path / "population_rate_trace.npy", np.asarray([0.0, 0.0], dtype=float))
    np.save(tmp_path / "sigma_trace.npy", np.asarray([1.0, 1.0], dtype=float))

    no_meta = proof_evaluate.recompute_metrics_from_artifacts(tmp_path, manifest={}, g9_gate=_g9_gate_payload())
    assert any("missing dt_ms or N" in err for err in no_meta["errors"])

    non_positive = proof_evaluate.recompute_metrics_from_artifacts(
        tmp_path,
        manifest={"dt_ms": -1.0, "N": 100},
        g9_gate=_g9_gate_payload(),
    )
    assert any("non-positive dt_ms or N" in err for err in non_positive["errors"])


def test_recompute_metrics_from_artifacts_rate_reconstruction_tolerance_failure(tmp_path: Path) -> None:
    np.save(tmp_path / "population_rate_trace.npy", np.asarray([1.23456789], dtype=float))
    np.save(tmp_path / "sigma_trace.npy", np.asarray([1.0], dtype=float))
    recomputed = proof_evaluate.recompute_metrics_from_artifacts(
        tmp_path,
        manifest={"dt_ms": 1.0, "N": 1},
        g9_gate=_g9_gate_payload(),
    )
    assert any("non-integer reconstruction" in err for err in recomputed["errors"])


def test_metric_consistency_gate_reports_missing_metrics() -> None:
    result = proof_evaluate.evaluate_gate_g9_metric_consistency(
        summary={"rate_mean_hz": 1.0},
        recomputed={"metrics": {"rate_mean_hz": 1.0, "sigma_mean": 1.0}, "errors": [], "sources": {}},
        gate=_g9_gate_payload(),
    )
    assert result["status"] == "FAIL"
    assert "spike_events: missing summary metric" in result["errors"]


def test_extract_manifest_numeric_reads_manifest_only() -> None:
    assert proof_evaluate._extract_manifest_numeric({"dt_ms": 0.5}, "dt_ms") == 0.5
    assert proof_evaluate._extract_manifest_numeric({}, "dt_ms") is None


def test_parse_g9_runtime_policy_fail_closed_paths() -> None:
    with pytest.raises(ValueError, match="G9 threshold policy missing"):
        proof_evaluate._parse_g9_runtime_policy({"threshold": {}})

    with pytest.raises(ValueError, match="G9 metric policy missing for spike_events"):
        proof_evaluate._parse_g9_runtime_policy(
            {
                "threshold": {
                    "policy": "summary_is_secondary_snapshot",
                    "metrics": {},
                    "recompute_policy": {"spike_events": {"canonical_raw_artifact": "traces.npz", "rounding_tolerance": 1e-6}},
                }
            }
        )

    with pytest.raises(ValueError, match="rounding_tolerance must be non-negative"):
        proof_evaluate._parse_g9_runtime_policy(
            {
                "threshold": {
                    "policy": "summary_is_secondary_snapshot",
                    "metrics": {
                        "spike_events": {"tolerance": 0.0, "policy": "exact_match", "policy_by_source": {"raw_npz": "exact_match"}},
                        "rate_mean_hz": {"tolerance": 1e-12, "policy": "abs_delta <= tolerance"},
                        "sigma_mean": {"tolerance": 1e-12, "policy": "abs_delta <= tolerance"},
                    },
                    "recompute_policy": {"spike_events": {"canonical_raw_artifact": "traces.npz", "rounding_tolerance": -1e-6}},
                }
            }
        )


def test_parse_g9_runtime_policy_accepts_registry_contract() -> None:
    registry = proof_evaluate._load_gate_registry()
    policy = proof_evaluate._parse_g9_runtime_policy(registry["G9_metrics_trace_consistency"])
    assert policy["policy"] == "summary_is_secondary_snapshot"
    assert policy["metrics"]["spike_events"]["policy_by_source"]["raw_npz"] == "exact_match"
    assert policy["spike_events_recompute"]["canonical_raw_artifact"] == "traces.npz"


def test_fail_closed_report_output_passes_schema_validation(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "proof-report.schema.json").read_text(encoding="utf-8"))
    report = proof_evaluate._fail_closed_report(tmp_path, "test-reason")
    jsonschema.validate(instance=report, schema=schema)
    assert report["verdict"] == "FAIL"
    assert report["recompute_sources"]["spike_events_source"] == "unverifiable"
    assert report["metric_consistency"]["spike_events"]["status"] == "FAIL"
    assert report["metric_consistency"]["rate_mean_hz"]["status"] == "FAIL"
    assert report["metric_consistency"]["sigma_mean"]["status"] == "FAIL"


def test_resolve_canonical_spike_source_present_and_absent(tmp_path: Path) -> None:
    existing = tmp_path / "traces.npz"
    existing.write_bytes(b"")
    result = proof_evaluate._resolve_canonical_spike_source(tmp_path, "traces.npz")
    assert result == existing

    absent = proof_evaluate._resolve_canonical_spike_source(tmp_path, "nonexistent.npz")
    assert absent is None


def test_extract_spike_events_from_canonical_raw_npz_missing_spike_steps(tmp_path: Path) -> None:
    npz_path = tmp_path / "traces.npz"
    np.savez(npz_path, other_key=np.asarray([1, 2, 3]))
    with pytest.raises(ValueError, match="missing spike_steps"):
        proof_evaluate._extract_spike_events_from_canonical_raw_npz(npz_path)


def test_g9_threshold_raises_on_missing_threshold() -> None:
    with pytest.raises(ValueError, match="G9 threshold missing"):
        proof_evaluate._g9_threshold({})

    with pytest.raises(ValueError, match="G9 threshold missing"):
        proof_evaluate._g9_threshold({"threshold": "not-a-dict"})


def test_g9_metric_consistency_raises_on_missing_metrics_policy() -> None:
    with pytest.raises(ValueError, match="G9 threshold.metrics missing"):
        proof_evaluate.evaluate_gate_g9_metric_consistency(
            summary={"spike_events": 10},
            recomputed={"metrics": {}, "errors": [], "sources": {}},
            gate={"threshold": {"policy": "no_metrics_key"}},
        )


def test_parse_g9_metric_policy_error_paths() -> None:
    # Path 1: entry not a dict (metric missing from policy)
    with pytest.raises(ValueError, match="G9 metric policy missing for spike_events"):
        proof_evaluate._parse_g9_metric_policy({}, "spike_events")

    # Path 2: tolerance not a number
    with pytest.raises(ValueError, match="G9 metric tolerance missing for rate_mean_hz"):
        proof_evaluate._parse_g9_metric_policy(
            {"rate_mean_hz": {"tolerance": "not-a-number", "policy": "abs_delta <= tolerance"}},
            "rate_mean_hz",
        )

    # Path 3: tolerance negative
    with pytest.raises(ValueError, match="G9 metric tolerance must be non-negative for sigma_mean"):
        proof_evaluate._parse_g9_metric_policy(
            {"sigma_mean": {"tolerance": -1.0, "policy": "abs_delta <= tolerance"}},
            "sigma_mean",
        )

    # Path 4: policy label missing/empty
    with pytest.raises(ValueError, match="G9 metric policy label missing for rate_mean_hz"):
        proof_evaluate._parse_g9_metric_policy(
            {"rate_mean_hz": {"tolerance": 1e-12, "policy": ""}},
            "rate_mean_hz",
        )

    # Path 5: policy_by_source malformed for spike_events
    with pytest.raises(ValueError, match="G9 spike_events policy_by_source malformed"):
        proof_evaluate._parse_g9_metric_policy(
            {
                "spike_events": {
                    "tolerance": 0.0,
                    "policy": "exact_match",
                    "policy_by_source": {"raw_npz": 42},
                }
            },
            "spike_events",
        )

    # Happy path: 0.0 tolerance is valid (no false-negative from 'or' bug)
    result = proof_evaluate._parse_g9_metric_policy(
        {
            "spike_events": {
                "tolerance": 0.0,
                "policy": "exact_match",
                "policy_by_source": {"raw_npz": "exact_match"},
            }
        },
        "spike_events",
    )
    assert result["tolerance"] == 0.0


def test_recompute_metrics_from_artifacts_zero_rounding_tolerance_is_exact(tmp_path: Path) -> None:
    # A rate trace that produces a non-integer per-step count.
    # With tolerance=0.0, reconstruction must fail.
    np.save(tmp_path / "population_rate_trace.npy", np.asarray([1.23456789], dtype=float))
    np.save(tmp_path / "sigma_trace.npy", np.asarray([1.0], dtype=float))

    gate_with_zero_tolerance = {
        "threshold": {
            "policy": "summary_is_secondary_snapshot",
            "metrics": {
                "spike_events": {
                    "tolerance": 0.0,
                    "policy": "exact_match",
                    "policy_by_source": {
                        "raw_npz": "exact_match",
                        "rate_trace_reconstruction": "exact_reconstruction_after_integer_check",
                        "unverifiable": "unverifiable_fails_closed",
                        "canonical_raw_npz_malformed": "malformed_raw_fails_closed",
                    },
                },
                "rate_mean_hz": {"tolerance": 1e-12, "policy": "abs_delta <= tolerance"},
                "sigma_mean": {"tolerance": 1e-12, "policy": "abs_delta <= tolerance"},
            },
            "recompute_policy": {
                "spike_events": {
                    "canonical_raw_artifact": "traces.npz",
                    "rounding_tolerance": 0.0,
                }
            },
        }
    }

    result = proof_evaluate.recompute_metrics_from_artifacts(
        tmp_path,
        manifest={"dt_ms": 1.0, "N": 1},
        g9_gate=gate_with_zero_tolerance,
    )
    assert any("non-integer reconstruction" in err for err in result["errors"]), (
        "Expected reconstruction to fail with tolerance=0.0, but it passed — "
        "likely the 'or' operator bug is still present"
    )


def test_recompute_metrics_from_artifacts_uses_canonical_raw_and_metadata(tmp_path: Path) -> None:
    np.save(tmp_path / "population_rate_trace.npy", np.asarray([0.0, 0.0], dtype=float))
    np.save(tmp_path / "sigma_trace.npy", np.asarray([1.0, 1.0], dtype=float))
    np.savez(
        tmp_path / "traces.npz",
        spike_steps=np.asarray([1, 2, 3], dtype=np.int64),
        spike_neurons=np.asarray([0, 1, 2], dtype=np.int64),
        dt_ms=np.asarray([0.1]),
        N=np.asarray([10]),
    )

    result = proof_evaluate.recompute_metrics_from_artifacts(
        tmp_path,
        manifest={"dt_ms": 0.1, "N": 10},
        g9_gate=_g9_gate_payload(),
    )
    assert result["spike_events_source"] == "raw_npz"
    assert result["metrics"]["spike_events"] == 3
    assert result["sources"]["spike_events"] == "traces.npz"
    assert result["spike_events_metadata"]["source"] == "traces.npz"


def test_recompute_metrics_from_artifacts_steps_mismatch_fails(tmp_path: Path) -> None:
    np.save(tmp_path / "population_rate_trace.npy", np.asarray([0.0, 0.0], dtype=float))
    np.save(tmp_path / "sigma_trace.npy", np.asarray([1.0, 1.0], dtype=float))

    result = proof_evaluate.recompute_metrics_from_artifacts(
        tmp_path,
        manifest={"dt_ms": 0.1, "N": 10, "steps": 3},
        g9_gate=_g9_gate_payload(),
    )
    assert any("steps mismatch" in err for err in result["errors"])


def test_metric_consistency_gate_reports_missing_recomputed_metric() -> None:
    result = proof_evaluate.evaluate_gate_g9_metric_consistency(
        summary={"spike_events": 1, "rate_mean_hz": 1.0, "sigma_mean": 1.0},
        recomputed={"metrics": {"spike_events": 1, "rate_mean_hz": 1.0}, "errors": [], "sources": {}},
        gate=_g9_gate_payload(),
    )
    assert result["status"] == "FAIL"
    assert "sigma_mean: missing recomputed metric" in result["errors"]
