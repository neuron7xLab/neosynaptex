from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import numpy as np
import yaml  # type: ignore[import-untyped]

from bnsyn.experiments.declarative import run_canonical_live_bundle


def test_canonical_live_bundle_writes_required_outputs(tmp_path: Path) -> None:
    bundle = run_canonical_live_bundle(
        "configs/canonical_profile.yaml",
        artifact_dir=tmp_path / "canonical_run",
    )

    out_dir = Path(str(bundle["artifact_dir"]))
    assert out_dir == tmp_path / "canonical_run"

    summary_path = out_dir / "summary_metrics.json"
    manifest_path = out_dir / "run_manifest.json"
    criticality_report_path = out_dir / "criticality_report.json"
    avalanche_report_path = out_dir / "avalanche_report.json"
    phase_space_report_path = out_dir / "phase_space_report.json"
    emergence_plot_path = out_dir / "emergence_plot.png"
    raster_path = out_dir / "raster_plot.png"
    rate_plot_path = out_dir / "population_rate_plot.png"
    population_rate_trace_path = out_dir / "population_rate_trace.npy"
    sigma_trace_path = out_dir / "sigma_trace.npy"
    coherence_trace_path = out_dir / "coherence_trace.npy"
    phase_space_rate_sigma_path = out_dir / "phase_space_rate_sigma.png"
    phase_space_rate_coherence_path = out_dir / "phase_space_rate_coherence.png"
    phase_space_activity_map_path = out_dir / "phase_space_activity_map.png"
    avalanche_fit_report_path = out_dir / "avalanche_fit_report.json"
    robustness_report_path = out_dir / "robustness_report.json"
    envelope_report_path = out_dir / "envelope_report.json"
    assert summary_path.exists()
    assert manifest_path.exists()
    assert criticality_report_path.exists()
    assert avalanche_report_path.exists()
    assert phase_space_report_path.exists()
    assert emergence_plot_path.exists()
    assert raster_path.exists()
    assert rate_plot_path.exists()
    assert population_rate_trace_path.exists()
    assert sigma_trace_path.exists()
    assert coherence_trace_path.exists()
    assert phase_space_rate_sigma_path.exists()
    assert phase_space_rate_coherence_path.exists()
    assert phase_space_activity_map_path.exists()
    assert avalanche_fit_report_path.exists()
    assert robustness_report_path.exists()
    assert envelope_report_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["cmd"] == "bnsyn run --profile canonical --plot"
    assert manifest["bundle_contract"] == "canonical-base"
    assert manifest["export_proof"] is False
    assert manifest["completed_stages"] == [
        "live_run",
        "summary_reports",
        "avalanche_and_fit",
        "robustness_envelope",
        "manifest",
        "proof_report",
        "product_surface",
    ]
    assert "proof_report.json" not in manifest["artifacts"]

    metrics = json.loads(summary_path.read_text(encoding="utf-8"))
    required = {
        "spike_events",
        "rate_mean_hz",
        "rate_peak_hz",
        "rate_variance",
        "sigma_mean",
        "sigma_final",
        "sigma_variance",
        "steps",
        "dt_ms",
        "duration_ms",
    }
    assert required.issubset(metrics)
    assert metrics["spike_events"] > 0
    assert metrics["rate_mean_hz"] > 0.0
    assert metrics["rate_variance"] > 0.0

    criticality = json.loads(criticality_report_path.read_text(encoding="utf-8"))
    criticality_required = {
        "schema_version", "seed", "N", "dt_ms", "duration_ms", "steps",
        "sigma_mean", "sigma_final", "sigma_variance", "rate_mean_hz",
        "rate_peak_hz", "spike_events", "sigma_distance_from_1",
        "sigma_within_band_fraction", "active_steps_fraction",
        "nonzero_rate_steps_fraction", "burstiness_proxy", "rate_cv",
    }
    assert criticality_required.issubset(criticality)

    avalanche = json.loads(avalanche_report_path.read_text(encoding="utf-8"))
    avalanche_fit = json.loads(avalanche_fit_report_path.read_text(encoding="utf-8"))
    assert {"alpha", "tau", "xmin", "ks_distance", "p_value", "likelihood_ratio", "fit_method", "sample_size", "validity"}.issubset(avalanche_fit)

    robustness = json.loads(robustness_report_path.read_text(encoding="utf-8"))
    assert len(robustness["seed_set"]) == 10
    assert robustness["replay_check"]["identical"] is True

    envelope = json.loads(envelope_report_path.read_text(encoding="utf-8"))
    assert envelope["verdict"] == "PASS"

    avalanche_required = {
        "schema_version", "seed", "N", "dt_ms", "duration_ms", "steps",
        "bin_width_steps", "avalanche_count", "active_bin_fraction", "size_mean",
        "size_max", "duration_mean", "duration_max", "sizes", "durations",
        "nonempty_bins", "largest_avalanche_fraction", "size_variance", "duration_variance",
    }
    assert avalanche_required.issubset(avalanche)


    phase_space = json.loads(phase_space_report_path.read_text(encoding="utf-8"))
    phase_space_required = {
        "schema_version", "seed", "N", "dt_ms", "duration_ms", "steps",
        "state_axes", "point_count", "rate_mean_hz", "sigma_mean",
        "coherence_mean", "coherence_std", "coherence_min", "coherence_max",
        "rate_sigma_correlation", "rate_coherence_correlation", "trajectory_length_l2",
        "bounding_box", "centroid", "activity_map", "artifacts",
    }
    assert set(phase_space.keys()) == phase_space_required

    population_rate_trace = np.load(population_rate_trace_path)
    sigma_trace = np.load(sigma_trace_path)
    coherence_trace = np.load(coherence_trace_path)
    assert population_rate_trace.shape[0] == metrics["steps"]
    assert sigma_trace.shape[0] == metrics["steps"]
    assert coherence_trace.shape[0] == metrics["steps"]
    assert np.all(np.isfinite(coherence_trace))
    assert np.all(coherence_trace >= 0.0)
    assert np.all(coherence_trace <= 1.0)


def test_canonical_live_bundle_is_deterministic(tmp_path: Path) -> None:
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_a)
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_b)

    summary_a = json.loads((out_a / "summary_metrics.json").read_text(encoding="utf-8"))
    summary_b = json.loads((out_b / "summary_metrics.json").read_text(encoding="utf-8"))
    criticality_a = json.loads((out_a / "criticality_report.json").read_text(encoding="utf-8"))
    criticality_b = json.loads((out_b / "criticality_report.json").read_text(encoding="utf-8"))
    avalanche_a = json.loads((out_a / "avalanche_report.json").read_text(encoding="utf-8"))
    avalanche_b = json.loads((out_b / "avalanche_report.json").read_text(encoding="utf-8"))
    phase_a = json.loads((out_a / "phase_space_report.json").read_text(encoding="utf-8"))
    phase_b = json.loads((out_b / "phase_space_report.json").read_text(encoding="utf-8"))
    assert summary_a == summary_b
    assert criticality_a == criticality_b
    assert avalanche_a == avalanche_b
    assert phase_a == phase_b

    manifest_a = json.loads((out_a / "run_manifest.json").read_text(encoding="utf-8"))
    assert "avalanche_report.json" in manifest_a["artifacts"]
    assert "phase_space_report.json" in manifest_a["artifacts"]
    for filename in [
        "population_rate_trace.npy",
        "sigma_trace.npy",
        "coherence_trace.npy",
        "phase_space_rate_sigma.png",
        "phase_space_rate_coherence.png",
        "phase_space_activity_map.png",
        "avalanche_fit_report.json",
        "robustness_report.json",
        "envelope_report.json",
    ]:
        assert (out_a / filename).read_bytes() == (out_b / filename).read_bytes()


def test_cli_run_profile_canonical_end_to_end(monkeypatch, tmp_path: Path) -> None:
    from bnsyn import cli

    monkeypatch.setattr(
        "sys.argv",
        ["bnsyn", "run", "--profile", "canonical", "--output", str(tmp_path / "canonical_run")],
    )

    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 0

    summary_path = tmp_path / "canonical_run" / "summary_metrics.json"
    assert summary_path.exists()
    metrics = json.loads(summary_path.read_text(encoding="utf-8"))
    assert metrics["spike_events"] > 0


def test_canonical_export_proof_manifest_command_truth(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_export"
    run_canonical_live_bundle(
        "configs/canonical_profile.yaml",
        artifact_dir=out_dir,
        export_proof=True,
        generate_product_report=True,
        product_package_version="0.2.0",
    )

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["cmd"] == "bnsyn run --profile canonical --plot --export-proof"
    assert manifest["bundle_contract"] == "canonical-export-proof"
    assert manifest["export_proof"] is True
    assert manifest["completed_stages"][-2:] == ["proof_report", "product_surface"]
    assert "proof_report.json" in manifest["artifacts"]
    assert (out_dir / "proof_report.json").exists()
    assert (out_dir / "product_summary.json").exists()
    assert (out_dir / "index.html").exists()


def test_canonical_live_bundle_resume_after_product_surface_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from bnsyn.experiments import declarative as decl

    out_dir = tmp_path / "resume_product_surface"
    live_run_calls = {"n": 0}
    robustness_calls = {"n": 0}
    product_calls = {"n": 0}

    original_stage_live_run = decl.stage_live_run
    original_stage_robustness = decl.stage_robustness_envelope
    original_product_writer = decl.write_product_report_bundle

    def _count_live_run(context):
        live_run_calls["n"] += 1
        return original_stage_live_run(context)

    def _count_robustness(context):
        robustness_calls["n"] += 1
        return original_stage_robustness(context)

    def _fail_once_product_writer(*args, **kwargs):
        product_calls["n"] += 1
        if product_calls["n"] == 1:
            raise RuntimeError("synthetic product surface failure")
        return original_product_writer(*args, **kwargs)

    monkeypatch.setattr(decl, "stage_live_run", _count_live_run)
    monkeypatch.setattr(decl, "stage_robustness_envelope", _count_robustness)
    monkeypatch.setattr(decl, "write_product_report_bundle", _fail_once_product_writer)

    with pytest.raises(RuntimeError, match="synthetic product surface failure"):
        decl.run_canonical_live_bundle(
            "configs/canonical_profile.yaml",
            artifact_dir=out_dir,
            export_proof=True,
            generate_product_report=True,
            product_package_version="0.2.0",
        )

    failed_stage = json.loads((out_dir / "stage_product_surface.json").read_text(encoding="utf-8"))
    assert failed_stage["status"] == "failed"
    assert "synthetic product surface failure" in failed_stage["failure_reason"]
    failed_manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert failed_manifest["failed_stage"] == "product_surface"
    assert "synthetic product surface failure" in failed_manifest["failure_reason"]
    assert live_run_calls["n"] == 1
    assert robustness_calls["n"] == 1

    bundle = decl.run_canonical_live_bundle(
        "configs/canonical_profile.yaml",
        artifact_dir=out_dir,
        export_proof=True,
        generate_product_report=True,
        product_package_version="0.2.0",
    )

    assert bundle["completed_stages"] == [
        "live_run",
        "summary_reports",
        "avalanche_and_fit",
        "robustness_envelope",
        "manifest",
        "proof_report",
        "product_surface",
    ]
    assert live_run_calls["n"] == 1
    assert robustness_calls["n"] == 1
    assert product_calls["n"] == 2
    assert (out_dir / "product_summary.json").exists()
    assert (out_dir / "index.html").exists()


def test_resume_reruns_from_first_stage_with_hash_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from bnsyn.experiments import declarative as decl

    out_dir = tmp_path / "hash_resume"
    decl.run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)

    call_counts = {"live": 0, "summary": 0}
    original_live = decl.stage_live_run
    original_summary = decl.stage_summary_reports

    def _count_live(context):
        call_counts["live"] += 1
        return original_live(context)

    def _count_summary(context):
        call_counts["summary"] += 1
        return original_summary(context)

    monkeypatch.setattr(decl, "stage_live_run", _count_live)
    monkeypatch.setattr(decl, "stage_summary_reports", _count_summary)

    (out_dir / "summary_metrics.json").write_text('{"tampered": true}\n', encoding="utf-8")

    bundle = decl.run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)

    assert call_counts == {"live": 0, "summary": 1}
    assert bundle["completed_stages"][1] == "summary_reports"


def test_resume_rejects_contract_change(tmp_path: Path) -> None:
    out_dir = tmp_path / "contract_change"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir, export_proof=False)

    with pytest.raises(ValueError, match="contract is immutable"):
        run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir, export_proof=True)


def test_resume_rejects_old_manifest_schema_version(tmp_path: Path) -> None:
    out_dir = tmp_path / "old_schema"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["schema_version"] = "1.0.0"
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)


def test_resume_rejects_policy_change_across_configs(tmp_path: Path) -> None:
    out_dir = tmp_path / "policy_change"
    alt_config = tmp_path / "alt_canonical.yaml"
    payload = yaml.safe_load(Path("configs/canonical_profile.yaml").read_text(encoding="utf-8"))
    payload["simulation"]["external_current_pA"] = float(payload["simulation"]["external_current_pA"]) + 1.0
    alt_config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)

    with pytest.raises(ValueError, match="Resume policy mismatch"):
        run_canonical_live_bundle(alt_config, artifact_dir=out_dir)


def test_artifact_dir_lock_blocks_parallel_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "locked"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".lock").write_text("busy\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="locked"):
        run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)


def test_progress_stream_reports_stage_queue(tmp_path: Path) -> None:
    out_dir = tmp_path / "progress"
    progress = io.StringIO()

    run_canonical_live_bundle(
        "configs/canonical_profile.yaml",
        artifact_dir=out_dir,
        progress_stream=progress,
    )

    text = progress.getvalue()
    assert "[RUN] live_run" in text
    assert "[DONE] product_surface" in text


def test_write_json_uses_atomic_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from bnsyn.experiments import declarative as decl

    target = tmp_path / "payload.json"
    calls: list[tuple[Path, Path]] = []
    original_replace = decl.os.replace

    def _record_replace(src: str | Path, dst: str | Path) -> None:
        calls.append((Path(src), Path(dst)))
        original_replace(src, dst)

    monkeypatch.setattr(decl.os, "replace", _record_replace)

    decl._write_json(target, {"status": "ok"})

    assert calls
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == {"status": "ok"}


def test_build_repro_reports_is_stateless_across_invocations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from bnsyn.experiments import declarative as decl

    config = decl.load_config("configs/canonical_profile.yaml")
    monkeypatch.setattr(decl, "CANONICAL_REPRO_SEEDS", (11,))

    call_count = {"n": 0}

    def _fake_run_emergence_to_disk(*, N: int, dt_ms: float, duration_ms: float, seed: int, external_current_pA: float, output_dir: Path | str):
        call_count["n"] += 1
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        artifact = out / f"run_{seed}_Iext_{int(round(external_current_pA))}pA.npz"
        trace = np.asarray([1.0, 2.0, 3.0], dtype=np.float64)
        np.savez(
            artifact,
            spike_steps=np.asarray([0, 1], dtype=np.int64),
            spike_neurons=np.asarray([0, 1], dtype=np.int64),
            sigma_trace=trace,
            rate_trace_hz=trace,
            coherence_trace=trace / 3.0,
            dt_ms=np.asarray(dt_ms, dtype=np.float64),
            steps=np.asarray(3, dtype=np.int64),
            N=np.asarray(N, dtype=np.int64),
            seed=np.asarray(seed, dtype=np.int64),
            external_current_pA=np.asarray(external_current_pA, dtype=np.float64),
        )
        return {"sigma_mean": 1.0, "rate_mean_hz": 2.0}, artifact.as_posix()

    monkeypatch.setattr(decl, "run_emergence_to_disk", _fake_run_emergence_to_disk)

    decl._build_repro_reports(config)
    decl._build_repro_reports(config)

    # 1 seed run + 2 replay runs per invocation; repeated calls must recompute fully.
    assert call_count["n"] == 6
