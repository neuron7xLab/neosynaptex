from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.compare_canonical_runs import CompareRunsError, compare_runs, render_markdown


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_bundle(root: Path, *, sigma: list[float], coherence: list[float], seed: int, verdict: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "summary_metrics.json", {"seed": seed})
    _write_json(root / "proof_report.json", {"verdict": verdict})
    np.save(root / "sigma_trace.npy", np.asarray(sigma, dtype=np.float64))
    np.save(root / "coherence_trace.npy", np.asarray(coherence, dtype=np.float64))


def test_compare_runs_reports_trace_deltas(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    current = tmp_path / "current"
    _write_bundle(baseline, sigma=[1.0, 1.0], coherence=[0.2, 0.3], seed=1, verdict="PASS")
    _write_bundle(current, sigma=[1.1, 0.9], coherence=[0.25, 0.4], seed=2, verdict="PASS")

    payload = compare_runs(baseline, current)

    assert payload["status"] == "PASS"
    assert payload["baseline_verdict"] == "PASS"
    assert payload["current_verdict"] == "PASS"
    assert payload["drift_assessment"]["level"] == "LOW"
    assert payload["sigma_trace"]["samples"] == 2
    assert payload["coherence_trace"]["max_abs_delta"] > 0.0
    assert "Cross-Commit Canonical Analytics" in render_markdown(payload)
    assert "Drift assessment" in render_markdown(payload)
    assert "status: **PASS**" in render_markdown(payload)


def test_compare_runs_flags_elevated_drift(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    current = tmp_path / "current"
    _write_bundle(baseline, sigma=[1.0, 1.0], coherence=[0.2, 0.2], seed=1, verdict="PASS")
    _write_bundle(current, sigma=[1.4, 1.4], coherence=[0.5, 0.5], seed=2, verdict="PASS")

    payload = compare_runs(baseline, current)

    assert payload["drift_assessment"]["level"] == "ELEVATED"
    assert "sigma_mean_delta" in payload["drift_assessment"]["flags"]


def test_compare_runs_fails_closed_on_trace_shape_mismatch(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    current = tmp_path / "current"
    _write_bundle(baseline, sigma=[1.0, 1.0], coherence=[0.2, 0.3], seed=1, verdict="PASS")
    _write_bundle(current, sigma=[1.1], coherence=[0.25, 0.4], seed=2, verdict="PASS")

    try:
        compare_runs(baseline, current)
    except CompareRunsError as exc:
        assert "trace shape mismatch for sigma_trace" in str(exc)
    else:
        raise AssertionError("expected CompareRunsError")
