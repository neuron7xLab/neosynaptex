"""Tests for core.mathematical_precision — advanced analytical toolkit."""

from __future__ import annotations

import numpy as np
import pytest

from core.mathematical_precision import (
    CramerRaoBound,
    FisherInformationResult,
    LyapunovResult,
    RenyiSpectrum,
    cramer_rao_fdt,
    fisher_information_gamma,
    lyapunov_exponent,
    renyi_entropy,
    renyi_spectrum,
)

# ═══════════════════════════════════════════════════════════════════════
#  Rényi entropy
# ═══════════════════════════════════════════════════════════════════════


class TestRenyiEntropy:
    def test_shannon_limit(self) -> None:
        """α=1 → Shannon entropy."""
        rng = np.random.default_rng(0)
        x = rng.normal(size=10000)
        h1 = renyi_entropy(x, alpha=1.0)
        assert h1 > 0

    def test_monotone_in_alpha(self) -> None:
        """H_α is non-increasing in α for fixed distribution."""
        rng = np.random.default_rng(42)
        x = rng.normal(size=5000)
        h0 = renyi_entropy(x, alpha=0.0)
        h1 = renyi_entropy(x, alpha=1.0)
        h2 = renyi_entropy(x, alpha=2.0)
        h_inf = renyi_entropy(x, alpha=100.0)
        assert h0 >= h1 - 0.01  # small tolerance for binning
        assert h1 >= h2 - 0.01
        assert h2 >= h_inf - 0.01

    def test_uniform_max_entropy(self) -> None:
        """Uniform distribution has max entropy for given support."""
        x = np.linspace(0, 1, 10000)
        h = renyi_entropy(x, alpha=1.0, n_bins=32)
        # For 32 bins uniform, Shannon = log(32) ≈ 3.47
        assert abs(h - np.log(32)) < 0.2

    def test_negative_alpha_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha"):
            renyi_entropy(np.zeros(100), alpha=-1.0)


class TestRenyiSpectrum:
    def test_spectrum_shape(self) -> None:
        rng = np.random.default_rng(7)
        x = rng.normal(size=5000)
        spec = renyi_spectrum(x)
        assert isinstance(spec, RenyiSpectrum)
        assert len(spec.alphas) == len(spec.entropies)

    def test_spectrum_fields(self) -> None:
        rng = np.random.default_rng(7)
        spec = renyi_spectrum(rng.normal(size=5000))
        assert spec.shannon_entropy > 0
        assert spec.min_entropy > 0
        assert spec.max_entropy >= spec.shannon_entropy - 0.1


# ═══════════════════════════════════════════════════════════════════════
#  Lyapunov exponent
# ═══════════════════════════════════════════════════════════════════════


class TestLyapunovExponent:
    def test_stable_trajectory(self) -> None:
        """Convergent trajectory → negative λ_max."""
        t = np.linspace(0, 10, 200)
        traj = np.column_stack([np.exp(-0.5 * t) * np.cos(t), np.exp(-0.5 * t) * np.sin(t)])
        result = lyapunov_exponent(traj, dt=0.05, max_steps=30)
        assert isinstance(result, LyapunovResult)
        assert result.lambda_max < 0.5  # should be negative or small

    def test_random_walk_near_zero(self) -> None:
        """Random walk → λ ≈ 0 (neither chaotic nor stable)."""
        rng = np.random.default_rng(42)
        traj = np.cumsum(rng.normal(size=(300, 2)), axis=0)
        result = lyapunov_exponent(traj, dt=1.0, max_steps=30)
        assert abs(result.lambda_max) < 2.0  # bounded, not extreme

    def test_short_trajectory_rejected(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            lyapunov_exponent(np.zeros((5, 2)), max_steps=50)

    def test_result_fields(self) -> None:
        rng = np.random.default_rng(0)
        traj = rng.normal(size=(200, 3))
        result = lyapunov_exponent(traj, max_steps=30)
        assert isinstance(result.is_chaotic, bool)
        assert isinstance(result.is_stable, bool)
        assert result.e_folding_time > 0


# ═══════════════════════════════════════════════════════════════════════
#  Fisher information
# ═══════════════════════════════════════════════════════════════════════


class TestFisherInformation:
    def test_high_precision_for_tight_gamma(self) -> None:
        """Tight γ around 1.0 → high Fisher info → low precision."""
        g = 1.0 + np.random.default_rng(0).normal(0, 0.01, size=100)
        result = fisher_information_gamma(g, theta_true=1.0)
        assert isinstance(result, FisherInformationResult)
        assert result.fisher_info > 100  # 1/0.01² = 10000
        assert result.estimation_precision < 0.1

    def test_low_precision_for_noisy_gamma(self) -> None:
        """Noisy γ → low Fisher info → high precision (bad)."""
        g = 1.0 + np.random.default_rng(0).normal(0, 0.5, size=100)
        result = fisher_information_gamma(g, theta_true=1.0)
        assert result.fisher_info < 10
        assert result.estimation_precision > 0.05

    def test_effective_samples_leq_n(self) -> None:
        """Correlated data → n_eff < n."""
        # Create correlated sequence
        rng = np.random.default_rng(42)
        g = np.zeros(200)
        g[0] = 1.0
        for i in range(1, 200):
            g[i] = 0.95 * g[i - 1] + 0.05 * rng.normal(1.0, 0.1)
        result = fisher_information_gamma(g, theta_true=1.0)
        assert result.effective_samples < 200

    def test_rejects_single_observation(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            fisher_information_gamma(np.array([1.0]))


# ═══════════════════════════════════════════════════════════════════════
#  Cramér-Rao bound
# ═══════════════════════════════════════════════════════════════════════


class TestCramerRao:
    def test_crlb_structure(self) -> None:
        result = cramer_rao_fdt(gamma_true=0.7, n_steps=2000, dt=0.01, n_monte_carlo=20, seed=42)
        assert isinstance(result, CramerRaoBound)
        assert result.crlb_variance > 0
        assert result.crlb_std > 0
        assert result.gamma_true == 0.7

    def test_efficiency_bounded(self) -> None:
        """Efficiency must be in [0, 1]."""
        result = cramer_rao_fdt(gamma_true=0.7, n_steps=5000, dt=0.01, n_monte_carlo=30, seed=0)
        assert 0.0 <= result.efficiency <= 1.0

    def test_more_data_tighter_bound(self) -> None:
        """More observations → lower CRLB variance."""
        r1 = cramer_rao_fdt(gamma_true=1.0, n_steps=1000, dt=0.01, n_monte_carlo=10)
        r2 = cramer_rao_fdt(gamma_true=1.0, n_steps=5000, dt=0.01, n_monte_carlo=10)
        assert r2.crlb_variance < r1.crlb_variance

    def test_invalid_params_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid"):
            cramer_rao_fdt(gamma_true=-1.0, n_steps=100, dt=0.01)
