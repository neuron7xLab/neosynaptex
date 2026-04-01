"""Discriminant v3 — precision strike tests on pressure classification trust.

Metrics computed:
  ECE, Brier score, noise FPR, collapse recall, transformation trigger rate.

# CALIBRATION: synthetic labels only, not real operational data.
# PROOF TYPE: empirical/synthetic, not analytical.
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.tau_control import (
    CalibrationResult,
    Discriminant,
    DiscriminantResult,
    IdentityEngine,
    NormSpace,
    PressureKind,
    TrajectoryDiscriminant,
)

# ── Synthetic trajectory generators ─────────────────────────────


def _synth_operational(n: int = 300, seed: int = 42) -> list[dict[str, float]]:
    """Low pressure, stable, high coherence."""
    rng = np.random.default_rng(seed)
    return [
        {"phi": rng.uniform(0, 0.5), "phi_trend": rng.normal(0, 0.1),
         "failure_density": rng.uniform(0, 0.1), "coherence": rng.uniform(0.6, 1.0),
         "steps_in_bad": float(rng.integers(0, 5))}
        for _ in range(n)
    ]


def _synth_existential(n: int = 300, seed: int = 43) -> list[dict[str, float]]:
    """High pressure, rising trend, low coherence."""
    rng = np.random.default_rng(seed)
    return [
        {"phi": rng.uniform(2.0, 8.0), "phi_trend": rng.uniform(0.1, 1.0),
         "failure_density": rng.uniform(0.3, 0.9), "coherence": rng.uniform(0.0, 0.3),
         "steps_in_bad": float(rng.integers(10, 50))}
        for _ in range(n)
    ]


def _synth_ambiguous(n: int = 100, seed: int = 44) -> list[dict[str, float]]:
    """Borderline cases near decision boundary."""
    rng = np.random.default_rng(seed)
    return [
        {"phi": rng.uniform(0.8, 2.5), "phi_trend": rng.normal(0.05, 0.15),
         "failure_density": rng.uniform(0.1, 0.3), "coherence": rng.uniform(0.3, 0.6),
         "steps_in_bad": float(rng.integers(3, 15))}
        for _ in range(n)
    ]


# ── Calibration metrics ─────────────────────────────────────────


class TestCalibrationMetrics:
    def test_calibration_produces_all_metrics(self) -> None:
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(300), _synth_existential(300))
        assert isinstance(result, CalibrationResult)
        assert hasattr(result, "ece")
        assert hasattr(result, "brier")
        assert hasattr(result, "noise_fpr")
        assert hasattr(result, "collapse_recall")

    def test_ece_below_threshold(self) -> None:
        """# CALIBRATION: synthetic labels only."""
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(500), _synth_existential(500))
        assert result.ece < 0.15, f"ECE={result.ece}"

    def test_brier_below_threshold(self) -> None:
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(500), _synth_existential(500))
        assert result.brier < 0.10, f"Brier={result.brier}"

    def test_noise_fpr_low(self) -> None:
        """Operational data should rarely trigger existential."""
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(500), _synth_existential(500))
        assert result.noise_fpr < 0.05, f"Noise FPR={result.noise_fpr}"

    def test_collapse_recall_high(self) -> None:
        """Existential data should be caught."""
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(500), _synth_existential(500))
        assert result.collapse_recall > 0.90, f"Recall={result.collapse_recall}"


# ── DiscriminantResult structure ─────────────────────────────────


class TestDiscriminantResult:
    def test_returns_structured_result(self) -> None:
        d = Discriminant(min_consecutive_existential=1)
        ns = NormSpace(np.zeros(4), np.eye(4))
        result = d.classify_detailed(
            phi=0.1, tau=3.0, x=np.zeros(4), norm=ns,
            phase_is_collapsing=False, coherence=0.9,
        )
        assert isinstance(result, DiscriminantResult)
        assert isinstance(result.pressure, PressureKind)
        assert 0.0 <= result.probability_existential <= 1.0
        assert 0.0 <= result.uncertainty <= 1.0
        assert isinstance(result.explanation, str)

    def test_backward_compatible_classify(self) -> None:
        d = Discriminant()
        ns = NormSpace(np.zeros(4), np.eye(4))
        result = d.classify(phi=0.1, tau=3.0, x=np.zeros(4), norm=ns,
                            phase_is_collapsing=False, coherence=0.9)
        assert isinstance(result, PressureKind)


# ── Uncertainty gate ─────────────────────────────────────────────


class TestUncertaintyGate:
    def test_ambiguous_defaults_to_operational(self) -> None:
        """Ambiguous inputs should not trigger EXISTENTIAL."""
        td = TrajectoryDiscriminant(uncertainty_threshold=0.4)
        td.calibrate(_synth_operational(300), _synth_existential(300))

        ambiguous = _synth_ambiguous(50)
        existential_count = 0
        for sample in ambiguous:
            kind, _prob, _unc = td.classify(
                sample["phi"], sample["phi_trend"], sample["failure_density"],
                sample["coherence"], int(sample["steps_in_bad"]),
            )
            if kind == PressureKind.EXISTENTIAL:
                existential_count += 1

        # Most ambiguous should NOT be existential
        rate = existential_count / len(ambiguous)
        assert rate < 0.50, f"Ambiguous existential rate={rate:.2f} (should be < 0.50)"


# ── Hard guard ───────────────────────────────────────────────────


class TestHardGuard:
    def test_sustained_collapse_triggers_hard_guard(self) -> None:
        d = Discriminant(
            min_consecutive_existential=3,
            hard_guard_consecutive=5,
            coherence_critical=0.15,
        )
        ns = NormSpace(np.zeros(4), np.eye(4))

        # 5+ consecutive collapses with critical coherence
        for _ in range(6):
            result = d.classify_detailed(
                phi=0.1, tau=99.0, x=np.zeros(4), norm=ns,
                phase_is_collapsing=True, coherence=0.1,
            )
        assert result.hard_guard_triggered
        assert result.pressure == PressureKind.EXISTENTIAL

    def test_no_hard_guard_without_sustained_collapse(self) -> None:
        d = Discriminant(hard_guard_consecutive=5)
        ns = NormSpace(np.zeros(4), np.eye(4))

        result = d.classify_detailed(
            phi=0.1, tau=99.0, x=np.zeros(4), norm=ns,
            phase_is_collapsing=True, coherence=0.1,
        )
        assert not result.hard_guard_triggered


# ── Hysteresis ───────────────────────────────────────────────────


class TestHysteresis:
    def test_single_existential_blocked(self) -> None:
        d = Discriminant(min_consecutive_existential=3)
        ns = NormSpace(np.zeros(4), np.eye(4))

        result = d.classify_detailed(
            phi=10.0, tau=3.0, x=np.zeros(4), norm=ns,
            phase_is_collapsing=False, coherence=0.9,
        )
        assert result.hysteresis_blocked
        assert result.pressure == PressureKind.OPERATIONAL

    def test_consecutive_existential_passes(self) -> None:
        d = Discriminant(min_consecutive_existential=3)
        ns = NormSpace(np.zeros(4), np.eye(4))

        for _ in range(3):
            result = d.classify_detailed(
                phi=10.0, tau=3.0, x=np.zeros(4), norm=ns,
                phase_is_collapsing=False, coherence=0.9,
            )
        assert not result.hysteresis_blocked
        assert result.pressure == PressureKind.EXISTENTIAL

    def test_hysteresis_counter_decays(self) -> None:
        """Counter decays instead of hard reset."""
        d = Discriminant(min_consecutive_existential=3)
        ns = NormSpace(np.zeros(4), np.eye(4))

        # Build up 2 existential
        for _ in range(2):
            d.classify_detailed(phi=10.0, tau=3.0, x=np.zeros(4), norm=ns,
                                phase_is_collapsing=False, coherence=0.9)

        # One operational — decays by 1 instead of reset
        d.classify_detailed(phi=0.0, tau=99.0, x=np.zeros(4), norm=ns,
                            phase_is_collapsing=False, coherence=0.9)

        # Should need 2 more to reach threshold (counter decayed to 1)
        for _ in range(2):
            result = d.classify_detailed(phi=10.0, tau=3.0, x=np.zeros(4), norm=ns,
                                         phase_is_collapsing=False, coherence=0.9)
        assert result.pressure == PressureKind.EXISTENTIAL


# ── Integration: IdentityEngine ──────────────────────────────────


class TestIdentityEngineIntegration:
    def test_noisy_operational_no_transforms(self) -> None:
        """Noisy operational trajectory should not trigger transformation."""
        engine = IdentityEngine(state_dim=4)
        rng = np.random.default_rng(42)

        for _ in range(500):
            engine.process(
                state_vector=rng.normal(0, 3.0, 4),
                free_energy=0.1 + rng.normal(0, 0.01),
                phase_is_collapsing=False,
                coherence=0.9,
                recovery_succeeded=True,
            )

        assert engine.transform.transform_count == 0

    def test_sustained_collapse_triggers_transform(self) -> None:
        """Sustained collapse should eventually trigger transformation."""
        engine = IdentityEngine(state_dim=4, collapse_k_max=2)
        engine.discriminant.min_consecutive_existential = 1

        rng = np.random.default_rng(42)
        for i in range(200):
            engine.process(
                state_vector=rng.normal(0, 1.0, 4),
                free_energy=1.0 + i * 0.05,
                phase_is_collapsing=True,
                coherence=0.1,
                recovery_succeeded=False,
            )

        assert engine.transform.transform_count >= 1

    def test_no_gamma_in_discriminant(self) -> None:
        import inspect
        sig = inspect.signature(Discriminant.classify)
        for name in sig.parameters:
            assert "gamma" not in name.lower()
        sig2 = inspect.signature(Discriminant.classify_detailed)
        for name in sig2.parameters:
            assert "gamma" not in name.lower()


# ── Evidence bundle ──────────────────────────────────────────────


class TestEvidenceBundle:
    def test_full_metrics_report(self) -> None:
        """Compute and report all discriminant quality metrics."""
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(500), _synth_existential(500))

        print("\n  DISCRIMINANT EVIDENCE BUNDLE")
        print(f"  ECE:             {result.ece:.4f}")
        print(f"  Brier:           {result.brier:.4f}")
        print(f"  Accuracy:        {result.accuracy:.4f}")
        print(f"  Noise FPR:       {result.noise_fpr:.4f}")
        print(f"  Collapse recall: {result.collapse_recall:.4f}")
        print(f"  Method:          {result.ece_method}")
        print(f"  N synthetic:     {result.n_synthetic}")

        # All targets
        assert result.ece < 0.15
        assert result.brier < 0.10
        assert result.noise_fpr < 0.05
        assert result.collapse_recall > 0.90
        assert result.accuracy > 0.90
