"""Adversarial test battery for the estimator admissibility trial.

These tests are NOT a substitute for the trial itself — they probe
properties that must hold regardless of the actual numerical output:

* Synthetic generator preserves the slope (sanity).
* An "always 1.0" oracle estimator with a CI excluding 0 must FAIL
  the FPR axis on null cells (adversarial).
* An exact-γ_true oracle estimator must PASS at every N (adversarial).
* The canonical Theil–Sen at large N, σ=0 should pass A1+A2 (sanity).
* The verdict block has all six fields with exact spelling (schema).

Tests run in <60 s on a laptop. They use M=20–60 only; the
admissibility trial proper is gated by the CI workflow at M=100/1000.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tools.phase_3.admissibility import VERDICT_FIELDS
from tools.phase_3.admissibility.estimators import (
    ESTIMATOR_NAMES,
    ESTIMATOR_REGISTRY,
    EstimatorResult,
    canonical_theil_sen,
)
from tools.phase_3.admissibility.metrics import (
    cell_metrics,
    false_positive_rate_on_null,
)
from tools.phase_3.admissibility.run_admissibility_trial import main as cli_main
from tools.phase_3.admissibility.synthetic_data import synthesise, synthesise_null
from tools.phase_3.admissibility.trial import TrialConfig, run_trial
from tools.phase_3.admissibility.verdict import build_verdict, format_verdict_block

# ─── Synthetic data generator sanity ────────────────────────────────


@pytest.mark.parametrize("gamma_true", [0.5, 1.0, 1.5, 2.0])
def test_synthesise_preserves_slope_at_zero_noise(gamma_true: float) -> None:
    """At σ=0 the canonical Theil–Sen must recover γ_true exactly."""
    sample = synthesise(gamma_true=gamma_true, n=64, sigma=0.0, seed=0)
    log_c = np.log(sample.C)
    log_k = np.log(sample.K)
    res = canonical_theil_sen(log_c, log_k)
    assert np.isfinite(res.gamma)
    assert res.gamma == pytest.approx(gamma_true, abs=1e-9)


def test_synthesise_is_deterministic_given_seed() -> None:
    """Two synthesise calls with same args yield byte-identical (C, K)."""
    a = synthesise(gamma_true=1.0, n=128, sigma=0.1, seed=42)
    b = synthesise(gamma_true=1.0, n=128, sigma=0.1, seed=42)
    np.testing.assert_array_equal(a.C, b.C)
    np.testing.assert_array_equal(a.K, b.K)


def test_synthesise_null_independent_of_c() -> None:
    """K under null mode has no slope dependence on C."""
    sample = synthesise_null(n=128, sigma=0.1, seed=7)
    # By construction K_i = a · exp(σ ε_i) — no log_c term.
    rng = np.random.default_rng(7)
    expected_eps = rng.standard_normal(128)
    expected_k = np.exp(0.1 * expected_eps)
    np.testing.assert_array_almost_equal(sample.K, expected_k)


# ─── Estimator-API contract ─────────────────────────────────────────


def test_all_five_estimators_registered() -> None:
    """Registry must carry exactly the 5 spec'd estimators in order."""
    assert ESTIMATOR_NAMES == (
        "canonical_theil_sen",
        "subwindow_bagged_theil_sen",
        "quantile_pivoted_slope",
        "bootstrap_median_slope",
        "odr_log_log",
    )
    for name in ESTIMATOR_NAMES:
        assert name in ESTIMATOR_REGISTRY


def test_canonical_theil_sen_at_n1024_sigma0_passes_sanity() -> None:
    """Canonical Theil–Sen at large N, no noise, must score:
    |bias| ≤ 1e-9, CI coverage = 1.0 (CI degenerate to point at σ=0 → contains γ).
    """
    estimates: list[EstimatorResult] = []
    for k in range(20):
        sample = synthesise(gamma_true=1.0, n=1024, sigma=0.0, seed=k)
        res = canonical_theil_sen(np.log(sample.C), np.log(sample.K))
        estimates.append(res)
    biases = [e.gamma - 1.0 for e in estimates]
    assert all(abs(b) < 1e-9 for b in biases)


def test_canonical_theil_sen_recovers_true_gamma_with_noise() -> None:
    """At σ=0.1, N=512: median |γ̂ − γ_true| should be small (<0.05)."""
    samples = [synthesise(gamma_true=1.0, n=512, sigma=0.1, seed=k) for k in range(50)]
    gammas = [canonical_theil_sen(np.log(s.C), np.log(s.K)).gamma for s in samples]
    median_abs = float(np.median([abs(g - 1.0) for g in gammas]))
    assert median_abs < 0.05


# ─── Adversarial oracle estimators ──────────────────────────────────


def _always_one_estimator(log_c: np.ndarray, log_k: np.ndarray) -> EstimatorResult:
    """Adversarial: always returns γ̂=1.0 with a tight CI excluding 0.

    Such an estimator passes A1 only at γ_true=1.0 and is a guaranteed
    false-positive on every null cell — so it MUST FAIL FPR on H0.
    """
    return EstimatorResult(gamma=1.0, ci95_low=0.5, ci95_high=1.5)


def _oracle_estimator_factory(
    gamma_true: float,
) -> Callable[[np.ndarray, np.ndarray], EstimatorResult]:
    """Adversarial: returns γ_true exactly + tight CI containing γ_true.

    The trial cell-by-cell needs different oracles for different γ_true,
    so we build per-cell oracles in the test below.
    """

    def fn(log_c: np.ndarray, log_k: np.ndarray) -> EstimatorResult:
        return EstimatorResult(
            gamma=gamma_true,
            ci95_low=gamma_true - 0.001,
            ci95_high=gamma_true + 0.001,
        )

    return fn


def test_always_one_estimator_fails_fpr_on_null() -> None:
    """At γ_true=0 (null cells) the always-1.0 estimator's CI excludes 0
    on every replicate, so FPR == 1.0 ≫ 0.05.
    """
    estimates = [_always_one_estimator(np.zeros(10), np.zeros(10)) for _ in range(50)]
    fpr = false_positive_rate_on_null(estimates)
    assert fpr == pytest.approx(1.0)


def test_oracle_estimator_passes_a1_a2_a3_at_n_min() -> None:
    """An oracle that returns γ_true exactly with a tight CI must satisfy
    every per-cell metric: |bias|=0, coverage=1.0, window_delta_max=0.
    """
    gamma_true = 1.0
    fit = _oracle_estimator_factory(gamma_true)
    estimates = []
    log_c_reps = []
    log_k_reps = []
    for k in range(20):
        sample = synthesise(gamma_true=gamma_true, n=128, sigma=0.1, seed=k)
        log_c_reps.append(np.log(sample.C))
        log_k_reps.append(np.log(sample.K))
        estimates.append(fit(log_c_reps[-1], log_k_reps[-1]))
    metrics = cell_metrics(
        gamma_true=gamma_true,
        estimates=estimates,
        log_c_replicates=log_c_reps,
        log_k_replicates=log_k_reps,
        fit_fn=fit,
        n_replicates_for_window_metrics=10,
    )
    assert metrics.bias == pytest.approx(0.0, abs=1e-12)
    assert metrics.ci95_coverage == pytest.approx(1.0)
    assert metrics.window_delta_max == pytest.approx(0.0, abs=1e-12)


# ─── Verdict-schema contract ────────────────────────────────────────


def test_verdict_block_has_all_six_fields_exact_spelling() -> None:
    """The verdict block must contain all six fields with exact strings."""
    # Construct a minimal mock results dict whose canonical estimator
    # passes everywhere — exercises the "ADMISSIBLE_AT_N_MIN" branch.
    config = TrialConfig(
        gamma_grid=(1.0,),
        n_grid=(64,),
        sigma_grid=(0.1,),
        estimator_names=("canonical_theil_sen",),
        m_replicates=20,
        seed_base=123,
        n_replicates_for_window_metrics=5,
    )
    results = run_trial(config)
    verdict = build_verdict(results)
    block = format_verdict_block(verdict)
    for field in VERDICT_FIELDS:
        assert field in block, f"missing field: {field!r}"
        assert f"{field}:" in block


def test_build_verdict_branch_when_canonical_fails_no_replacement() -> None:
    """When canonical fails A1 (bias > 0.05) and no alternative passes,
    the verdict must be FINAL_VERDICT=BLOCKED_BY_MEASUREMENT_OPERATOR.
    """
    # Synthetic results with all estimators biased: none can pass.
    fake_cells: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for est in ESTIMATOR_NAMES:
        fake_cells[est] = {}
        for g in [1.0]:
            from tools.phase_3.admissibility.trial import _fmt_float

            g_key = _fmt_float(g)
            fake_cells[est][g_key] = {}
            for n in [64, 128, 256, 512, 1024]:
                fake_cells[est][g_key][str(n)] = {}
                for s in [0.1]:
                    s_key = _fmt_float(s)
                    fake_cells[est][g_key][str(n)][s_key] = {
                        "bias": 0.5,  # FAIL A1
                        "variance": 0.01,
                        "rmse": 0.5,
                        "ci95_coverage": 0.30,  # FAIL A2
                        "window_delta_max": 0.5,  # FAIL A3
                        "leave_one_window_out_drift": 0.1,
                        "bootstrap_slope_dispersion": 0.05,
                        "false_positive_rate_on_null": 0.5,  # FAIL A4
                        "n_replicates_used": 50,
                        "nan_fraction": 0.0,
                    }
    fake_results = {
        "config": {
            "gamma_grid": [1.0],
            "n_grid": [64, 128, 256, 512, 1024],
            "sigma_grid": [0.1],
            "estimator_names": list(ESTIMATOR_NAMES),
            "m_replicates": 50,
            "seed_base": 0,
            "n_replicates_for_window_metrics": 5,
        },
        "cells": fake_cells,
    }
    verdict = build_verdict(fake_results)
    assert verdict["ESTIMATOR_ADMISSIBILITY"] == "FAILED"
    assert verdict["MINIMUM_TRAJECTORY_LENGTH"] == "INF"
    assert verdict["CANONICAL_ESTIMATOR"] == "rejected"
    assert verdict["REPLACEMENT_ESTIMATOR"] == "NONE"
    assert verdict["HYPOTHESIS_TEST_STATUS"] == "BLOCKED"
    assert verdict["FINAL_VERDICT"] == "BLOCKED_BY_MEASUREMENT_OPERATOR"


# ─── CLI smoke ──────────────────────────────────────────────────────


def test_cli_smoke_minimal_grid_writes_valid_json(tmp_path: Path) -> None:
    """End-to-end: run the CLI on a tiny grid, verify JSON has verdict + hash.

    Uses a 1-estimator × 1-γ × 2-N × 1-σ × M=10 grid to keep runtime
    well under a second.
    """
    out = tmp_path / "smoke.json"
    rc = cli_main(
        [
            "--M",
            "10",
            "--smoke",
            "--out",
            str(out),
            "--estimators",
            "canonical_theil_sen",
            "--gamma-grid",
            "1.0",
            "--n-grid",
            "64,128",
            "--noise-sigma",
            "0.1",
            "--n-window-replicates",
            "3",
        ]
    )
    assert rc == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "result_hash" in payload
    assert "verdict_block" in payload
    block = payload["verdict_block"]
    for field in VERDICT_FIELDS:
        assert field in block


def test_cli_smoke_reproducible_hash(tmp_path: Path) -> None:
    """Same args → same result_hash. Two consecutive runs must agree."""
    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"
    args = [
        "--M",
        "10",
        "--smoke",
        "--estimators",
        "canonical_theil_sen",
        "--gamma-grid",
        "1.0",
        "--n-grid",
        "64",
        "--noise-sigma",
        "0.1",
        "--n-window-replicates",
        "3",
    ]
    assert cli_main([*args, "--out", str(out_a)]) == 0
    assert cli_main([*args, "--out", str(out_b)]) == 0
    pa = json.loads(out_a.read_text(encoding="utf-8"))
    pb = json.loads(out_b.read_text(encoding="utf-8"))
    assert pa["result_hash"] == pb["result_hash"]
