# ruff: noqa: N802 — physics naming convention (R = Kuramoto order parameter, K_eff, K_c)
"""Phase 4b — canonical Kuramoto observable tests.

Tests the *coordinate contract* (``core.exponent_measurement``) and
the *boundary observable contract* (``substrates.serotonergic_kuramoto
.observables``) against analytically known reference values. None of
these tests touches the substrate adapter, runs the simulation, or
makes any γ claim. They only verify that the building blocks of a
future canonical γ-claim path produce the right numbers on inputs
where the answer is provable from theory.

Verdict logic for this PR:
    CI passes if these tests pass. β = 0.5 is *not* required to pass
    here — the β fit lives in Phase 4d. This PR only ratifies that
    the measurement object is correctly defined.

Numbered structural tests:

A.  ``order_parameter_R`` on coherent phases (all θ_i = 0) returns 1.
B.  ``order_parameter_R`` on uniformly random phases approaches 0 as
    N grows (with a quantified rate).
C.  Two-cluster hand-built phase state gives the analytical R = |cos(Δ/2)|
    for clusters at ±Δ/2 with equal occupancy.
D.  ``compute_K_eff(c, K_base, mod_slope)`` matches the closed form
    on a parametric grid.
E.  ``compute_K_c_from_frequency_density`` is deterministic and
    matches ``σ · sqrt(8/π)`` for a Gaussian draw, on independent
    repeats with the same input array.
F.  ``compute_reduced_coupling`` is deterministic on a grid.
G.  ``c_crossing ≈ 0.963`` from the canonical adapter constants
    (K_base = 2.0, mod_slope = 0.7, σ_op = 0.065 Hz).
H.  Adapter ``topo``/``thermo_cost`` source files (text inspection)
    are not exposed by the canonical Phase 4b modules.
I.  Forbidden claims absent from the new Phase 4b doc.
J.  ``susceptibility_chi`` on a degenerate constant ``R(t)`` gives 0.
K.  ``order_parameter_R_timeseries`` returns shape (T,) and entries
    in [0, 1].
L.  Per-function input-validation: every helper raises ``ValueError``
    on degenerate input it cannot meaningfully handle.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from core.exponent_measurement import (
    EXPECTED_BETA_SUPER_CRITICAL,
    EXPECTED_GAMMA_SUSCEPTIBILITY,
    compute_c_at_critical_crossing,
    compute_K_c_from_frequency_density,
    compute_K_eff,
    compute_reduced_coupling,
)
from substrates.serotonergic_kuramoto.observables import (
    instantaneous_R,
    order_parameter_R,
    order_parameter_R_timeseries,
    susceptibility_chi,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROTOCOL_PATH = _REPO_ROOT / "docs" / "audit" / "PHASE_4B_CANONICAL_KURAMOTO_OBSERVABLES.md"
_ADAPTER_PATH = _REPO_ROOT / "substrates" / "serotonergic_kuramoto" / "adapter.py"


# Adapter calibration constants (matches the literal values in
# ``substrates/serotonergic_kuramoto/adapter.py``). Hard-coded here to
# avoid importing the adapter module (which triggers the Phase 2.1
# binding gate; tests must be importable on a stale-binding worktree).
_K_BASE: float = 2.0
_MOD_SLOPE: float = 0.7
_SIGMA_HZ_OP: float = 0.065
_MEAN_HZ: float = 10.0
_N_OSC: int = 64


# A
def test_order_parameter_R_on_coherent_phases_returns_one() -> None:
    theta_history = np.zeros((100, _N_OSC), dtype=np.float64)
    R = order_parameter_R(theta_history)
    assert math.isclose(R, 1.0, rel_tol=0.0, abs_tol=1e-12)


# B
@pytest.mark.parametrize("n_oscillators", [16, 64, 256, 1024])
def test_order_parameter_R_on_uniform_random_phases_decays_with_N(
    n_oscillators: int,
) -> None:
    """Incoherent floor: R ≈ 1/√N for uniformly random phases."""
    rng = np.random.default_rng(42)
    theta_snapshot = rng.uniform(0.0, 2.0 * np.pi, size=n_oscillators)
    R = instantaneous_R(theta_snapshot)
    expected_floor = 1.0 / math.sqrt(n_oscillators)
    # R is a sum of N unit vectors whose magnitude scales as √N; divided
    # by N gives 1/√N. Allow 6× the floor as the upper bound for the
    # finite-sample fluctuation (very loose, ~6σ).
    assert 6.0 * expected_floor >= R, f"R={R} too large for N={n_oscillators} incoherent ensemble"


# C
@pytest.mark.parametrize("delta", [0.0, math.pi / 4, math.pi / 2, math.pi])
def test_order_parameter_R_on_two_cluster_state(delta: float) -> None:
    """Two equal-occupancy clusters at ±Δ/2 give R = |cos(Δ/2)|."""
    n_per_cluster = _N_OSC // 2
    theta_snapshot = np.concatenate(
        [
            np.full(n_per_cluster, +delta / 2.0),
            np.full(n_per_cluster, -delta / 2.0),
        ]
    )
    R = instantaneous_R(theta_snapshot)
    expected = abs(math.cos(delta / 2.0))
    assert math.isclose(R, expected, rel_tol=0.0, abs_tol=1e-12)


# D
@pytest.mark.parametrize(
    "c, K_base, mod_slope, expected",
    [
        (0.0, 2.0, 0.7, 2.0),
        (1.0, 2.0, 0.7, 0.6),
        (0.5, 2.0, 0.7, 1.3),
        (0.963, 2.0, 0.7, 2.0 * (1.0 - 0.7 * 0.963)),
        (0.0, 1.0, 0.5, 1.0),
        (1.0, 1.0, 0.5, 0.5),
    ],
)
def test_compute_K_eff_matches_closed_form(
    c: float, K_base: float, mod_slope: float, expected: float
) -> None:
    K_eff = compute_K_eff(c, K_base, mod_slope)
    assert math.isclose(K_eff, expected, rel_tol=0.0, abs_tol=1e-12)


# E
def test_compute_K_c_is_deterministic_and_matches_sigma_sqrt_8_over_pi() -> None:
    sigma = 0.4083  # ≈ 0.065 Hz · 2π
    rng = np.random.default_rng(0)
    omega = rng.normal(0.0, sigma, size=512)
    K_c_a = compute_K_c_from_frequency_density(omega)
    K_c_b = compute_K_c_from_frequency_density(omega)
    assert K_c_a == K_c_b  # deterministic
    expected = float(np.std(omega, ddof=0)) * math.sqrt(8.0 / math.pi)
    assert math.isclose(K_c_a, expected, rel_tol=0.0, abs_tol=1e-12)


# F
def test_compute_reduced_coupling_is_deterministic_on_grid() -> None:
    K_c = 0.6517
    grid = [0.1, 0.5, 1.0, 1.5, 2.0]
    a = [compute_reduced_coupling(K_eff, K_c) for K_eff in grid]
    b = [compute_reduced_coupling(K_eff, K_c) for K_eff in grid]
    assert a == b
    for K_eff, r in zip(grid, a, strict=True):
        assert math.isclose(r, (K_eff - K_c) / K_c, rel_tol=0.0, abs_tol=1e-12)


# G
def test_c_crossing_at_canonical_adapter_constants_is_about_0_963() -> None:
    """The canonical 5-HT2A axis crosses K_c at c ≈ 0.963."""
    sigma_rad = _SIGMA_HZ_OP * 2.0 * math.pi
    K_c = sigma_rad * math.sqrt(8.0 / math.pi)
    c_cross = compute_c_at_critical_crossing(_K_BASE, _MOD_SLOPE, K_c)
    assert math.isclose(c_cross, 0.963, abs_tol=0.005), (
        f"expected c_crossing ≈ 0.963 at canonical constants; got {c_cross}"
    )


# H
def test_topo_and_thermo_cost_are_not_in_canonical_observable_module() -> None:
    """Phase 4b canonical observables module exposes only theory-grounded
    Kuramoto observables. ``topo`` and ``thermo_cost`` are deprecated
    legacy paths and must not be re-exported here."""
    from substrates.serotonergic_kuramoto import observables

    public = set(getattr(observables, "__all__", ()))
    assert "topo" not in public
    assert "thermo_cost" not in public
    # And the new module must NOT define them (case-sensitive check).
    assert not hasattr(observables, "topo")
    assert not hasattr(observables, "thermo_cost")


# I
def test_no_forbidden_claims_in_phase_4b_protocol_doc() -> None:
    """The new Phase 4b protocol doc must not assert any of the
    Phase 4a forbidden claims as positive statements."""
    if not _PROTOCOL_PATH.is_file():
        pytest.skip("protocol doc not yet written; will be present in PR")
    text = _PROTOCOL_PATH.read_text(encoding="utf-8")
    forbidden = (
        "γ≈1 validated",
        "substrate validated",
        "Phase 4 fixed the hypothesis",
        "old γ preserved",
        "Theil-Sen killed the hypothesis",
    )
    disavowal_tokens = (
        "forbidden",
        "rejected",
        "must not",
        "do not",
        "does not",
        "is not",
        "never",
        "no auto-promotion",
        "anti-",
        "disavow",
        "forbidden_claims",
    )
    lines = text.splitlines()
    disavowal_at: set[int] = {
        i for i, line in enumerate(lines) if any(tok in line.lower() for tok in disavowal_tokens)
    }
    window = 12
    violations: list[str] = []
    for n, line in enumerate(lines, start=1):
        line_lower = line.lower()
        for phrase in forbidden:
            if phrase.lower() not in line_lower:
                continue
            if any(tok in line_lower for tok in disavowal_tokens):
                continue
            i0 = n - 1
            if any((i0 - k) in disavowal_at for k in range(1, window + 1)):
                continue
            violations.append(f"PHASE_4B doc:{n}: {phrase!r} → {line.strip()[:140]}")
    assert not violations, "positive forbidden-claim use:\n" + "\n".join(violations)


# J
def test_susceptibility_chi_is_zero_on_constant_R() -> None:
    R_values = np.full(64, 0.7, dtype=np.float64)
    chi = susceptibility_chi(R_values, _N_OSC)
    # var(constant) is exactly 0 in real arithmetic; numpy may return
    # ~1e-31 for a non-zero constant due to FP rounding in the
    # variance accumulator. Tolerance is the FP floor, not a science
    # tolerance.
    assert abs(chi) < 1e-12, f"χ on constant R must be ~0; got {chi}"


# K
def test_order_parameter_R_timeseries_shape_and_range() -> None:
    rng = np.random.default_rng(42)
    theta_history = rng.uniform(0.0, 2.0 * np.pi, size=(50, _N_OSC))
    series = order_parameter_R_timeseries(theta_history)
    assert series.shape == (50,)
    assert np.all(series >= 0.0)
    assert np.all(series <= 1.0)


# L
def test_input_validation_raises_value_error() -> None:
    with pytest.raises(ValueError):
        instantaneous_R(np.zeros((2, 2)))
    with pytest.raises(ValueError):
        instantaneous_R(np.zeros(0))
    with pytest.raises(ValueError):
        order_parameter_R_timeseries(np.zeros(10))
    with pytest.raises(ValueError):
        order_parameter_R_timeseries(np.zeros((0, 5)))
    with pytest.raises(ValueError):
        susceptibility_chi(np.array([0.5]), 64)
    with pytest.raises(ValueError):
        susceptibility_chi(np.array([0.5, 0.6]), 0)
    with pytest.raises(ValueError):
        compute_K_eff(0.5, K_base=0.0, mod_slope=0.7)
    with pytest.raises(ValueError):
        compute_K_c_from_frequency_density(np.array([]), distribution="gaussian")
    with pytest.raises(ValueError):
        compute_K_c_from_frequency_density(np.array([1.0, np.inf]))
    with pytest.raises(ValueError):
        compute_K_c_from_frequency_density(np.array([1.0, 2.0]), distribution="lorentzian")
    with pytest.raises(ValueError):
        compute_K_c_from_frequency_density(np.array([5.0, 5.0, 5.0]))  # zero variance
    with pytest.raises(ValueError):
        compute_reduced_coupling(1.0, K_c=0.0)
    with pytest.raises(ValueError):
        compute_c_at_critical_crossing(K_base=2.0, mod_slope=0.0, K_c=0.5)


# Sanity: the expected-exponent constants are exactly what theory says.
def test_expected_exponents_are_canonical_mean_field_values() -> None:
    assert EXPECTED_BETA_SUPER_CRITICAL == 0.5
    assert EXPECTED_GAMMA_SUSCEPTIBILITY == -1.0


# Sanity: the adapter file still has the wrong-docstring claim
# (c ≈ 0.71). Phase 4b documents the correct value (c ≈ 0.963) in
# the new protocol doc; the adapter docstring fix is deferred to a
# follow-up PR that also rebinds ``adapter_code_hash`` per Phase 2.1.
def test_adapter_docstring_inconsistency_documented() -> None:
    """Cross-reference: the adapter.py docstring still claims
    c ≈ 0.71 (an arithmetic error). Phase 4b does NOT modify the
    adapter source because changing it would invalidate the Phase 2.1
    ``adapter_code_hash`` binding without an accompanying ledger
    update — which is out of scope per the PR contract. The adapter
    fix lives in a follow-up PR. This test guards that: if a future
    contributor silently fixes the adapter docstring without updating
    the ledger binding, this test stays green (it only asserts the
    inconsistency *is acknowledged in the new protocol doc*) but the
    binding gate downstream will catch the SHA drift."""
    if not _PROTOCOL_PATH.is_file():
        pytest.skip("protocol doc not yet written")
    if not _ADAPTER_PATH.is_file():
        pytest.skip("adapter source not present in this checkout")
    proto = _PROTOCOL_PATH.read_text(encoding="utf-8")
    # The new protocol doc must document the correct crossing value
    # explicitly, regardless of whether the adapter has been fixed yet.
    assert "0.963" in proto, "PHASE_4B protocol doc must declare c_crossing ≈ 0.963"
