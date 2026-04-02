"""12 tests for falsification shield — method sensitivity, null ensembles, bias detection."""

import numpy as np

from core.falsification import (
    BiasProbeResult,
    bias_probe,
    estimate_gamma_multi,
    null_ensemble_test,
    run_falsification,
)


def _make_power_law(gamma: float = 1.0, n: int = 128, noise: float = 0.05, seed: int = 42):
    rng = np.random.default_rng(seed)
    topo = np.linspace(1, 10, n)
    cost = 10.0 * topo ** (-gamma) + rng.normal(0, noise, n)
    return np.log(topo), np.log(np.clip(cost, 1e-6, None))


# ─── Axis 1: Estimator Sensitivity ──────────────────────────────────────


def test_three_estimators_returned():
    lt, lc = _make_power_law(1.0)
    results = estimate_gamma_multi(lt, lc)
    assert len(results) == 3
    names = {r.name for r in results}
    assert names == {"theilslopes", "ols", "huber"}


def test_estimators_agree_on_clean_data():
    lt, lc = _make_power_law(1.0, noise=0.01)
    results = estimate_gamma_multi(lt, lc)
    gammas = [r.gamma for r in results]
    spread = max(gammas) - min(gammas)
    assert spread < 0.1, f"Estimators disagree too much: spread={spread:.4f}"


def test_estimator_ci_contains_true():
    lt, lc = _make_power_law(1.0, noise=0.05)
    results = estimate_gamma_multi(lt, lc)
    for r in results:
        assert r.ci_low <= 1.1 and r.ci_high >= 0.9, (
            f"{r.name}: CI [{r.ci_low:.3f}, {r.ci_high:.3f}] doesn't contain ~1.0"
        )


# ─── Axis 2: Null Ensemble ──────────────────────────────────────────────


def test_null_ensemble_significant_for_real_signal():
    lt, lc = _make_power_law(1.0)
    result = null_ensemble_test(lt, lc, n_surrogates=99)
    assert result.p_shuffle < 0.05, f"Shuffle p={result.p_shuffle}"
    assert result.significant or result.p_iaaft < 0.1


def test_null_ensemble_not_significant_for_noise():
    rng = np.random.default_rng(42)
    lt = np.log(np.linspace(1, 10, 128))
    lc = rng.normal(0, 1, 128)  # pure noise, no power law
    result = null_ensemble_test(lt, lc, n_surrogates=99)
    # Shuffle should NOT be significant for pure noise
    assert result.p_shuffle > 0.01


def test_null_returns_all_p_values():
    lt, lc = _make_power_law(1.0)
    result = null_ensemble_test(lt, lc, n_surrogates=49)
    assert 0.0 <= result.p_shuffle <= 1.0
    assert 0.0 <= result.p_iaaft <= 1.0
    assert 0.0 <= result.p_phase_rand <= 1.0


# ─── Axis 3: Bias Detector ──────────────────────────────────────────────


def test_bias_probe_returns_results():
    results = bias_probe(gamma_values=[0.5, 1.0, 1.5], n_trials=20)
    assert len(results) == 3
    assert all(isinstance(r, BiasProbeResult) for r in results)


def test_bias_small_at_gamma_one():
    results = bias_probe(gamma_values=[1.0], n_trials=50, noise=0.05)
    assert abs(results[0].bias_theilsen) < 0.05
    assert abs(results[0].bias_ols) < 0.05


def test_bias_curve_monotonic():
    results = bias_probe(gamma_values=[0.0, 0.5, 1.0, 1.5, 2.0], n_trials=30)
    ts_gammas = [r.gamma_theilsen for r in results]
    # Recovered gammas should roughly increase with true gammas
    assert ts_gammas[-1] > ts_gammas[0]


# ─── Full Report ────────────────────────────────────────────────────────


def test_full_falsification_report():
    substrates = {
        "syn_a": _make_power_law(0.95, seed=1),
        "syn_b": _make_power_law(1.0, seed=2),
        "syn_c": _make_power_law(1.05, seed=3),
    }
    report = run_falsification(substrates, seed=42)
    assert report.verdict in ("ROBUST", "FRAGILE", "INCONCLUSIVE")
    assert len(report.estimator_sensitivity) == 3
    assert len(report.null_ensemble) == 3
    assert len(report.bias_curve) == 10


def test_falsification_verdict_robust_on_clean():
    substrates = {
        "clean_a": _make_power_law(0.95, noise=0.03, seed=10),
        "clean_b": _make_power_law(1.0, noise=0.03, seed=20),
    }
    report = run_falsification(substrates, seed=42)
    # Clean data should give ROBUST or at worst INCONCLUSIVE
    assert report.verdict in ("ROBUST", "INCONCLUSIVE")
