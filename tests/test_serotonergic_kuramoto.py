"""Tests for the Serotonergic (5-HT2A) Kuramoto substrate.

Design contract (per CLAUDE.md spec):

  1. γ ∈ [0.7, 1.3] across the serotonergic concentration sweep that spans
     the canonical points {0, 0.25, 0.5, 0.75, 1.0}.
  2. Adapter interface matches the DomainAdapter protocol used by every
     other live NFI substrate (domain, state_keys, state, topo, thermo_cost).
  3. R(c) — the Kuramoto order parameter — decreases monotonically with
     increasing 5-HT2A concentration (entropic-brain signature).

Implementation notes
--------------------
Adapter construction runs the full sweep once and is moderately
expensive (~8 s). We therefore share ONE adapter across every test in
this module via a session-scoped fixture. Parameterised γ assertions at
the five canonical concentrations all read from the same pre-computed
sweep, keeping the whole file under ~15 s.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from substrates.serotonergic_kuramoto.adapter import (
    SerotonergicKuramotoAdapter,
    _sweep_gamma,
)

CANONICAL_CONCENTRATIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


# ---------------------------------------------------------------------------
# Shared session-scoped adapter (expensive to build)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def adapter() -> SerotonergicKuramotoAdapter:
    return SerotonergicKuramotoAdapter(concentration=0.5, seed=42)


@pytest.fixture(scope="module")
def sweep_gamma(adapter: SerotonergicKuramotoAdapter) -> tuple[float, float]:
    gamma, r2 = _sweep_gamma(adapter)
    return gamma, r2


# ---------------------------------------------------------------------------
# 1. DomainAdapter protocol compliance — must match the other substrates
# ---------------------------------------------------------------------------
def test_adapter_interface_matches_existing(
    adapter: SerotonergicKuramotoAdapter,
) -> None:
    # domain
    assert isinstance(adapter.domain, str)
    assert adapter.domain == "serotonergic_kuramoto"

    # state_keys — list of strings, at most 4 (engine contract)
    assert isinstance(adapter.state_keys, list)
    assert 1 <= len(adapter.state_keys) <= 4
    assert all(isinstance(k, str) for k in adapter.state_keys)

    # state() — dict[str, float] covering every declared key
    s = adapter.state()
    assert isinstance(s, dict)
    for k in adapter.state_keys:
        assert k in s, f"state() missing key '{k}'"
        assert isinstance(s[k], float)
        assert math.isfinite(s[k])

    # topo / thermo_cost — strictly positive floats
    t = adapter.topo()
    c = adapter.thermo_cost()
    assert isinstance(t, float) and t > 0.0 and math.isfinite(t)
    assert isinstance(c, float) and c > 0.0 and math.isfinite(c)


def test_adapter_topo_bounded_by_pair_count(
    adapter: SerotonergicKuramotoAdapter,
) -> None:
    """topo is a count of pairs (i<j), so 0 ≤ topo ≤ N·(N−1)/2 = 2016."""
    max_pairs = adapter._N * (adapter._N - 1) // 2
    for s in adapter._samples:
        assert 0.0 <= s["topo"] <= max_pairs


def test_adapter_integrates_with_neosynaptex_engine() -> None:
    from neosynaptex import Neosynaptex

    engine = Neosynaptex(window=16)
    engine.register(SerotonergicKuramotoAdapter(concentration=0.25, seed=3))
    state = None
    for _ in range(24):
        state = engine.observe()
    assert state is not None
    assert state.phase in (
        "INITIALIZING",
        "METASTABLE",
        "CONVERGING",
        "DRIFTING",
        "DIVERGING",
        "COLLAPSING",
        "DEGENERATE",
    )
    # The engine should have computed a per-domain γ for us
    assert "serotonergic_kuramoto" in state.gamma_per_domain


# ---------------------------------------------------------------------------
# 2. γ sits in [0.7, 1.3] across the serotonergic sweep
# ---------------------------------------------------------------------------
def test_sweep_gamma_in_metastable_range(
    adapter: SerotonergicKuramotoAdapter,
    sweep_gamma: tuple[float, float],
) -> None:
    gamma, r2 = sweep_gamma
    print(
        f"[serotonergic_kuramoto] sweep: γ={gamma:.4f} R²={r2:.4f} "
        f"K_c={adapter._Kc:.3f} rad/s "
        f"K/Kc∈[{adapter._samples[-1]['K_over_Kc']:.3f}, "
        f"{adapter._samples[0]['K_over_Kc']:.3f}]"
    )
    assert math.isfinite(gamma), "γ is not finite"
    assert 0.7 <= gamma <= 1.3, f"γ={gamma:.4f} leaves metastable [0.7, 1.3]"
    assert r2 > 0.3, f"R²={r2:.4f} too low for a meaningful scaling fit"


@pytest.mark.parametrize("concentration", CANONICAL_CONCENTRATIONS)
def test_canonical_concentration_sample_is_physical(
    adapter: SerotonergicKuramotoAdapter,
    concentration: float,
) -> None:
    """At each canonical c, verify metrics are physical and coupling obeys spec.

    The spec's γ-range requirement is covered by
    :func:`test_sweep_gamma_in_metastable_range`; this test verifies
    that the sweep *does contain* each canonical concentration with
    spec-consistent K_eff = K_base·(1 − 0.7·c).
    """
    s = adapter.sample_at(concentration)
    # K_eff obeys the spec formula exactly at the grid point nearest c
    expected_K_eff = 2.0 * (1.0 - 0.7 * s["c"])
    assert math.isclose(s["K_eff"], expected_K_eff, rel_tol=1e-9)
    # R ∈ [0, 1]
    assert 0.0 <= s["R"] <= 1.0
    # Phase entropy ∈ [0, log(bins)]
    assert 0.0 <= s["phase_entropy"] <= math.log(16) + 1e-6
    # Mean PLV ∈ [0, 1]
    assert 0.0 <= s["mean_plv"] <= 1.0
    # topo / cost strictly positive
    assert s["topo"] > 0.0
    assert s["thermo_cost"] > 0.0
    print(
        f"[canonical c={concentration:.2f}] K/Kc={s['K_over_Kc']:.3f} "
        f"R={s['R']:.4f} topo={s['topo']:.1f} cost={s['thermo_cost']:.3f}"
    )


# ---------------------------------------------------------------------------
# 3. R(c) monotonically decreases with 5-HT2A concentration
# ---------------------------------------------------------------------------
def test_order_parameter_monotonic_in_concentration(
    adapter: SerotonergicKuramotoAdapter,
) -> None:
    # R along the full pre-computed sweep
    c_grid = np.array([s["c"] for s in adapter._samples])
    R_grid = np.array([s["R"] for s in adapter._samples])
    # Sort by c (sweep is already ordered, but be explicit)
    order = np.argsort(c_grid)
    c_grid, R_grid = c_grid[order], R_grid[order]
    diffs = np.diff(R_grid)
    # Allow tiny numerical non-monotonicities (< 1 %) but require the
    # global trend to be strictly decreasing.
    assert np.all(diffs <= 1e-3), f"R(c) not non-increasing along sweep: diffs={diffs}"
    assert R_grid[0] > R_grid[-1] + 0.2, (
        f"R drop from c=0 to c=1 is too small: {R_grid[0]:.4f} → {R_grid[-1]:.4f}"
    )
    print(
        f"[R monotonicity] R(c=0)={R_grid[0]:.4f} "
        f"R(c=1)={R_grid[-1]:.4f}  ΔR={R_grid[0] - R_grid[-1]:.4f}"
    )


@pytest.mark.parametrize(
    "c_lo, c_hi",
    [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)],
)
def test_order_parameter_decreases_between_canonical_points(
    adapter: SerotonergicKuramotoAdapter,
    c_lo: float,
    c_hi: float,
) -> None:
    """Strict R(c_lo) > R(c_hi) for every adjacent canonical pair."""
    R_lo = adapter.sample_at(c_lo)["R"]
    R_hi = adapter.sample_at(c_hi)["R"]
    assert R_lo > R_hi, f"R({c_lo})={R_lo:.4f} !> R({c_hi})={R_hi:.4f}"


# ---------------------------------------------------------------------------
# 4. Determinism — same seed → same γ
# ---------------------------------------------------------------------------
def test_gamma_reproducible_across_constructions() -> None:
    a1 = SerotonergicKuramotoAdapter(concentration=0.5, seed=2024)
    a2 = SerotonergicKuramotoAdapter(concentration=0.5, seed=2024)
    g1, _ = _sweep_gamma(a1)
    g2, _ = _sweep_gamma(a2)
    assert math.isclose(g1, g2, rel_tol=1e-9), f"γ not reproducible: {g1} vs {g2}"
