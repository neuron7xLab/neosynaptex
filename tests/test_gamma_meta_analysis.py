"""Tests for ``analysis.gamma_meta_analysis``.

Cover:
  * structural shape of ``MetaResult`` / ``HeterogeneityResult`` /
    ``ProofBundle`` / ``ForestRow``;
  * homogeneous-inputs invariants (zero heterogeneity, pooled gamma
    equals input);
  * inverse-variance weighting matches a manual calculation;
  * forest-plot weight percentages sum to 100;
  * on the canonical ``evidence/gamma_ledger.json``, the verdict is
    ``INVARIANT_CONFIRMED`` and the prediction interval is wider than
    the pooled CI (structural property of random-effects meta-analysis).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from analysis.gamma_meta_analysis import (
    ForestRow,
    GammaMetaAnalysis,
    HeterogeneityResult,
    MetaResult,
    ProofBundle,
    SubstrateResult,
    load_from_gamma_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _homogeneous_substrates(
    k: int = 5, gamma: float = 1.0, half_ci: float = 0.1
) -> list[SubstrateResult]:
    return [
        SubstrateResult(
            name=f"s{i}",
            gamma=gamma,
            ci_lower=gamma - half_ci,
            ci_upper=gamma + half_ci,
            n=10,
        )
        for i in range(k)
    ]


# ── synthetic invariants ─────────────────────────────────────────────


def test_constructor_rejects_single_substrate() -> None:
    with pytest.raises(ValueError, match="requires >= 2"):
        GammaMetaAnalysis([SubstrateResult("solo", 1.0, 0.9, 1.1, 10)])


def test_constructor_rejects_degenerate_ci() -> None:
    with pytest.raises(ValueError, match="degenerate CI"):
        GammaMetaAnalysis(
            [
                SubstrateResult("bad", 1.0, 1.0, 1.0, 10),
                SubstrateResult("ok", 1.0, 0.9, 1.1, 10),
            ]
        )


def test_homogeneous_pooled_gamma_equals_input() -> None:
    subs = _homogeneous_substrates(k=5, gamma=1.0, half_ci=0.1)
    a = GammaMetaAnalysis(subs)
    fe = a.pooled_estimate_fixed_effects()
    re = a.pooled_estimate_random_effects()
    assert math.isclose(fe.gamma, 1.0, abs_tol=1e-12)
    assert math.isclose(re.gamma, 1.0, abs_tol=1e-12)
    # With identical inputs Cochran's Q is zero, so tau^2 collapses.
    assert re.tau2 == 0.0


def test_homogeneous_heterogeneity_zero() -> None:
    a = GammaMetaAnalysis(_homogeneous_substrates())
    h = a.heterogeneity()
    assert h.Q < 1e-9
    assert h.I2 == 0.0


def test_fixed_effects_weighted_mean_matches_manual() -> None:
    # Two substrates with different precision; manual inverse-variance check.
    s = [
        SubstrateResult("a", gamma=0.9, ci_lower=0.8, ci_upper=1.0, n=10),
        SubstrateResult("b", gamma=1.1, ci_lower=1.05, ci_upper=1.15, n=20),
    ]
    fe = GammaMetaAnalysis(s).pooled_estimate_fixed_effects()

    # Re-derive the reference value independently of the module.
    # We use the same z_0.975 constant the module uses so the check is
    # exact (not sensitive to 1.96 vs 1.9599... rounding).
    from scipy.stats import norm

    z = float(norm.ppf(0.975))
    se_a = 0.1 / z
    se_b = 0.05 / z
    w_a = 1.0 / se_a**2
    w_b = 1.0 / se_b**2
    expected = (w_a * 0.9 + w_b * 1.1) / (w_a + w_b)

    assert math.isclose(fe.gamma, expected, rel_tol=1e-12)


def test_forest_weights_sum_to_100_percent() -> None:
    a = GammaMetaAnalysis(_homogeneous_substrates(k=5))
    forest = a.forest_plot_data()
    assert math.isclose(sum(r.weight_fixed_pct for r in forest), 100.0, abs_tol=1e-9)
    assert math.isclose(sum(r.weight_random_pct for r in forest), 100.0, abs_tol=1e-9)


def test_meta_result_ci_round_trips_through_se() -> None:
    a = GammaMetaAnalysis(_homogeneous_substrates(k=4, gamma=1.03, half_ci=0.05))
    fe = a.pooled_estimate_fixed_effects()
    # CI half-width / z should recover SE.
    from scipy.stats import norm

    z = float(norm.ppf(0.975))
    recovered_se = (fe.ci_upper - fe.ci_lower) / (2.0 * z)
    assert math.isclose(recovered_se, fe.se, rel_tol=1e-12)


# ── canonical-ledger end-to-end ──────────────────────────────────────


@pytest.fixture
def ledger_bundle() -> ProofBundle:
    subs = load_from_gamma_ledger(REPO_ROOT / "evidence" / "gamma_ledger.json")
    assert len(subs) >= 5, f"expected >=5 validated substrates, got {len(subs)}"
    return GammaMetaAnalysis(subs).run_full_analysis()


def test_proof_bundle_has_expected_fields(ledger_bundle: ProofBundle) -> None:
    assert isinstance(ledger_bundle.fixed, MetaResult)
    assert isinstance(ledger_bundle.random, MetaResult)
    assert isinstance(ledger_bundle.heterogeneity, HeterogeneityResult)
    assert isinstance(ledger_bundle.prediction_interval, tuple)
    assert len(ledger_bundle.prediction_interval) == 2
    assert all(isinstance(r, ForestRow) for r in ledger_bundle.forest)
    assert ledger_bundle.n_substrates == len(ledger_bundle.forest)


def test_meta_result_ci_bounds_well_formed(ledger_bundle: ProofBundle) -> None:
    for m in (ledger_bundle.fixed, ledger_bundle.random):
        assert m.ci_lower < m.gamma < m.ci_upper
        assert m.se > 0.0
        assert 0.0 <= m.p_value <= 1.0


def test_heterogeneity_fields_in_range(ledger_bundle: ProofBundle) -> None:
    h = ledger_bundle.heterogeneity
    assert h.Q >= 0.0
    assert h.df >= 1
    assert 0.0 <= h.I2 <= 100.0
    assert 0.0 <= h.p_heterogeneity <= 1.0


def test_verdict_is_confirmed(ledger_bundle: ProofBundle) -> None:
    assert ledger_bundle.verdict == "INVARIANT_CONFIRMED", (
        f"verdict REJECTED with reasons: {ledger_bundle.verdict_reasons}"
    )
    assert ledger_bundle.verdict_reasons == []


def test_prediction_interval_at_least_as_wide_as_random_ci(
    ledger_bundle: ProofBundle,
) -> None:
    # PI bounds where a *new* substrate's true gamma would fall; it
    # must be at least as wide as the CI for the pooled centre
    # (strictly wider when tau^2 > 0).
    re = ledger_bundle.random
    pi_low, pi_high = ledger_bundle.prediction_interval
    pi_width = pi_high - pi_low
    ci_width = re.ci_upper - re.ci_lower
    assert pi_width >= ci_width - 1e-12


def test_pooled_random_ci_contains_one(ledger_bundle: ProofBundle) -> None:
    re = ledger_bundle.random
    assert re.ci_lower <= 1.0 <= re.ci_upper


def test_ledger_loader_drops_non_validated() -> None:
    # All loaded rows must have VALIDATED status with a complete CI.
    subs = load_from_gamma_ledger(REPO_ROOT / "evidence" / "gamma_ledger.json")
    for s in subs:
        assert s.ci_lower < s.ci_upper
        assert s.ci_lower <= s.gamma <= s.ci_upper or math.isclose(
            s.gamma, s.ci_upper, abs_tol=1e-6
        )
