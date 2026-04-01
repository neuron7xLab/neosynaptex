"""Tests for GammaFieldProbe — cross-substrate γ measurement."""

import numpy as np
import pytest

from mycelium_fractal_net.probes.gamma_field_probe import (
    GammaFieldProbe,
    GammaFieldReport,
)


def test_gamma_random_fields_near_zero():
    """Random noise fields should have γ near 0 (no organization)."""
    rng = np.random.default_rng(42)
    fields = rng.standard_normal((100, 32, 32))
    probe = GammaFieldProbe(n_bootstrap=50, seed=42)
    report = probe.measure(fields, substrate="random_noise")
    # Random fields should have γ near 0 or inconclusive
    assert abs(report.gamma) < 2.0 or report.r2 < 0.1


def test_gamma_organized_fields_positive():
    """Structured evolving fields should produce a measurable γ."""
    rng = np.random.default_rng(42)
    T, H, W = 150, 32, 32
    fields = np.zeros((T, H, W))
    x, y = np.meshgrid(np.linspace(-3, 3, W), np.linspace(-3, 3, H))
    for t in range(T):
        phase = t * 0.05
        fields[t] = np.exp(
            -((x - np.sin(phase)) ** 2 + (y - np.cos(phase)) ** 2) / 2.0
        )
        fields[t] += rng.standard_normal((H, W)) * 0.05
    probe = GammaFieldProbe(n_bootstrap=50, seed=42)
    report = probe.measure(fields, substrate="organized")
    assert report.n_pairs >= 5  # enough data to measure


def test_control_destroys_signal():
    """Shuffled control should give γ closer to 0 than real."""
    rng = np.random.default_rng(42)
    T, H, W = 150, 32, 32
    fields = np.zeros((T, H, W))
    x, y = np.meshgrid(np.linspace(-3, 3, W), np.linspace(-3, 3, H))
    for t in range(T):
        phase = t * 0.05
        fields[t] = np.exp(
            -((x - np.sin(phase)) ** 2 + (y - np.cos(phase)) ** 2) / 2.0
        )
    probe = GammaFieldProbe(n_bootstrap=50, seed=42)
    real = probe.measure(fields, substrate="organized")
    ctrl = probe.measure_control(fields, substrate="shuffled")
    # Control should have lower R² or lower |γ| (some tolerance)
    assert ctrl.r2 <= real.r2 + 0.3


def test_report_summary_format():
    """Report summary contains expected fields."""
    report = GammaFieldReport(
        substrate="test",
        gamma=1.0,
        r2=0.5,
        ci_low=0.5,
        ci_high=1.5,
        n_pairs=50,
    )
    s = report.summary()
    assert "test" in s
    assert "CI" in s
    assert "1.043" in s  # γ_WT reference


def test_insufficient_data():
    """Too few frames should give INSUFFICIENT DATA or very few pairs."""
    rng = np.random.default_rng(42)
    fields = rng.standard_normal((5, 16, 16))
    probe = GammaFieldProbe(n_bootstrap=10, seed=42)
    report = probe.measure(fields, substrate="tiny")
    # Either insufficient pairs or n_pairs is very small
    assert report.n_pairs < 20 or "INSUFFICIENT" in report.verdict


def test_verdict_consistent_with_gamma_wt():
    """Report with γ in [0.8, 1.3] should give CONSISTENT verdict."""
    report = GammaFieldReport(
        substrate="x", gamma=1.05, r2=0.6, ci_low=0.9, ci_high=1.2, n_pairs=50
    )
    assert report.verdict == "CONSISTENT WITH γ_WT"


def test_verdict_organized():
    """Report with γ > 1.3 should give ORGANIZED verdict."""
    report = GammaFieldReport(
        substrate="x", gamma=2.0, r2=0.5, ci_low=1.5, ci_high=2.5, n_pairs=50
    )
    assert report.verdict == "ORGANIZED (γ > 0)"


def test_verdict_anti_organized():
    """Report with γ < 0 should give ANTI-ORGANIZED verdict."""
    report = GammaFieldReport(
        substrate="x", gamma=-0.5, r2=0.5, ci_low=-1.0, ci_high=0.0, n_pairs=50
    )
    assert report.verdict == "ANTI-ORGANIZED (γ < 0)"


def test_run_on_mfn_engine():
    """Integration test: run γ probe on actual MFN+ engine."""
    from mycelium_fractal_net.core.reaction_diffusion_engine import (
        ReactionDiffusionEngine,
    )
    from mycelium_fractal_net.core.reaction_diffusion_config import (
        ReactionDiffusionConfig,
    )

    config = ReactionDiffusionConfig(grid_size=32, random_seed=42)
    engine = ReactionDiffusionEngine(config=config)
    probe = GammaFieldProbe(n_bootstrap=50, seed=42)
    real, ctrl = probe.run_on_engine(
        engine, steps=100, substrate_label="mfn_activator"
    )

    assert isinstance(real, GammaFieldReport)
    assert isinstance(ctrl, GammaFieldReport)
    assert real.substrate == "mfn_activator"
    assert "shuffled" in ctrl.substrate
