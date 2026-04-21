"""Falsification battery tests + null result contract."""

from __future__ import annotations

import numpy as np

from probe.falsification import FalsificationResult, run_falsification


def test_null_not_rejected_when_same_distribution() -> None:
    rng = np.random.default_rng(7)
    a = rng.normal(0.5, 0.1, size=32).tolist()
    b = rng.normal(0.5, 0.1, size=32).tolist()
    result = run_falsification(a, b, n_permutations=2000, seed=7)
    assert isinstance(result, FalsificationResult)
    assert result.permutation_p > 0.05
    assert not result.significant


def test_effect_detected_when_distributions_differ() -> None:
    rng = np.random.default_rng(7)
    human_ai = rng.normal(0.9, 0.1, size=40).tolist()
    llm = rng.normal(0.1, 0.1, size=40).tolist()
    result = run_falsification(human_ai, llm, n_permutations=5000, seed=7)
    assert result.permutation_p < 0.01
    assert result.significant
    assert result.cohens_d > 0.0


def test_null_confirmed_when_llm_mean_negative() -> None:
    rng = np.random.default_rng(7)
    human_ai = rng.normal(0.9, 0.1, size=20).tolist()
    llm = rng.normal(-0.1, 0.05, size=20).tolist()
    result = run_falsification(human_ai, llm, n_permutations=2000, seed=7)
    assert result.null_confirmed is True
    assert result.mean_llm < 0.0
    # Null result coexists with a significant human-AI vs LLM effect —
    # both facts must be reportable simultaneously.


def test_cohens_d_sign_matches_mean_difference() -> None:
    rng = np.random.default_rng(7)
    high = rng.normal(1.0, 0.05, size=20).tolist()
    low = rng.normal(0.2, 0.05, size=20).tolist()
    result = run_falsification(high, low, n_permutations=1000, seed=7)
    assert result.cohens_d > 0.0
    result2 = run_falsification(low, high, n_permutations=1000, seed=7)
    assert result2.cohens_d < 0.0


def test_ks_statistic_in_unit_interval() -> None:
    rng = np.random.default_rng(7)
    a = rng.normal(0.5, 0.1, size=32).tolist()
    b = rng.normal(0.6, 0.1, size=32).tolist()
    result = run_falsification(a, b, n_permutations=1000, seed=7)
    assert 0.0 <= result.ks_stat <= 1.0
    assert 0.0 <= result.ks_p <= 1.0


def test_insufficient_samples_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        run_falsification([0.5], [0.3, 0.4], n_permutations=100, seed=7)


def test_nonfinite_values_filtered() -> None:
    # NaN/inf must be stripped without crashing; 5 values minus one
    # non-finite leaves 4 per group.
    result = run_falsification(
        [0.5, float("nan"), 0.6, 0.7, 0.55],
        [0.1, float("inf"), 0.2, 0.15, 0.12],
        n_permutations=1000,
        seed=7,
    )
    assert result.n_human_ai == 4
    assert result.n_llm == 4
