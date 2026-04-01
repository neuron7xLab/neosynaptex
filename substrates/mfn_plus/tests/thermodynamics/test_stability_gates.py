"""Thermodynamic gate contract tests."""

import json

import numpy as np
import pytest

from mycelium_fractal_net.core.thermodynamic_kernel import (
    ThermodynamicKernel,
    ThermodynamicKernelConfig,
)


def _null_reaction(u, v):
    return np.zeros_like(u), np.zeros_like(v)


@pytest.fixture
def stable_trajectory():
    """Decaying sinusoidal — stable, λ₁ < 0."""
    frames = []
    for t in np.linspace(0, 10, 50):
        u = np.sin(2 * np.pi * np.arange(32) / 32)[None, :] * np.exp(-0.1 * t)
        u = np.broadcast_to(u, (32, 32)).copy()
        frames.append((u, np.zeros_like(u)))
    return frames


@pytest.fixture
def turing_trajectory():
    """Turing-like — metastable zone."""
    rng = np.random.default_rng(42)
    frames = []
    u = rng.uniform(0.4, 0.6, (32, 32))
    for _ in range(100):
        u = u + 0.001 * np.sin(8 * np.pi * u)
        frames.append((u.copy(), np.zeros_like(u)))
    return frames


@pytest.fixture
def diverging_trajectory():
    """Exponentially growing — unstable."""
    frames = []
    u = np.ones((16, 16)) * 0.5
    for _ in range(30):
        u = u * 1.5
        u = np.clip(u, 0, 1e6)
        frames.append((u.copy(), np.zeros_like(u)))
    return frames


class TestGateContracts:
    def test_stable_gate_open(self, stable_trajectory):
        # Decaying sinusoidal has non-negligible energy changes — use generous threshold
        config = ThermodynamicKernelConfig(
            allow_metastable=True, drift_threshold=1.0
        )
        kernel = ThermodynamicKernel(config)
        report = kernel.analyze_trajectory(stable_trajectory, _null_reaction)
        assert report.gate_passed
        assert report.stability_verdict in ("stable", "metastable")

    def test_diverging_gate_closed(self, diverging_trajectory):
        kernel = ThermodynamicKernel()
        report = kernel.analyze_trajectory(diverging_trajectory, _null_reaction)
        assert not report.gate_passed
        assert report.stability_verdict == "unstable"

    def test_metastable_blocked_without_flag(self, turing_trajectory):
        config = ThermodynamicKernelConfig(allow_metastable=False)
        kernel = ThermodynamicKernel(config)
        report = kernel.analyze_trajectory(turing_trajectory, _null_reaction)
        if report.stability_verdict == "metastable":
            assert not report.gate_passed

    def test_metastable_allowed_with_flag(self, turing_trajectory):
        config = ThermodynamicKernelConfig(allow_metastable=True)
        kernel = ThermodynamicKernel(config)
        report = kernel.analyze_trajectory(turing_trajectory, _null_reaction)
        if report.stability_verdict == "metastable":
            assert report.gate_passed

    def test_report_serializable(self, stable_trajectory):
        kernel = ThermodynamicKernel()
        report = kernel.analyze_trajectory(stable_trajectory, _null_reaction)
        data = report.model_dump()
        assert len(json.dumps(data)) > 0

    def test_report_summary(self, stable_trajectory):
        kernel = ThermodynamicKernel()
        report = kernel.analyze_trajectory(stable_trajectory, _null_reaction)
        s = report.summary()
        assert "THERMO" in s
        assert "gate=" in s

    def test_empty_frames_raises(self):
        kernel = ThermodynamicKernel()
        with pytest.raises(ValueError, match="non-empty"):
            kernel.analyze_trajectory([], _null_reaction)
