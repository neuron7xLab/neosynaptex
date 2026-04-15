"""Screening decision-rule tests — guard against broken family passes."""

from __future__ import annotations

import numpy as np

import run_null_family_screening as rns
from core.nulls.metrics import acf_rmse, compute_delta_h, distribution_error, log_psd_rmse


# ---------------------------------------------------------------------------
# Metric sanity
# ---------------------------------------------------------------------------
def test_distribution_error_zero_on_permutation() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(1024)
    y = rng.permutation(x)
    assert distribution_error(x, y) < 1e-12


def test_distribution_error_positive_on_scale() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(1024)
    assert distribution_error(x, 2.0 * x) > 0.5


def test_log_psd_rmse_self_zero() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(1024)
    assert log_psd_rmse(x, x) < 1e-12


def test_acf_rmse_self_zero() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(1024)
    assert acf_rmse(x, x) < 1e-12


def test_compute_delta_h_finite() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(4096)
    dh = compute_delta_h(x)
    assert np.isfinite(dh)
    assert dh >= 0.0


# ---------------------------------------------------------------------------
# Fixture validity
# ---------------------------------------------------------------------------
def test_binomial_cascade_fixture_is_multifractal() -> None:
    x = rns.fix_binomial_cascade(n_levels=12, p=0.3, seed=0)
    dh = compute_delta_h(x)
    assert dh > rns.CASCADE_DH_PREFLIGHT, f"cascade Δh={dh} below preflight gate"


def test_hrv_like_synthetic_deterministic_and_finite() -> None:
    y1 = rns.fix_hrv_like_nonlinear(n=4096, seed=42)
    y2 = rns.fix_hrv_like_nonlinear(n=4096, seed=42)
    assert np.array_equal(y1, y2)
    assert y1.shape == (4096,)
    assert np.all(np.isfinite(y1))
    assert float(np.var(y1)) > 0


def test_linear_fixtures_have_small_delta_h() -> None:
    """Linear synthetics should sit at low intrinsic Δh — if not, the
    measurement branch is misreporting."""
    for name, x in (
        ("white_noise", rns.fix_white_noise(4096, 0)),
        ("pink_fgn_H07", rns.fix_pink_fgn(4096, 0.7, 0)),
        ("phase_rand_1f", rns.fix_phase_rand_1f(4096, 0)),
    ):
        dh = compute_delta_h(x)
        assert dh < 0.30, f"{name}: linear fixture Δh={dh} unexpectedly large"


# ---------------------------------------------------------------------------
# Preflight gate behaviour
# ---------------------------------------------------------------------------
def test_preflight_returns_ok_on_healthy_fixtures() -> None:
    ok, msg, info = rns.preflight()
    assert ok, f"preflight should succeed: {msg}"
    assert "cascade_delta_h" in info


# ---------------------------------------------------------------------------
# Admissibility rule behaviour
# ---------------------------------------------------------------------------
def _make_fixture_outcome(
    fixture: str,
    kind: str,
    *,
    sep: float,
    psd: float = 0.01,
    acf: float = 0.01,
    std_dh: float = 0.001,
    dist: float = 0.0,
    timeout: bool = False,
) -> rns.FixtureOutcome:
    return rns.FixtureOutcome(
        fixture=fixture,
        kind=kind,
        delta_h_real=0.5,
        seed_runs=[],
        median_delta_h_surrogate=0.5 - sep,
        median_psd_error=psd,
        median_acf_error=acf,
        max_dist_error=dist,
        sep=sep,
        std_psd_error=0.001,
        std_acf_error=0.001,
        std_dh_surrogate=std_dh,
        any_timeout=timeout,
    )


def test_admissibility_rejects_timeout() -> None:
    fx = [
        _make_fixture_outcome("ln", "linear_synth", sep=0.0, timeout=True),
    ]
    admit, fails, _ = rns.evaluate_admissibility("family", True, fx)
    assert not admit
    assert any("FAIL_NULL_TIMEOUT" in f for f in fails)


def test_admissibility_rejects_dist_drift_when_claimed_exact() -> None:
    fx = [
        _make_fixture_outcome("ln", "linear_synth", sep=0.0, dist=1e-5),
    ]
    admit, fails, _ = rns.evaluate_admissibility("family", True, fx)
    assert not admit
    assert any("FAIL_NULL_DIST" in f for f in fails)


def test_admissibility_does_not_require_exact_dist_when_not_claimed() -> None:
    fx = [
        _make_fixture_outcome("ln", "linear_synth", sep=0.0, dist=0.5),
        _make_fixture_outcome("nl", "nonlinear_synth", sep=0.2),
    ]
    admit, fails, _ = rns.evaluate_admissibility("family", False, fx)
    assert admit, f"non-exact-claiming family should pass on dist=0.5; fails={fails}"


def test_admissibility_rejects_false_nonlinearity_injection() -> None:
    """All linear fixtures show sep > LINEAR_SEP_ABS_GATE — injection."""
    fx = [
        _make_fixture_outcome("ln1", "linear_synth", sep=0.10),
        _make_fixture_outcome("ln2", "linear_synth", sep=0.12),
        _make_fixture_outcome("ln3", "linear_synth", sep=0.11),
        _make_fixture_outcome("nl", "nonlinear_synth", sep=0.20),
    ]
    admit, fails, _ = rns.evaluate_admissibility("family", False, fx)
    assert not admit
    assert any("FAIL_DISC_LINEAR" in f or "FAIL_DISC_INJECTION" in f for f in fails)


def test_admissibility_rejects_collapse() -> None:
    """All nonlinear fixtures show sep ≤ 0.02 — collapse."""
    fx = [
        _make_fixture_outcome("ln", "linear_synth", sep=0.0),
        _make_fixture_outcome("nl1", "nonlinear_synth", sep=0.015),
        _make_fixture_outcome("nl2", "nonlinear_synth", sep=0.01),
    ]
    admit, fails, _ = rns.evaluate_admissibility("family", False, fx)
    assert not admit
    assert "FAIL_DISC_COLLAPSE" in fails


def test_admissibility_admits_well_behaved_family() -> None:
    fx = [
        _make_fixture_outcome("ln1", "linear_synth", sep=0.01),
        _make_fixture_outcome("ln2", "linear_synth", sep=-0.01),
        _make_fixture_outcome("nl1", "nonlinear_synth", sep=0.20),
        _make_fixture_outcome("nl2", "nonlinear_synth", sep=0.10),
    ]
    admit, fails, _ = rns.evaluate_admissibility("family", False, fx)
    assert admit, f"well-behaved family should admit; fails={fails}"


# ---------------------------------------------------------------------------
# Selection rule behaviour (§SELECTION LAW — simplest first)
# ---------------------------------------------------------------------------
def test_selection_prefers_simpler_family() -> None:
    def _fo(name: str) -> rns.FamilyOutcome:
        return rns.FamilyOutcome(
            family=name,
            preserves_distribution_exactly=False,
            fixtures=[],
            admit=True,
            fail_codes=[],
            summary_notes=[],
        )

    chosen = rns.select_single(
        [_fo("constrained_randomization"), _fo("linear_matched"), _fo("wavelet_phase")]
    )
    assert chosen is not None
    # linear_matched has the lowest simplicity rank → must be selected.
    assert chosen.family == "linear_matched"


def test_selection_none_when_no_admissible() -> None:
    assert rns.select_single([]) is None
