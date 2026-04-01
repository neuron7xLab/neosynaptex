"""Tests for multi-scale criticality renormalization engine."""

from __future__ import annotations

import numpy as np

from bnsyn.criticality.renormalization import (
    RenormalizationEngine,
    RenormalizationParams,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

N = 64
NE = 48
WINDOW = 1000
TOTAL_STEPS = 1500
SPIKE_PROB = 0.005


def _make_engine(
    n_scales: int = 4, window: int = WINDOW
) -> RenormalizationEngine:
    params = RenormalizationParams(
        grouping_factor=4,
        n_scales=n_scales,
        analysis_window=window,
        update_interval=500,
    )
    return RenormalizationEngine(N=N, nE=NE, params=params)


def _feed_poisson(
    engine: RenormalizationEngine, steps: int, rng: np.random.Generator
) -> None:
    for t in range(steps):
        spikes = rng.random(N) < SPIKE_PROB
        engine.observe(spikes, step=t)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_none_insufficient_data() -> None:
    """compute() returns None when fewer than analysis_window steps observed."""
    engine = _make_engine()
    rng = np.random.default_rng(42)
    _feed_poisson(engine, WINDOW - 1, rng)
    assert engine.compute() is None


def test_correct_number_of_scales() -> None:
    """Result contains exactly n_scales ScaleMetrics entries."""
    engine = _make_engine(n_scales=4)
    rng = np.random.default_rng(42)
    _feed_poisson(engine, TOTAL_STEPS, rng)
    result = engine.compute()
    assert result is not None
    assert len(result.scales) == 4
    for i, sm in enumerate(result.scales):
        assert sm.scale == i


def test_sigma_cv_computed() -> None:
    """sigma_cv is a finite non-negative float."""
    engine = _make_engine()
    rng = np.random.default_rng(42)
    _feed_poisson(engine, TOTAL_STEPS, rng)
    result = engine.compute()
    assert result is not None
    assert np.isfinite(result.sigma_cv)
    assert result.sigma_cv >= 0.0


def test_scale_invariant_flag() -> None:
    """scale_invariant is True iff sigma_cv < 0.1."""
    engine = _make_engine()
    rng = np.random.default_rng(42)
    _feed_poisson(engine, TOTAL_STEPS, rng)
    result = engine.compute()
    assert result is not None
    assert result.scale_invariant == (result.sigma_cv < 0.1)


def test_entropy_rate_bounded() -> None:
    """entropy_rate is in [0, 1] for every scale."""
    engine = _make_engine()
    rng = np.random.default_rng(42)
    _feed_poisson(engine, TOTAL_STEPS, rng)
    result = engine.compute()
    assert result is not None
    for sm in result.scales:
        assert 0.0 <= sm.entropy_rate <= 1.0, (
            f"entropy_rate={sm.entropy_rate} out of [0,1] at scale {sm.scale}"
        )


def test_flow_trajectory_length() -> None:
    """flow_trajectory has exactly n_scales entries."""
    n_scales = 3
    engine = _make_engine(n_scales=n_scales)
    rng = np.random.default_rng(42)
    _feed_poisson(engine, TOTAL_STEPS, rng)
    result = engine.compute()
    assert result is not None
    assert len(result.flow_trajectory) == n_scales
    for sigma, tau, h in result.flow_trajectory:
        assert np.isfinite(sigma)
        assert np.isfinite(tau)
        assert np.isfinite(h)
