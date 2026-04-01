"""Tests for cell assembly detection (PCA + Marchenko-Pastur)."""

import numpy as np

from bnsyn.assembly.detector import AssemblyDetector


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _feed_random_spikes(det: AssemblyDetector, N: int, n_steps: int, rate: float = 0.1, seed: int = 42) -> None:
    """Feed independent random spikes into the detector."""
    rng = np.random.default_rng(seed)
    for step in range(n_steps):
        spiked = rng.random(N) < rate
        det.observe(spiked, step)


def _feed_correlated_groups(det: AssemblyDetector, N: int, n_steps: int, seed: int = 0) -> None:
    """Feed spikes with two correlated groups into the detector.

    Group A (neurons 0-9): fire together with p=0.8
    Group B (neurons 10-19): fire together with p=0.8
    Remaining neurons: independent at p=0.05
    """
    rng = np.random.default_rng(seed)
    for step in range(n_steps):
        spiked = np.zeros(N, dtype=bool)
        # Group A
        if rng.random() < 0.3:
            spiked[:10] = rng.random(10) < 0.8
        # Group B
        if rng.random() < 0.3:
            spiked[10:20] = rng.random(10) < 0.8
        # Background
        spiked[20:] = rng.random(N - 20) < 0.05
        det.observe(spiked, step)


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

class TestAssemblyDetector:
    def test_detect_no_assemblies_random(self) -> None:
        """Random independent spikes should produce 0 significant assemblies."""
        N = 50
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=200)
        _feed_random_spikes(det, N, n_steps=2000, rate=0.05, seed=99)
        result = det.detect()
        # With truly independent Poisson-like spikes, eigenvalues should
        # not exceed the MP threshold (or at most very few).
        assert result.n_significant <= 1, (
            f"Expected <=1 significant assembly from random spikes, got {result.n_significant}"
        )

    def test_detect_assemblies_correlated(self) -> None:
        """Correlated neuron groups should yield at least 1 detected assembly."""
        N = 50
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=300)
        _feed_correlated_groups(det, N, n_steps=3000, seed=7)
        result = det.detect()
        assert result.n_significant >= 1, (
            "Expected at least 1 assembly from correlated groups"
        )
        # Check that assemblies have non-empty weights
        for a in result.assemblies:
            assert a.weights.shape == (N,)
            assert a.eigenvalue > result.marchenko_pastur_threshold

    def test_mp_threshold_positive(self) -> None:
        """Marchenko-Pastur threshold should always be positive."""
        N = 30
        det = AssemblyDetector(N, bin_ms=5.0, buffer_bins=100)
        _feed_random_spikes(det, N, n_steps=500, rate=0.1)
        result = det.detect()
        assert result.marchenko_pastur_threshold > 0

    def test_core_neurons_subset(self) -> None:
        """Core neurons should be a subset of [0, N)."""
        N = 50
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=300)
        _feed_correlated_groups(det, N, n_steps=3000, seed=12)
        result = det.detect()
        for a in result.assemblies:
            for neuron_idx in a.core_neurons:
                assert 0 <= neuron_idx < N

    def test_activation_traces_shape(self) -> None:
        """Activation traces should have length equal to the number of bins used."""
        N = 40
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=200)
        _feed_correlated_groups(det, N, n_steps=2000, seed=3)
        result = det.detect()
        # Number of bins = n_steps / bin_ms = 2000 / 10 = 200
        expected_bins = 200
        for idx, trace in result.activation_traces.items():
            assert len(trace) == expected_bins, (
                f"Assembly {idx}: expected trace length {expected_bins}, got {len(trace)}"
            )
