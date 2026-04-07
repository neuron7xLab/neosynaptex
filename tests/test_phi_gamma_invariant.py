"""Tests for H_φγ invariant analysis."""

from __future__ import annotations

import numpy as np
import pytest

from analysis.phi_gamma_invariant import (
    PHI,
    PHI_INV,
    bootstrap_ratio_ci,
    build_core_periphery,
    compute_energy_ratio,
    compute_gamma_windows,
    compute_predictive_ratio,
    compute_spectral_energy_ratio,
    evaluate_phi_gamma,
    run_phi_gamma_experiment,
    select_unity_windows,
)
from analysis.phi_gamma_nulls import (
    null_phase_randomization,
    null_temporal_shuffle,
    null_topology_shuffle,
)
from analysis.phi_gamma_report import build_report, build_substrate_entry

# ── Constants ────────────────────────────────────────────────────────────────


def test_phi_constants_precise():
    """PHI and PHI_INV match canonical values and satisfy φ · φ⁻¹ = 1."""
    assert abs(PHI - 1.6180339887498949) < 1e-12
    assert abs(PHI_INV - 0.6180339887498949) < 1e-12
    assert abs(PHI * PHI_INV - 1.0) < 1e-10


# ── Energy Ratio ─────────────────────────────────────────────────────────────


def test_attention_ratio_finite():
    """R(t) should be finite and positive for a synthetic signal."""
    rng = np.random.default_rng(0)
    n_nodes, n_time = 10, 128
    data = rng.standard_normal((n_nodes, n_time))
    core_idx = np.array([0, 1, 2, 3])
    periph_idx = np.array([4, 5, 6, 7, 8, 9])
    ratio = compute_energy_ratio(data, core_idx, periph_idx)
    assert np.isfinite(ratio)
    assert ratio > 0


def test_no_division_by_zero():
    """Delta guard prevents division by zero when periphery energy is 0."""
    n_nodes, n_time = 5, 64
    data = np.zeros((n_nodes, n_time))
    # Only core has energy
    data[0, :] = 1.0
    data[1, :] = 2.0
    core_idx = np.array([0, 1])
    periph_idx = np.array([2, 3, 4])
    ratio = compute_energy_ratio(data, core_idx, periph_idx, delta=1e-12)
    assert np.isfinite(ratio)
    assert ratio > 0


def test_energy_ratio_all_zeros():
    """Both core and periphery zero → finite ratio (= 0 / delta)."""
    data = np.zeros((4, 32))
    core_idx = np.array([0, 1])
    periph_idx = np.array([2, 3])
    ratio = compute_energy_ratio(data, core_idx, periph_idx)
    assert np.isfinite(ratio)
    assert ratio == 0.0


# ── Unity Window Selection ───────────────────────────────────────────────────


def test_unity_window_selector():
    """Mask should select only windows where |γ − 1| < ε."""
    gamma = np.array([0.5, 0.9, 0.95, 1.0, 1.05, 1.1, 1.5, 2.0])
    mask = select_unity_windows(gamma, epsilon=0.10)
    # |0.9 - 1| = 0.1, strict < means False; |0.95 - 1| = 0.05 < 0.10 → True
    expected = np.array([False, True, True, True, True, False, False, False])
    np.testing.assert_array_equal(mask, expected)


def test_unity_window_all_unity():
    """All windows near unity should be selected."""
    gamma = np.ones(50) + np.random.default_rng(0).uniform(-0.05, 0.05, 50)
    mask = select_unity_windows(gamma, epsilon=0.10)
    assert mask.all()


def test_unity_window_none_unity():
    """No windows near unity should give an all-False mask."""
    gamma = np.array([0.0, 0.5, 2.0, 3.0])
    mask = select_unity_windows(gamma, epsilon=0.10)
    assert not mask.any()


# ── Null Models ──────────────────────────────────────────────────────────────


def test_null_shuffle_changes_result():
    """Temporal shuffle should produce a different ratio distribution."""
    rng = np.random.default_rng(42)
    n_nodes, n_time = 10, 256
    data = rng.standard_normal((n_nodes, n_time))

    core_idx, periph_idx = build_core_periphery(data, core_fraction=0.382)
    orig_ratio = compute_energy_ratio(data, core_idx, periph_idx)

    shuffled = null_temporal_shuffle(data, rng=np.random.default_rng(99))
    core_s, periph_s = build_core_periphery(shuffled, core_fraction=0.382)
    shuf_ratio = compute_energy_ratio(shuffled, core_s, periph_s)

    # They should typically differ (probability of equality is negligible)
    assert orig_ratio != shuf_ratio


def test_null_topology_shuffle_preserves_sizes():
    """Topology shuffle must preserve core/periphery group sizes."""
    core_idx = np.array([0, 2, 5])
    periph_idx = np.array([1, 3, 4, 6, 7])
    n_nodes = 8
    new_core, new_periph = null_topology_shuffle(
        core_idx, periph_idx, n_nodes, rng=np.random.default_rng(0),
    )
    assert len(new_core) == len(core_idx)
    assert len(new_periph) == len(periph_idx)
    # All indices covered
    combined = np.sort(np.concatenate([new_core, new_periph]))
    np.testing.assert_array_equal(combined, np.arange(n_nodes))


def test_null_phase_randomization_preserves_power():
    """Phase randomization should preserve the power spectrum."""
    rng = np.random.default_rng(7)
    sig = rng.standard_normal(512)
    surrogate = null_phase_randomization(sig, rng=np.random.default_rng(8))

    orig_power = np.abs(np.fft.rfft(sig)) ** 2
    surr_power = np.abs(np.fft.rfft(surrogate)) ** 2
    np.testing.assert_allclose(orig_power, surr_power, rtol=1e-6)


def test_null_phase_randomization_2d():
    """Phase randomization on 2-D input should preserve power per channel."""
    rng = np.random.default_rng(3)
    sig = rng.standard_normal((4, 256))
    surrogate = null_phase_randomization(sig, rng=np.random.default_rng(4))
    assert surrogate.shape == sig.shape
    for ch in range(sig.shape[0]):
        orig_p = np.abs(np.fft.rfft(sig[ch])) ** 2
        surr_p = np.abs(np.fft.rfft(surrogate[ch])) ** 2
        np.testing.assert_allclose(orig_p, surr_p, rtol=1e-6)


# ── Bootstrap CI ─────────────────────────────────────────────────────────────


def test_bootstrap_ci_ordered():
    """Bootstrap CI lower bound must be ≤ upper bound."""
    rng = np.random.default_rng(1)
    ratios = rng.standard_normal(100) + 1.5
    lo, hi = bootstrap_ratio_ci(ratios, n_boot=500, seed=1)
    assert lo <= hi


def test_bootstrap_ci_contains_median():
    """95% CI should contain the sample median for well-behaved data."""
    rng = np.random.default_rng(2)
    ratios = rng.normal(1.6, 0.1, size=200)
    lo, hi = bootstrap_ratio_ci(ratios, n_boot=2000, seed=2)
    med = np.median(ratios)
    assert lo <= med <= hi


def test_bootstrap_ci_empty():
    """Empty input should return (nan, nan)."""
    lo, hi = bootstrap_ratio_ci(np.array([]))
    assert np.isnan(lo) and np.isnan(hi)


# ── Verdict Logic ────────────────────────────────────────────────────────────


def test_verdict_returns_all_three_states():
    """Construct explicit cases for support, reject, insufficient."""
    rng = np.random.default_rng(10)

    # --- insufficient: too few windows ---
    ratios_few = rng.normal(PHI, 0.05, size=5)
    null_few = rng.normal(1.0, 0.3, size=100)
    result_insuf = evaluate_phi_gamma(ratios_few, null_few, min_windows=30)
    assert result_insuf["verdict"] == "insufficient"

    # --- support: median near φ, significantly different from null ---
    ratios_phi = np.full(50, PHI) + rng.normal(0, 0.01, size=50)
    null_far = rng.normal(1.0, 0.05, size=500)
    result_support = evaluate_phi_gamma(
        ratios_phi, null_far, min_windows=30, p_threshold=0.05,
    )
    assert result_support["verdict"] == "support"

    # --- reject: median far from φ and φ_inv, null not rejected ---
    ratios_far = np.full(50, 3.0) + rng.normal(0, 0.01, size=50)
    null_also_far = rng.normal(3.0, 0.05, size=500)
    result_reject = evaluate_phi_gamma(
        ratios_far, null_also_far, min_windows=30, p_threshold=0.05,
    )
    assert result_reject["verdict"] == "reject"


def test_verdict_support_phi_inv():
    """Support verdict should also work when median is near φ⁻¹."""
    rng = np.random.default_rng(11)
    ratios = np.full(50, PHI_INV) + rng.normal(0, 0.01, size=50)
    null_far = rng.normal(1.0, 0.05, size=500)
    result = evaluate_phi_gamma(ratios, null_far, min_windows=30)
    assert result["verdict"] == "support"


# ── Core/Periphery ───────────────────────────────────────────────────────────


def test_build_core_periphery_sizes():
    """Core/periphery partition should have correct sizes."""
    rng = np.random.default_rng(5)
    data = rng.standard_normal((20, 128))
    core, periph = build_core_periphery(data, core_fraction=0.382)
    assert len(core) == int(np.ceil(20 * 0.382))
    assert len(core) + len(periph) == 20


def test_build_core_periphery_no_overlap():
    """Core and periphery should not overlap."""
    rng = np.random.default_rng(6)
    data = rng.standard_normal((15, 64))
    core, periph = build_core_periphery(data, core_fraction=0.382)
    assert len(np.intersect1d(core, periph)) == 0
    combined = np.sort(np.concatenate([core, periph]))
    np.testing.assert_array_equal(combined, np.arange(15))


# ── Gamma Windows ────────────────────────────────────────────────────────────


def test_gamma_windows_shape():
    """Number of gamma windows matches expected count from signal length."""
    n = 2048
    window, step = 256, 32
    sig = np.random.default_rng(0).standard_normal(n)
    gammas = compute_gamma_windows(sig, window=window, step=step)
    expected_n = len(range(0, n - window + 1, step))
    assert len(gammas) == expected_n


def test_gamma_windows_all_finite():
    """All gamma values should be finite for a normal random signal."""
    sig = np.random.default_rng(1).standard_normal(1024)
    gammas = compute_gamma_windows(sig, window=256, step=64)
    assert np.all(np.isfinite(gammas))


# ── R2 / R3 ─────────────────────────────────────────────────────────────────


def test_spectral_energy_ratio_finite():
    """R2 should return a finite positive ratio."""
    rng = np.random.default_rng(12)
    data = rng.standard_normal((8, 128))
    ratio = compute_spectral_energy_ratio(data, core_fraction=0.382)
    assert np.isfinite(ratio)
    assert ratio > 0


def test_predictive_ratio_finite():
    """R3 should return a finite positive ratio."""
    rng = np.random.default_rng(13)
    data = rng.standard_normal((8, 128))
    ratio = compute_predictive_ratio(data, core_fraction=0.382)
    assert np.isfinite(ratio)
    assert ratio > 0


# ── Report Schema ────────────────────────────────────────────────────────────


def test_report_schema():
    """JSON report must contain all required keys."""
    entry = build_substrate_entry(
        name="test", ratio_method="R1", n_windows=100, n_unity_windows=40,
        median_ratio=1.6, mean_ratio=1.61, bootstrap_ci=(1.5, 1.7),
        null_median=1.0, p_value=0.01, verdict="support",
    )
    required_keys = {
        "name", "ratio_method", "n_windows", "n_unity_windows",
        "median_ratio", "mean_ratio", "bootstrap_ci",
        "distance_to_phi", "distance_to_phi_inv",
        "null_median", "p_value", "verdict",
    }
    assert required_keys.issubset(entry.keys())

    report = build_report([entry])
    assert "hypothesis" in report
    assert report["hypothesis"] == "H_phi_gamma"
    assert "substrates" in report
    assert "cross_substrate" in report
    cs = report["cross_substrate"]
    assert "n_support" in cs
    assert "n_reject" in cs
    assert "n_insufficient" in cs
    assert "pooled_median_ratio" in cs
    assert "pooled_ci" in cs
    assert "closest_target" in cs


# ── Full Pipeline ────────────────────────────────────────────────────────────


@pytest.mark.slow
def test_full_pipeline_runs():
    """Full pipeline should run without error and produce a valid report."""
    config = {
        "phi": PHI,
        "phi_inv": PHI_INV,
        "epsilon": 0.10,
        "window": 256,
        "step": 64,
        "core_fraction": 0.382,
        "delta": 1e-12,
        "min_unity_windows": 5,  # low threshold for demo data
        "n_bootstrap": 200,
        "p_value_threshold": 0.05,
    }
    report = run_phi_gamma_experiment(config)
    assert report["hypothesis"] == "H_phi_gamma"
    assert len(report["substrates"]) > 0
    for sub in report["substrates"]:
        assert sub["verdict"] in ("support", "reject", "insufficient")
        assert np.isfinite(sub["median_ratio"])
        assert np.isfinite(sub["p_value"])
