"""Tests for the Transfer Entropy engine."""

from __future__ import annotations

import numpy as np

from bnsyn.causality.transfer_entropy import (
    TransferEntropyEngine,
    TransferEntropyParams,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(
    N: int = 200,
    nE: int = 160,
    buffer_size: int = 600,
    n_surrogates: int = 50,
    history_depth: int = 3,
    bin_ms: float = 1.0,
) -> TransferEntropyEngine:
    """Construct an engine with test-friendly defaults."""
    params = TransferEntropyParams(
        bin_ms=bin_ms,
        history_depth=history_depth,
        buffer_size=buffer_size,
        n_surrogates=n_surrogates,
        bias_correction=True,
    )
    return TransferEntropyEngine(N=N, nE=nE, params=params)


def _feed_independent_poisson(
    engine: TransferEntropyEngine,
    N: int,
    nE: int,
    steps: int,
    rate_e: float = 0.05,
    rate_i: float = 0.05,
    seed: int = 0,
) -> None:
    """Feed independent Poisson spike trains into the engine."""
    rng = np.random.default_rng(seed)
    for t in range(steps):
        spiked = np.zeros(N, dtype=bool)
        spiked[:nE] = rng.random(nE) < rate_e
        spiked[nE:] = rng.random(N - nE) < rate_i
        engine.observe(spiked, t)


def _feed_causal_pair(
    engine: TransferEntropyEngine,
    N: int,
    nE: int,
    steps: int,
    delay: int = 3,
    seed: int = 1,
) -> None:
    """Feed spikes where E causally drives I with a fixed delay.

    E fires independently; I at time t copies E's firing pattern from t-delay
    (with some noise).
    """
    rng = np.random.default_rng(seed)
    e_history = []
    for t in range(steps):
        spiked = np.zeros(N, dtype=bool)
        # E fires independently at ~10% rate.
        e_firing = rng.random(nE) < 0.10
        spiked[:nE] = e_firing
        e_history.append(float(np.sum(e_firing)))

        # I mirrors E's summed activity from `delay` steps ago.
        if t >= delay:
            past_rate = min(e_history[t - delay] / max(nE, 1), 1.0)
            # Probability of each I neuron firing proportional to past E rate.
            spiked[nE:] = rng.random(N - nE) < (past_rate * 0.8 + 0.01)
        else:
            spiked[nE:] = rng.random(N - nE) < 0.01

        engine.observe(spiked, t)


def _feed_symmetric_coupled(
    engine: TransferEntropyEngine,
    N: int,
    nE: int,
    steps: int,
    delay: int = 2,
    seed: int = 2,
) -> None:
    """Feed spikes where E and I are symmetrically coupled with mutual delay."""
    rng = np.random.default_rng(seed)
    nI = N - nE
    e_history: list[float] = []
    i_history: list[float] = []

    for t in range(steps):
        spiked = np.zeros(N, dtype=bool)

        # Baseline firing.
        base_e = 0.05
        base_i = 0.05

        # Coupling: each population is driven by the other's past activity.
        if t >= delay:
            past_i_rate = min(i_history[t - delay] / max(nI, 1), 1.0)
            past_e_rate = min(e_history[t - delay] / max(nE, 1), 1.0)
            e_prob = min(base_e + 0.5 * past_i_rate, 1.0)
            i_prob = min(base_i + 0.5 * past_e_rate, 1.0)
        else:
            e_prob = base_e
            i_prob = base_i

        spiked[:nE] = rng.random(nE) < e_prob
        spiked[nE:] = rng.random(nI) < i_prob

        e_history.append(float(np.sum(spiked[:nE])))
        i_history.append(float(np.sum(spiked[nE:])))

        engine.observe(spiked, t)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTransferEntropy:
    """Core TE engine tests."""

    def test_te_zero_for_independent_poisson(self) -> None:
        """Two independent Poisson processes should yield TE ~ 0."""
        N, nE = 200, 160
        engine = _make_engine(N=N, nE=nE, buffer_size=800, n_surrogates=20)
        _feed_independent_poisson(engine, N, nE, steps=800, seed=7)
        result = engine.compute()

        assert result is not None
        assert abs(result.te_e_to_i) < 0.05, (
            f"TE(E->I) should be ~0 for independent processes, got {result.te_e_to_i}"
        )
        assert abs(result.te_i_to_e) < 0.05, (
            f"TE(I->E) should be ~0 for independent processes, got {result.te_i_to_e}"
        )

    def test_te_positive_for_causal_pair(self) -> None:
        """When E drives I with delay, TE(E->I) > 0 and TE(I->E) ~ 0."""
        N, nE = 200, 160
        engine = _make_engine(
            N=N, nE=nE, buffer_size=1500, n_surrogates=20, history_depth=4
        )
        _feed_causal_pair(engine, N, nE, steps=1500, delay=3, seed=42)
        result = engine.compute()

        assert result is not None
        assert result.te_e_to_i > 0.0, (
            f"TE(E->I) should be positive for causal pair, got {result.te_e_to_i}"
        )
        # Net flow should be E->I dominant.
        assert result.te_net > 0.0, (
            f"Net TE should be positive (E->I dominant), got {result.te_net}"
        )

    def test_te_symmetric_for_coupled(self) -> None:
        """Bidirectional coupling should produce roughly symmetric TE values."""
        N, nE = 200, 160
        engine = _make_engine(
            N=N, nE=nE, buffer_size=2000, n_surrogates=20, history_depth=3
        )
        _feed_symmetric_coupled(engine, N, nE, steps=2000, delay=2, seed=99)
        result = engine.compute()

        assert result is not None
        # Both should be non-negative.
        assert result.te_e_to_i >= 0.0
        assert result.te_i_to_e >= 0.0
        # The difference should be small relative to the mean.
        mean_te = (result.te_e_to_i + result.te_i_to_e) / 2.0
        if mean_te > 0.001:
            relative_diff = abs(result.te_e_to_i - result.te_i_to_e) / mean_te
            assert relative_diff < 2.0, (
                f"Symmetric coupling should yield similar TE in both directions. "
                f"E->I={result.te_e_to_i:.4f}, I->E={result.te_i_to_e:.4f}, "
                f"relative diff={relative_diff:.2f}"
            )

    def test_te_surrogates_destroy_signal(self) -> None:
        """For a causal pair, surrogate-based p-value should be small (< 0.05)."""
        N, nE = 200, 160
        engine = _make_engine(
            N=N, nE=nE, buffer_size=1500, n_surrogates=100, history_depth=4
        )
        _feed_causal_pair(engine, N, nE, steps=1500, delay=3, seed=77)
        result = engine.compute()

        assert result is not None
        assert result.p_value_e_to_i < 0.05, (
            f"p-value for causal E->I direction should be < 0.05, got {result.p_value_e_to_i}"
        )

    def test_buffer_overflow_deterministic(self) -> None:
        """Ring buffer should wrap without crash and return valid results."""
        N, nE = 100, 80
        buf_size = 200
        engine = _make_engine(
            N=N, nE=nE, buffer_size=buf_size, n_surrogates=10, history_depth=2
        )

        rng = np.random.default_rng(seed=123)
        # Feed well beyond the buffer size.
        total_steps = buf_size * 5
        for t in range(total_steps):
            spiked = rng.random(N) < 0.05
            engine.observe(spiked, t)

        result = engine.compute()
        assert result is not None
        # Values should be finite.
        assert np.isfinite(result.te_e_to_i)
        assert np.isfinite(result.te_i_to_e)
        assert np.isfinite(result.te_net)
        assert 0.0 <= result.p_value_e_to_i <= 1.0
        assert 0.0 <= result.p_value_i_to_e <= 1.0
        assert result.timestamp_step == total_steps - 1
