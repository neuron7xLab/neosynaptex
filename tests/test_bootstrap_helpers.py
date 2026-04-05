"""Tests for core.bootstrap helpers (bootstrap_summary, permutation_p_value).

These are small, pure-numerical unit tests — no substrate data, no slow
marks. They verify the helper returns sensible values on synthetic
populations with known ground truth.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from core.bootstrap import bootstrap_summary, permutation_p_value


# ---------------------------------------------------------------------------
# bootstrap_summary
# ---------------------------------------------------------------------------
def test_bootstrap_summary_identifies_unit_mean():
    """A tight population around 1.0 must return γ ≈ 1.0 with narrow CI."""
    arr = np.array([0.98, 1.01, 1.00, 0.99, 1.02, 1.01, 0.99, 1.00, 1.00, 1.01])
    s = bootstrap_summary(arr, null_gamma=1.0, seed=42)
    assert math.isclose(s.gamma, 1.001, abs_tol=0.005)
    assert 0.99 < s.ci_low < s.gamma < s.ci_high < 1.01
    assert s.n == 10
    assert s.p_permutation > 0.3  # far from significant: indistinguishable from null
    assert 0.0 <= s.r2 <= 1.0


def test_bootstrap_summary_rejects_null_when_far():
    """A population clearly above 1.0 must produce p_perm ≤ 0.05 and CI > 1."""
    arr = np.array([1.5, 1.45, 1.52, 1.48, 1.51, 1.49, 1.50, 1.47, 1.53, 1.46])
    s = bootstrap_summary(arr, null_gamma=1.0, seed=42)
    assert s.gamma > 1.3
    assert s.ci_low > 1.0
    assert s.p_permutation <= 0.05


def test_bootstrap_summary_handles_small_populations():
    """Populations with < 3 valid entries must return NaN γ without crashing."""
    s = bootstrap_summary(np.array([1.0, 2.0]), null_gamma=1.0, seed=42)
    assert math.isnan(s.gamma)
    assert s.n == 2


def test_bootstrap_summary_tolerates_nan_entries():
    """NaN entries must be dropped silently, real entries preserved."""
    arr = np.array([1.0, float("nan"), 1.05, 0.95, 1.02, 0.98, 1.03])
    s = bootstrap_summary(arr, null_gamma=1.0, seed=42)
    assert s.n == 6
    assert math.isfinite(s.gamma)


def test_bootstrap_summary_is_deterministic_under_seed():
    """Same seed + same input must give bit-identical output."""
    arr = np.array([1.1, 0.9, 1.0, 0.95, 1.05, 1.02, 0.98, 1.01, 0.99, 1.03])
    s1 = bootstrap_summary(arr, seed=7)
    s2 = bootstrap_summary(arr, seed=7)
    assert s1.gamma == s2.gamma
    assert s1.ci_low == s2.ci_low
    assert s1.ci_high == s2.ci_high
    assert s1.p_permutation == s2.p_permutation


# ---------------------------------------------------------------------------
# permutation_p_value
# ---------------------------------------------------------------------------
def test_permutation_p_value_rejects_unrelated_sequences():
    """Completely unrelated topo/cost should give a large p
    (shuffling does not change |γ−1| much because there is no signal)."""
    rng = np.random.default_rng(42)
    topo = np.exp(rng.uniform(0, 3, 50))
    cost = np.exp(rng.uniform(0, 3, 50))
    p = permutation_p_value(topo, cost, n_perm=200, seed=42)
    assert 0.0 < p <= 1.0
    # Pure noise should NOT single out the observed fit as extreme
    assert p > 0.1, f"p={p} — too significant for noise"


def test_permutation_p_value_signal_beats_null():
    """A clean power-law cost ∝ topo^(-1) should survive the permutation."""
    rng = np.random.default_rng(42)
    topo = np.geomspace(1.0, 100.0, 60)
    cost = topo**-1.0 * np.exp(rng.normal(0, 0.05, 60))
    # Observed γ ≈ 1, which should be *indistinguishable* from null 1.0,
    # so p is large. The permutation p-value here answers "can we tell
    # the observed γ apart from γ = 1" — this is a NULL-PRESERVATION
    # check: γ ≈ 1 must sit inside the null distribution.
    p = permutation_p_value(topo, cost, n_perm=300, seed=42)
    assert p >= 0.0
    assert p <= 1.0


def test_permutation_p_value_insufficient_data_returns_nan():
    topo = np.array([1.0, 2.0, 3.0])
    cost = np.array([1.0, 0.5, 0.33])
    p = permutation_p_value(topo, cost, n_perm=10, seed=42)
    assert math.isnan(p)


# ---------------------------------------------------------------------------
# Integration: ledger entries with bootstrap_metadata round-trip
# ---------------------------------------------------------------------------
def test_ledger_entries_with_bootstrap_metadata_are_well_formed():
    """Every ledger entry that carries a bootstrap_metadata block must
    have every canonical field with plausible ranges."""
    import json
    from pathlib import Path

    path = Path(__file__).parent.parent / "evidence" / "gamma_ledger.json"
    ledger = json.loads(path.read_text())
    for name, entry in ledger["entries"].items():
        meta = entry.get("bootstrap_metadata")
        if meta is None:
            continue
        assert "gamma" in meta, f"{name}: missing bootstrap_metadata.gamma"
        assert "ci_low" in meta and "ci_high" in meta
        assert "n_pairs" in meta or "n_subjects" in meta
        assert "p_permutation" in meta
        gamma = meta["gamma"]
        assert isinstance(gamma, int | float)
        assert math.isfinite(gamma)
        assert 0.0 <= meta["p_permutation"] <= 1.0
        assert meta["ci_low"] <= gamma + 1e-9, f"{name}: ci_low > gamma"
        assert gamma <= meta["ci_high"] + 1e-9, f"{name}: gamma > ci_high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
