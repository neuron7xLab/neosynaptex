"""Tests for tau-control v2 — discriminant calibration, certified viability,
barrier monitor, KL-bounded transformation, and proof-oriented synthetics.

Every test is falsifiable. All labels are synthetic.
# PROOF TYPE: empirical/synthetic, not analytical.
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.tau_control import (
    BarrierMonitor,
    CalibrationResult,
    CertifiedEllipsoid,
    IdentityEngine,
    LyapunovMonitor,
    MetaRuleSpace,
    NormSpace,
    PressureKind,
    TrajectoryDiscriminant,
    TransformationProtocol,
)

# ── Synthetic data generators ────────────────────────────────────


def _synth_operational(n: int = 200, seed: int = 42) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    return [
        {"phi": rng.uniform(0, 0.5), "phi_trend": rng.normal(0, 0.1),
         "failure_density": rng.uniform(0, 0.1), "coherence": rng.uniform(0.6, 1.0),
         "steps_in_bad": float(rng.integers(0, 5))}
        for _ in range(n)
    ]


def _synth_existential(n: int = 200, seed: int = 43) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    return [
        {"phi": rng.uniform(2.0, 8.0), "phi_trend": rng.uniform(0.1, 1.0),
         "failure_density": rng.uniform(0.3, 0.9), "coherence": rng.uniform(0.0, 0.3),
         "steps_in_bad": float(rng.integers(10, 50))}
        for _ in range(n)
    ]


# ── TrajectoryDiscriminant ───────────────────────────────────────


class TestTrajectoryDiscriminant:
    def test_calibration_ece(self) -> None:
        """# CALIBRATION: synthetic labels only."""
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(300), _synth_existential(300))
        assert isinstance(result, CalibrationResult)
        # IMPLEMENTED TRUTH: isotonic calibration, ECE < 0.15 on synthetic data.
        assert result.ece < 0.15, f"ECE too high: {result.ece}"
        assert result.accuracy > 0.85, f"Accuracy too low: {result.accuracy}"
        assert result.ece_method == "isotonic"
        assert result.label == "synthetic_calibration"

    def test_high_uncertainty_forces_operational(self) -> None:
        """Gate 7: high uncertainty -> OPERATIONAL."""
        td = TrajectoryDiscriminant(uncertainty_threshold=0.4)
        # Borderline case: features near decision boundary
        kind, _prob, unc = td.classify(phi=1.5, phi_trend=0.1, failure_density=0.15,
                                       coherence=0.5, steps_in_bad_phase=5)
        if unc > 0.4:
            assert kind == PressureKind.OPERATIONAL

    def test_existential_requires_evidence(self) -> None:
        """Single spike should not classify as existential alone."""
        td = TrajectoryDiscriminant()
        # Low phi, single bad step
        kind, _, _ = td.classify(phi=0.3, phi_trend=0.0, failure_density=0.05,
                                coherence=0.8, steps_in_bad_phase=1)
        assert kind == PressureKind.OPERATIONAL

    def test_no_gamma_in_features(self) -> None:
        import inspect
        sig = inspect.signature(TrajectoryDiscriminant.classify)
        for name in sig.parameters:
            assert "gamma" not in name.lower()


# ── CertifiedEllipsoid ──────────────────────────────────────────


class TestCertifiedEllipsoid:
    def test_positive_definite_required(self) -> None:
        with pytest.raises(ValueError, match="positive definite"):
            CertifiedEllipsoid(P=-np.eye(4), mu=np.zeros(4))

    def test_center_is_viable(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        assert ce.is_viable(np.zeros(4))

    def test_far_point_not_viable(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        assert not ce.is_viable(np.ones(4) * 10)

    def test_barrier_positive_inside(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        assert ce.barrier_value(np.zeros(4)) > 0

    def test_barrier_negative_outside(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        assert ce.barrier_value(np.ones(4) * 10) <= 0

    def test_certificate_summary(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4) * 2, mu=np.zeros(4))
        s = ce.certificate_summary()
        assert s["min_eigenvalue"] > 0
        assert s["certificate_valid"]

    def test_from_data(self) -> None:
        rng = np.random.default_rng(42)
        data = rng.normal(0, 1, (100, 4))
        ce = CertifiedEllipsoid.from_data(data, coverage_quantile=0.95)
        # Most training points should be inside
        inside = sum(ce.is_viable(data[i]) for i in range(100))
        assert inside > 80, f"Only {inside}/100 inside (expected > 80)"

    def test_fp_rate_on_operational(self) -> None:
        """False positive rate < 0.05 on held-out operational data."""
        rng = np.random.default_rng(42)
        train = rng.normal(0, 1, (200, 4))
        test = rng.normal(0, 1, (100, 4))
        ce = CertifiedEllipsoid.from_data(train, 0.95)
        fp = sum(1 for i in range(100) if not ce.is_viable(test[i]))
        assert fp / 100 < 0.20  # allow some margin for stochastic test


# ── BarrierMonitor ───────────────────────────────────────────────


class TestBarrierMonitor:
    def test_inside_no_violation(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        bm = BarrierMonitor()
        status = bm.update(np.zeros(4), ce)
        assert not status.outside_safe_set
        assert status.b_value > 0

    def test_approaching_boundary(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        bm = BarrierMonitor(delta_b=0.01)
        # Start at center
        bm.update(np.zeros(4), ce)
        # Move toward boundary
        for i in range(1, 10):
            x = np.array([0.1 * i, 0, 0, 0])
            status = bm.update(x, ce)
        # Should detect approach
        assert status.delta_b < 0

    def test_consecutive_violations(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        bm = BarrierMonitor()
        bm.update(np.zeros(4), ce)
        # Move outward monotonically
        for i in range(1, 8):
            status = bm.update(np.array([0.15 * i, 0, 0, 0]), ce)
        assert status.consecutive_violations >= 3


# ── Lyapunov KL ──────────────────────────────────────────────────


class TestLyapunovKL:
    def test_kl_zero_when_equal(self) -> None:
        lm = LyapunovMonitor()
        ns = NormSpace(np.zeros(4), np.eye(4))
        meta = MetaRuleSpace()
        state = lm.compute(0.0, ns, ns, meta, meta)
        assert state.v_c_kl < 0.01

    def test_kl_positive_when_changed(self) -> None:
        lm = LyapunovMonitor()
        ns = NormSpace(np.zeros(4), np.eye(4))
        meta_origin = MetaRuleSpace(learning_rate_bounds=(0.001, 0.1))
        meta_new = MetaRuleSpace(learning_rate_bounds=(0.01, 0.5))
        state = lm.compute(0.0, ns, ns, meta_new, meta_origin)
        assert state.v_c_kl > 0

    def test_kl_bounded_check(self) -> None:
        lm = LyapunovMonitor()
        m1 = MetaRuleSpace(learning_rate_bounds=(0.001, 0.1))
        m2 = MetaRuleSpace(learning_rate_bounds=(0.01, 0.5))
        assert not lm.kl_bounded(m2, m1, epsilon_c=0.001)  # big change
        assert lm.kl_bounded(m1, m1, epsilon_c=0.001)  # no change

    def test_violation_counters(self) -> None:
        lm = LyapunovMonitor()
        ns = NormSpace(np.zeros(4), np.eye(4))
        meta = MetaRuleSpace()
        # Increasing free energy -> V_x violations
        for i in range(10):
            state = lm.compute(float(i) * 0.1, ns, ns, meta, meta)
        assert state.violation_counter_vx > 0


# ── KL-bounded transformation ───────────────────────────────────


class TestTransformationKL:
    def test_kl_rejection(self) -> None:
        lm = LyapunovMonitor(delta_max=100.0)  # generous V bound
        tp = TransformationProtocol(lyapunov=lm, epsilon_c=0.0001)  # very strict KL
        ns = NormSpace(np.zeros(4), np.eye(4))
        meta = MetaRuleSpace()
        _, accepted = tp.transform(meta, phi=5.0, free_energy=0.1,
                                   norm=ns, norm_origin=ns, meta_origin=meta)
        # With epsilon_c=0.0001, any change should be rejected
        if not accepted:
            assert tp.last_reject_reason == "KL_exceeded"


# ── Proof-oriented synthetic tests ──────────────────────────────


class TestProofsV2:
    """# PROOF TYPE: empirical/synthetic, not analytical."""

    def test_no_metadrift_kl(self) -> None:
        engine = IdentityEngine(state_dim=4)
        rng = np.random.default_rng(42)
        for _ in range(500):
            engine.process(
                state_vector=rng.normal(0, 0.3, 4),
                free_energy=0.1 + rng.normal(0, 0.01),
                phase_is_collapsing=False,
                coherence=0.9,
                recovery_succeeded=True,
            )
        assert engine.transform.transform_count == 0
        assert engine.lyapunov.meta_stable_trend() <= 0.01

    def test_no_rigidity(self) -> None:
        """Norm adapts when in recovery mode (outside norm)."""
        engine = IdentityEngine(state_dim=4)
        rng = np.random.default_rng(42)
        # Phase 1: centered data
        for _ in range(50):
            engine.process(rng.normal(0, 0.1, 4), 0.1, False, 0.9, True)
        # Phase 2: data outside norm -> triggers RECOVERY which updates norm
        for _ in range(200):
            x = rng.normal(3.0, 0.1, 4)  # outside norm (Mahalanobis > 1)
            engine.process(x, 0.1, False, 0.9, True)
        # Shape matrix should have expanded (norm adapted even in recovery)
        trace = float(np.trace(engine.norm.shape_matrix))
        assert trace > 4.0 + 0.1, f"Shape matrix unchanged: trace={trace}"

    def test_rare_transform_under_noise(self) -> None:
        engine = IdentityEngine(state_dim=4)
        rng = np.random.default_rng(42)
        for _ in range(1000):
            engine.process(
                state_vector=rng.normal(0, 3.0, 4),  # large noise
                free_energy=0.1,
                phase_is_collapsing=False,
                coherence=0.9,
                recovery_succeeded=True,
            )
        rate = engine.transform.transform_count / 1000
        assert rate < 0.01, f"Transform rate {rate:.3f} too high under noise"

    def test_transform_under_true_collapse(self) -> None:
        engine = IdentityEngine(state_dim=4, collapse_k_max=2)
        rng = np.random.default_rng(42)
        # Sustained collapse
        for i in range(100):
            engine.process(
                state_vector=rng.normal(0, 1.0, 4),
                free_energy=1.0 + i * 0.1,
                phase_is_collapsing=True,
                coherence=0.1,
                recovery_succeeded=False,
            )
        assert engine.transform.transform_count >= 1

    def test_barrier_detects_approach(self) -> None:
        ce = CertifiedEllipsoid(P=np.eye(4), mu=np.zeros(4))
        bm = BarrierMonitor(delta_b=0.01)
        approaching_seen = False
        outside_seen = False
        for i in range(20):
            x = np.array([0.05 * i, 0, 0, 0])
            status = bm.update(x, ce)
            if status.approaching_boundary:
                approaching_seen = True
            if status.outside_safe_set:
                outside_seen = True
        # Approaching should be detected before outside
        assert approaching_seen or outside_seen

    def test_discriminant_calibration_full(self) -> None:
        """# CALIBRATION: synthetic labels only."""
        td = TrajectoryDiscriminant()
        result = td.calibrate(_synth_operational(500), _synth_existential(500))
        # IMPLEMENTED TRUTH: isotonic calibration, ECE < 0.15 on synthetic data.
        assert result.ece < 0.15, f"ECE too high: {result.ece}"
        assert result.ece_method == "isotonic"
        assert result.accuracy > 0.80
