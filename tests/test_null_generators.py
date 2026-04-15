"""Smoke + contract tests for each null family.

Ensures broken families cannot silently pass screening by enforcing:
length, diagnostics presence, seed determinism, timeout visibility,
no silent exception swallowing.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.nulls import FAMILIES, NullDiagnostics

FAMILY_NAMES = sorted(FAMILIES.keys())


@pytest.fixture
def linear_signal() -> np.ndarray:
    rng = np.random.default_rng(123)
    return rng.standard_normal(4096)


@pytest.fixture
def too_short_signal() -> np.ndarray:
    return np.arange(16, dtype=float)


@pytest.mark.parametrize("family_name", FAMILY_NAMES)
def test_length_preserved(family_name: str, linear_signal: np.ndarray) -> None:
    fn = FAMILIES[family_name]
    y, diag = fn(linear_signal, seed=0, timeout_s=30.0)
    assert y.shape == linear_signal.shape
    assert diag.length == len(linear_signal)


@pytest.mark.parametrize("family_name", FAMILY_NAMES)
def test_diagnostics_present(family_name: str, linear_signal: np.ndarray) -> None:
    fn = FAMILIES[family_name]
    _, diag = fn(linear_signal, seed=0, timeout_s=30.0)
    assert isinstance(diag, NullDiagnostics)
    assert diag.null_family == family_name
    assert diag.seed == 0
    assert isinstance(diag.converged, bool)
    assert isinstance(diag.terminated_by_timeout, bool)
    assert isinstance(diag.preserves_distribution_exactly, bool)
    assert diag.psd_error is not None
    assert diag.acf_error is not None
    assert diag.delta_h_surrogate is not None


@pytest.mark.parametrize("family_name", FAMILY_NAMES)
def test_seed_determinism(family_name: str, linear_signal: np.ndarray) -> None:
    fn = FAMILIES[family_name]
    y1, _ = fn(linear_signal, seed=7, timeout_s=30.0)
    y2, _ = fn(linear_signal, seed=7, timeout_s=30.0)
    assert np.array_equal(y1, y2), f"{family_name} not deterministic under seed"


@pytest.mark.parametrize("family_name", FAMILY_NAMES)
def test_seed_variability(family_name: str, linear_signal: np.ndarray) -> None:
    fn = FAMILIES[family_name]
    y_a, _ = fn(linear_signal, seed=11, timeout_s=30.0)
    y_b, _ = fn(linear_signal, seed=17, timeout_s=30.0)
    # Different seeds must produce different surrogates.
    assert not np.array_equal(y_a, y_b), f"{family_name} seed has no effect"


@pytest.mark.parametrize("family_name", FAMILY_NAMES)
def test_timeout_surfaces_in_diagnostics(family_name: str, linear_signal: np.ndarray) -> None:
    """A sub-iteration timeout must be reported, not swallowed."""
    fn = FAMILIES[family_name]
    _, diag = fn(linear_signal, seed=0, timeout_s=1e-6)
    # Either the family completed under the sub-microsecond budget (the
    # wavelet path can still produce *something* before checking timeout),
    # OR it explicitly reports terminated_by_timeout. Silent swallow is
    # the failure mode we guard against.
    assert diag.terminated_by_timeout or diag.converged


@pytest.mark.parametrize("family_name", FAMILY_NAMES)
def test_short_signal_rejects(family_name: str, too_short_signal: np.ndarray) -> None:
    fn = FAMILIES[family_name]
    with pytest.raises(ValueError):
        fn(too_short_signal, seed=0, timeout_s=5.0)


def test_constrained_randomization_preserves_marginal_exactly() -> None:
    from core.nulls.constrained_randomization import generate_surrogate

    rng = np.random.default_rng(3)
    x = rng.standard_normal(1024)
    y, diag = generate_surrogate(x, seed=0, timeout_s=30.0, n_proposals=2000)
    assert diag.preserves_distribution_exactly is True
    assert float(np.max(np.abs(np.sort(x) - np.sort(y)))) < 1e-10


def test_wavelet_phase_does_not_claim_exact_preservation() -> None:
    from core.nulls.wavelet_phase import generate_surrogate

    rng = np.random.default_rng(3)
    x = rng.standard_normal(1024)
    _, diag = generate_surrogate(x, seed=0, timeout_s=30.0)
    assert diag.preserves_distribution_exactly is False


def test_linear_matched_does_not_claim_exact_preservation() -> None:
    from core.nulls.linear_matched import generate_surrogate

    rng = np.random.default_rng(3)
    x = rng.standard_normal(1024)
    _, diag = generate_surrogate(x, seed=0, timeout_s=30.0)
    assert diag.preserves_distribution_exactly is False
