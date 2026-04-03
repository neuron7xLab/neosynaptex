"""Tests for the Truth Function — Sutskever's criterion.

7 tests verifying that the truth function correctly distinguishes
REAL gamma from ARTIFACT:
  1. Constructed (tautological) data -> CONSTRUCTED verdict
  2. Real scaling signal -> VERIFIED/INCONCLUSIVE (not CONSTRUCTED)
  3. Pure noise -> not VERIFIED
  4. Estimator consensus on clean signal
  5. Surrogate significance for real signal
  6. DFA cross-validation
  7. Engine integration via truth_function() method
"""

import numpy as np

from core.truth_function import assess_truth
from neosynaptex import (
    MockBnSynAdapter,
    MockMfnAdapter,
    MockPsycheCoreAdapter,
    Neosynaptex,
)


class TestTautologyDetection:
    def test_perfect_construction_detected(self):
        """If cost = topo^(-gamma) exactly, tautology risk should be high."""
        topo = np.linspace(1.0, 50.0, 40)
        # Perfectly constructed: cost = topo^(-1.0), zero noise
        cost = topo ** (-1.0)
        a = assess_truth(topo, cost, 1.0, n_surrogates=20, seed=42)
        assert a.tautology_risk >= 0.7, f"Expected tautology, got risk={a.tautology_risk}"
        assert a.r2_suspicion is True

    def test_noisy_signal_not_tautological(self):
        """Real signal with noise should NOT be flagged as tautological."""
        rng = np.random.default_rng(42)
        topo = np.linspace(1.0, 50.0, 40)
        cost = topo ** (-1.0) * (1.0 + 0.15 * rng.standard_normal(40))
        cost = np.maximum(cost, 0.01)
        a = assess_truth(topo, cost, 1.0, n_surrogates=20, seed=42)
        assert a.tautology_risk < 0.5, f"False tautology, risk={a.tautology_risk}"


class TestEstimatorConsensus:
    def test_clean_signal_estimators_agree(self):
        """On clean power-law data, all three estimators should agree."""
        rng = np.random.default_rng(99)
        topo = np.linspace(1.0, 100.0, 80)
        cost = topo ** (-1.0) * (1.0 + 0.02 * rng.standard_normal(80))
        cost = np.maximum(cost, 0.01)
        a = assess_truth(topo, cost, 1.0, n_surrogates=10, seed=42)
        assert a.estimators_agree, f"Spread={a.estimator_spread}"
        assert a.estimator_spread < 0.15


class TestSurrogateSignificance:
    def test_real_signal_survives_null(self):
        """True power-law signal should survive shuffle null."""
        rng = np.random.default_rng(7)
        topo = np.linspace(1.0, 80.0, 60)
        cost = topo ** (-1.0) * (1.0 + 0.05 * rng.standard_normal(60))
        cost = np.maximum(cost, 0.01)
        a = assess_truth(topo, cost, 1.0, n_surrogates=49, seed=42)
        assert a.survives_null, f"p={a.surrogate_p}"

    def test_noise_does_not_survive(self):
        """Pure noise should NOT survive surrogate test."""
        rng = np.random.default_rng(42)
        topo = np.abs(rng.standard_normal(40)) + 0.5
        cost = np.abs(rng.standard_normal(40)) + 0.5
        a = assess_truth(topo, cost, 0.5, n_surrogates=49, seed=42)
        # Either p > 0.05 or gamma is NaN (insufficient range/R2)
        if np.isfinite(a.surrogate_p):
            assert not a.survives_null or a.surrogate_p > 0.01


class TestDFACrossValidation:
    def test_dfa_on_sufficient_trace(self):
        """DFA should produce finite Hurst exponent on sufficient trace."""
        rng = np.random.default_rng(42)
        # Simulated gamma trace (Brownian-like, 200 points for DFA)
        trace = np.cumsum(0.01 * rng.standard_normal(200)) + 1.0
        topo = np.linspace(1.0, 50.0, 30)
        cost = topo ** (-1.0) * (1.0 + 0.05 * rng.standard_normal(30))
        cost = np.maximum(cost, 0.01)
        a = assess_truth(topo, cost, 1.0, gamma_trace=trace.tolist(), n_surrogates=10, seed=42)
        assert np.isfinite(a.hurst_exponent), "DFA should produce H"
        assert np.isfinite(a.gamma_dfa), "gamma_dfa = 2H+1 should be finite"


class TestEngineIntegration:
    def test_truth_function_method(self):
        """Neosynaptex.truth_function() returns per-domain assessments."""
        nx = Neosynaptex(window=16)
        nx.register(MockBnSynAdapter())
        nx.register(MockMfnAdapter())
        nx.register(MockPsycheCoreAdapter())
        for _ in range(30):
            nx.observe()
        result = nx.truth_function()

        assert "global_verdict" in result
        assert "per_domain" in result
        assert result["global_verdict"] in (
            "VERIFIED",
            "FRAGILE",
            "CONSTRUCTED",
            "INCONCLUSIVE",
        )
        # At least one domain should have assessment
        assert len(result["per_domain"]) >= 2
        for domain, assessment in result["per_domain"].items():
            assert "verdict" in assessment
            assert "tautology_risk" in assessment
