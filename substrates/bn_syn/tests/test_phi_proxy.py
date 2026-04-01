"""Tests for the Phi-Proxy (Integrated Information) engine.

Validates Phi* computation on synthetic spike trains with known properties.
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.emergence.phi_proxy import PhiProxyEngine, PhiProxyParams


def _feed_independent_poisson(
    engine: PhiProxyEngine,
    N: int,
    n_steps: int,
    rate: float,
    rng: np.random.Generator,
) -> None:
    """Feed independent Poisson spike trains into the engine."""
    for step in range(n_steps):
        spiked = rng.random(N) < rate
        engine.observe(spiked, step)


def _feed_coupled_network(
    engine: PhiProxyEngine,
    N: int,
    n_steps: int,
    rng: np.random.Generator,
) -> None:
    """Feed spike trains from a densely coupled linear-nonlinear network.

    Uses a stable random coupling matrix so each neuron's firing probability
    depends on specific other neurons' recent activity, creating genuine
    integrated information that cannot be decomposed by bipartition.

    The coupling matrix has strong off-diagonal elements ensuring cross-neuron
    dependencies that persist through the spike generation nonlinearity.
    """
    # Dense coupling matrix with controlled spectral radius
    W = rng.normal(0, 1.0, (N, N))
    eigvals = np.linalg.eigvals(W)
    W = W / (np.max(np.abs(eigvals)) + 0.1) * 0.85  # spectral radius ~0.85

    # Latent continuous state driven by W
    latent = np.zeros(N)
    for step in range(n_steps):
        latent = W @ latent + rng.normal(0, 0.2, N)
        # Sigmoid to get firing probabilities, centered around 0.5
        prob = 1.0 / (1.0 + np.exp(-2.0 * latent))
        spiked = rng.random(N) < prob
        engine.observe(spiked, step)


@pytest.fixture()
def rng() -> np.random.Generator:
    return np.random.default_rng(42)


class TestPhiProxy:
    """Tests for PhiProxyEngine."""

    def test_phi_zero_for_independent_neurons(self, rng: np.random.Generator) -> None:
        """Independent Poisson processes should yield Phi* near zero."""
        N = 20
        params = PhiProxyParams(
            subnetwork_size=8,
            n_subsamples=5,
            time_lag=1,
            bin_ms=1.0,
            min_observations=100,
            regularization=1e-5,
        )
        engine = PhiProxyEngine(N, params, rng)
        _feed_independent_poisson(engine, N, n_steps=2000, rate=0.3, rng=rng)

        result = engine.compute()
        assert result is not None
        # Independent neurons: Phi* should be very small
        assert result.phi_mean < 0.1, (
            f"Expected near-zero Phi* for independent neurons, got {result.phi_mean}"
        )

    def test_phi_positive_for_coupled_network(self, rng: np.random.Generator) -> None:
        """Strongly coupled neurons should yield Phi* > 0."""
        N = 20
        params = PhiProxyParams(
            subnetwork_size=6,
            n_subsamples=5,
            time_lag=1,
            bin_ms=5.0,
            min_observations=100,
            regularization=1e-6,
        )
        engine = PhiProxyEngine(N, params, rng)
        _feed_coupled_network(engine, N, n_steps=5000, rng=rng)

        result = engine.compute()
        assert result is not None
        assert result.phi_mean > 0.0, (
            f"Expected positive Phi* for coupled network, got {result.phi_mean}"
        )

    def test_phi_above_shuffled(self, rng: np.random.Generator) -> None:
        """For a coupled network, phi_z_score should be positive."""
        N = 20
        params = PhiProxyParams(
            subnetwork_size=4,
            n_subsamples=8,
            time_lag=1,
            bin_ms=10.0,
            min_observations=100,
            regularization=1e-6,
        )
        engine = PhiProxyEngine(N, params, rng)
        _feed_coupled_network(engine, N, n_steps=10000, rng=rng)

        result = engine.compute()
        assert result is not None
        assert result.phi_z_score > 0.0, (
            f"Expected positive z-score for coupled network, got {result.phi_z_score}"
        )

    def test_phi_returns_none_insufficient_data(
        self, rng: np.random.Generator
    ) -> None:
        """With fewer than min_observations bins, compute() returns None."""
        N = 10
        params = PhiProxyParams(
            subnetwork_size=6,
            n_subsamples=3,
            time_lag=1,
            bin_ms=5.0,
            min_observations=200,
            regularization=1e-6,
        )
        engine = PhiProxyEngine(N, params, rng)

        # Feed only 50 steps; with bin_ms=5, that's 10 bins, far below 200
        for step in range(50):
            spiked = rng.random(N) < 0.3
            engine.observe(spiked, step)

        result = engine.compute()
        assert result is None

    def test_phi_partition_valid(self, rng: np.random.Generator) -> None:
        """best_partition should cover all neurons in subsample with no overlap."""
        N = 20
        sub_size = 6
        params = PhiProxyParams(
            subnetwork_size=sub_size,
            n_subsamples=3,
            time_lag=1,
            bin_ms=5.0,
            min_observations=100,
            regularization=1e-6,
        )
        engine = PhiProxyEngine(N, params, rng)
        _feed_coupled_network(engine, N, n_steps=5000, rng=rng)

        result = engine.compute()
        assert result is not None

        part_a, part_b = result.best_partition
        # Both parts should be non-empty
        assert len(part_a) > 0, "Partition A is empty"
        assert len(part_b) > 0, "Partition B is empty"

        # No overlap
        overlap = set(part_a) & set(part_b)
        assert len(overlap) == 0, f"Partition has overlapping neurons: {overlap}"

        # Union should have exactly subnetwork_size elements
        union = set(part_a) | set(part_b)
        assert len(union) == sub_size, (
            f"Partition union has {len(union)} neurons, expected {sub_size}"
        )

        # All indices should be valid neuron IDs
        for idx in union:
            assert 0 <= idx < N, f"Invalid neuron index {idx}"
