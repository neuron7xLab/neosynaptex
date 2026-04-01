from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import numpy as np

from bnsyn.experiments.declarative import _build_phase_space_report, run_canonical_live_bundle


def test_phase_space_handcrafted_trace_is_deterministic() -> None:
    rates = np.asarray([0.0, 1.0, 2.0, 1.0], dtype=np.float64)
    sigmas = np.asarray([1.0, 2.0, 3.0, 2.0], dtype=np.float64)
    coherence = np.asarray([0.2, 0.3, 0.4, 0.1], dtype=np.float64)

    report_a = _build_phase_space_report(
        seed=7,
        n_neurons=4,
        dt_ms=1.0,
        duration_ms=4.0,
        steps=4,
        rate_trace_hz=rates,
        sigma_trace=sigmas,
        coherence_trace=coherence,
    )
    report_b = _build_phase_space_report(
        seed=7,
        n_neurons=4,
        dt_ms=1.0,
        duration_ms=4.0,
        steps=4,
        rate_trace_hz=rates,
        sigma_trace=sigmas,
        coherence_trace=coherence,
    )

    assert report_a == report_b
    assert report_a["point_count"] == 4


def test_phase_space_report_schema_and_manifest(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)

    phase_path = out_dir / "phase_space_report.json"
    manifest_path = out_dir / "run_manifest.json"
    assert phase_path.exists()

    report = json.loads(phase_path.read_text(encoding="utf-8"))
    schema = json.loads(Path("schemas/phase-space-report.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)

    assert report["state_axes"] == ["population_rate_hz", "sigma", "coherence"]
    assert 0.0 <= report["coherence_min"] <= report["coherence_max"] <= 1.0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact_name in [
        "phase_space_report.json",
        "population_rate_trace.npy",
        "sigma_trace.npy",
        "coherence_trace.npy",
        "phase_space_rate_sigma.png",
        "phase_space_rate_coherence.png",
        "phase_space_activity_map.png",
    ]:
        assert artifact_name in manifest["artifacts"]


def test_phase_space_report_deterministic_repeated_runs(tmp_path: Path) -> None:
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_a)
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_b)

    for filename in [
        "phase_space_report.json",
        "population_rate_trace.npy",
        "sigma_trace.npy",
        "coherence_trace.npy",
        "phase_space_rate_sigma.png",
        "phase_space_rate_coherence.png",
        "phase_space_activity_map.png",
    ]:
        assert (out_a / filename).read_bytes() == (out_b / filename).read_bytes()


def test_phase_space_fail_closed_on_steps_mismatch() -> None:
    rates = np.asarray([0.0, 1.0, 2.0], dtype=np.float64)
    sigmas = np.asarray([1.0, 1.1, 1.2], dtype=np.float64)
    coherence = np.asarray([0.2, 0.4, 0.6], dtype=np.float64)
    try:
        _build_phase_space_report(
            seed=1,
            n_neurons=2,
            dt_ms=0.5,
            duration_ms=1.5,
            steps=4,
            rate_trace_hz=rates,
            sigma_trace=sigmas,
            coherence_trace=coherence,
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError for steps mismatch")


def test_phase_space_fail_closed_on_trace_length_mismatch() -> None:
    rates = np.asarray([0.0, 1.0, 2.0], dtype=np.float64)
    sigmas = np.asarray([1.0, 1.1], dtype=np.float64)
    coherence = np.asarray([0.1, 0.2, 0.3], dtype=np.float64)
    try:
        _build_phase_space_report(
            seed=1,
            n_neurons=2,
            dt_ms=0.5,
            duration_ms=1.0,
            steps=3,
            rate_trace_hz=rates,
            sigma_trace=sigmas,
            coherence_trace=coherence,
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError for trace length mismatch")


def test_phase_space_zero_and_constant_traces_cover_edge_branches() -> None:
    rates = np.asarray([5.0, 5.0, 5.0], dtype=np.float64)
    sigmas = np.asarray([1.2, 1.2, 1.2], dtype=np.float64)
    coherence = np.asarray([0.4, 0.4, 0.4], dtype=np.float64)
    report = _build_phase_space_report(
        seed=9,
        n_neurons=3,
        dt_ms=1.0,
        duration_ms=3.0,
        steps=3,
        rate_trace_hz=rates,
        sigma_trace=sigmas,
        coherence_trace=coherence,
    )
    assert report["rate_sigma_correlation"] == 0.0
    assert report["rate_coherence_correlation"] == 0.0
    assert report["trajectory_length_l2"] == 0.0
    assert report["activity_map"]["occupied_cell_fraction"] == 1.0 / (64.0 * 64.0)


def test_phase_space_empty_trace_edge_branch() -> None:
    rates = np.asarray([], dtype=np.float64)
    sigmas = np.asarray([], dtype=np.float64)
    coherence = np.asarray([], dtype=np.float64)
    report = _build_phase_space_report(
        seed=11,
        n_neurons=1,
        dt_ms=1.0,
        duration_ms=0.0,
        steps=0,
        rate_trace_hz=rates,
        sigma_trace=sigmas,
        coherence_trace=coherence,
    )
    assert report["point_count"] == 0
    assert report["trajectory_length_l2"] == 0.0
    assert report["activity_map"]["occupied_cell_fraction"] == 0.0


def test_coherence_trace_is_not_trivial_rate_rescaling(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical"
    run_canonical_live_bundle("configs/canonical_profile.yaml", artifact_dir=out_dir)

    rates = np.load(out_dir / "population_rate_trace.npy")
    coherence = np.load(out_dir / "coherence_trace.npy")
    rate_max = float(np.max(rates)) if rates.size else 0.0
    if rate_max > 0.0:
        rate_rescaled = rates / rate_max
        assert not np.allclose(coherence, rate_rescaled, atol=1e-12, rtol=1e-12)
    assert np.any(np.diff(coherence) != 0.0)
