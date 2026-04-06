"""Tests for core.ablation_study — Task 6 ablation: role vs energy."""

from __future__ import annotations

import numpy as np
import pytest

from core.ablation_study import (
    ALL_REGIMES,
    REGIME_ENERGY_ONLY,
    REGIME_HYBRID,
    REGIME_ROLES_ONLY,
    AblationConfig,
    AblationReport,
    AblationStudy,
)
from core.coherence_state_space import CoherenceState

# ── Config validation ───────────────────────────────────────────────────


class TestAblationConfig:
    def test_valid_construction(self) -> None:
        cfg = AblationConfig(regime=REGIME_ROLES_ONLY)
        assert cfg.regime == REGIME_ROLES_ONLY
        assert cfg.n_steps == 200
        assert cfg.n_seeds == 10

    def test_invalid_regime_rejected(self) -> None:
        with pytest.raises(ValueError, match="regime must be one of"):
            AblationConfig(regime="unknown")

    def test_invalid_n_steps(self) -> None:
        with pytest.raises(ValueError, match="n_steps"):
            AblationConfig(regime=REGIME_ROLES_ONLY, n_steps=0)

    def test_invalid_n_seeds(self) -> None:
        with pytest.raises(ValueError, match="n_seeds"):
            AblationConfig(regime=REGIME_ROLES_ONLY, n_seeds=0)

    def test_custom_initial_state(self) -> None:
        state = CoherenceState(S=0.7, gamma=0.9, E_obj=0.1, sigma2=2e-3)
        cfg = AblationConfig(regime=REGIME_ENERGY_ONLY, initial_state=state)
        assert cfg.initial_state.S == 0.7


# ── Single run ──────────────────────────────────────────────────────────


class TestSingleRun:
    def test_roles_only_produces_valid_trajectory(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_ROLES_ONLY, n_steps=50, n_seeds=1)
        result = study.run_single(cfg, seed=42)
        assert result.regime == REGIME_ROLES_ONLY
        assert result.trajectory.shape == (51, 4)
        assert 0.0 <= result.quality <= 1.0
        assert 0.0 <= result.delta_s_positive_frac <= 1.0
        assert result.compute_cost >= 0.0

    def test_energy_only_produces_valid_trajectory(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_ENERGY_ONLY, n_steps=50, n_seeds=1)
        result = study.run_single(cfg, seed=42)
        assert result.regime == REGIME_ENERGY_ONLY
        assert result.trajectory.shape == (51, 4)

    def test_hybrid_produces_valid_trajectory(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_HYBRID, n_steps=50, n_seeds=1)
        result = study.run_single(cfg, seed=42)
        assert result.regime == REGIME_HYBRID
        assert result.trajectory.shape == (51, 4)

    def test_deterministic_given_same_seed(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_HYBRID, n_steps=50, n_seeds=1)
        r1 = study.run_single(cfg, seed=99)
        r2 = study.run_single(cfg, seed=99)
        np.testing.assert_array_equal(r1.trajectory, r2.trajectory)
        assert r1.quality == r2.quality

    def test_different_seeds_differ(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_ENERGY_ONLY, n_steps=50, n_seeds=1)
        r1 = study.run_single(cfg, seed=0)
        r2 = study.run_single(cfg, seed=1)
        assert not np.array_equal(r1.trajectory, r2.trajectory)

    def test_custom_energy_gain_schedule(self) -> None:
        gains = tuple(0.1 for _ in range(50))
        cfg = AblationConfig(
            regime=REGIME_ENERGY_ONLY,
            n_steps=50,
            n_seeds=1,
            energy_gain_schedule=gains,
        )
        study = AblationStudy()
        result = study.run_single(cfg, seed=42)
        assert result.trajectory.shape == (51, 4)

    def test_short_gain_schedule_padded(self) -> None:
        """Gain schedule shorter than n_steps is edge-padded."""
        gains = (0.1, 0.2, 0.3)
        cfg = AblationConfig(
            regime=REGIME_ENERGY_ONLY,
            n_steps=50,
            n_seeds=1,
            energy_gain_schedule=gains,
        )
        study = AblationStudy()
        result = study.run_single(cfg, seed=42)
        assert result.trajectory.shape == (51, 4)


# ── Multi-seed aggregation ──────────────────────────────────────────────


class TestAggregation:
    def test_run_config_returns_correct_count(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_ROLES_ONLY, n_steps=30, n_seeds=5, base_seed=10)
        results = study.run_config(cfg)
        assert len(results) == 5
        assert all(r.regime == REGIME_ROLES_ONLY for r in results)
        seeds = [r.seed for r in results]
        assert seeds == [10, 11, 12, 13, 14]

    def test_summarize_produces_valid_metrics(self) -> None:
        study = AblationStudy()
        cfg = AblationConfig(regime=REGIME_ENERGY_ONLY, n_steps=30, n_seeds=5)
        results = study.run_config(cfg)
        summary = study.summarize(results)
        assert summary.regime == REGIME_ENERGY_ONLY
        assert summary.n_runs == 5
        assert 0.0 <= summary.quality_mean <= 1.0
        assert summary.quality_std >= 0.0
        assert summary.cost_mean >= 0.0
        # Pareto point tuple
        q, rob, c = summary.pareto_point
        assert 0.0 <= q <= 1.0
        assert 0.0 <= rob <= 1.0
        assert c >= 0.0

    def test_summarize_rejects_empty(self) -> None:
        study = AblationStudy()
        with pytest.raises(ValueError, match="empty"):
            study.summarize([])


# ── Full study ──────────────────────────────────────────────────────────


class TestFullStudy:
    def test_run_all_returns_complete_report(self) -> None:
        study = AblationStudy()
        report = study.run_all(n_steps=30, n_seeds=3, base_seed=0)
        assert isinstance(report, AblationReport)
        assert len(report.summaries) == 3
        assert len(report.all_results) == 9  # 3 regimes × 3 seeds
        regimes = {s.regime for s in report.summaries}
        assert regimes == set(ALL_REGIMES)
        assert report.dominant_regime in ALL_REGIMES

    def test_summary_for_lookup(self) -> None:
        study = AblationStudy()
        report = study.run_all(n_steps=30, n_seeds=3)
        for regime in ALL_REGIMES:
            s = report.summary_for(regime)
            assert s.regime == regime

    def test_summary_for_missing_raises(self) -> None:
        study = AblationStudy()
        report = study.run_all(n_steps=30, n_seeds=3)
        with pytest.raises(KeyError):
            report.summary_for("nonexistent")

    def test_energy_regime_has_higher_cost_than_roles(self) -> None:
        """Energy-based control injects E_obj actively → higher cost."""
        study = AblationStudy()
        report = study.run_all(n_steps=100, n_seeds=5, base_seed=42)
        roles = report.summary_for(REGIME_ROLES_ONLY)
        energy = report.summary_for(REGIME_ENERGY_ONLY)
        # Energy regime should have measurably higher compute cost
        # because it actively injects objection energy.
        assert energy.cost_mean > roles.cost_mean

    def test_hybrid_quality_at_least_as_good_as_roles(self) -> None:
        """Hybrid (energy + roles) should not degrade below roles-only."""
        study = AblationStudy()
        report = study.run_all(n_steps=100, n_seeds=10, base_seed=0)
        roles = report.summary_for(REGIME_ROLES_ONLY)
        hybrid = report.summary_for(REGIME_HYBRID)
        # Hybrid has energy control → should maintain or improve quality.
        # Allow small tolerance for stochastic noise.
        assert hybrid.quality_mean >= roles.quality_mean - 0.15
