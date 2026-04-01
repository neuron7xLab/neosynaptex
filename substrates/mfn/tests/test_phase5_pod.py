"""Phase 5 POD+Galerkin tests — PDE->ODE reduction for viability certification.

# EVIDENCE TYPE: numerical verification on synthetic contracting dynamics
# IMPLEMENTED TRUTH: POD via SVD (Sirovich 1987), Galerkin projection (Holmes 2012)
# APPROXIMATION: truncated modal expansion, not exact PDE
# REMAINING THEORETICAL GAP: formal SOS requires analytical PDE->polynomial reduction

Ref: Vasylenko (2026), Sirovich (1987), Holmes et al. (2012), Aubin (1991)
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.tau_control import (
    CertifiedEllipsoid,
    CertifiedViabilityV3,
    CertifiedViabilityV4,
    GalerkinODE,
    MFNSnapshot,
    PODProjector,
    PolynomialDynamicsApproximator,
)

# ── Shared trajectory fixtures ────────────────────────────────


def _make_contracting_trajectory(
    d: int = 8, n: int = 100, contraction: float = 0.92, seed: int = 42,
) -> list[MFNSnapshot]:
    """Contracting linear dynamics with noise: x_{t+1} = c*x_t + eps."""
    rng = np.random.default_rng(seed)
    snapshots = []
    x = rng.normal(0, 1, d)
    A = contraction * np.eye(d) + 0.03 * rng.standard_normal((d, d))
    for _ in range(n):
        snapshots.append(MFNSnapshot(state_vector=x.copy()))
        x = A @ x + rng.normal(0, 0.02, d)
    return snapshots


def _make_oscillatory_trajectory(
    d: int = 6, n: int = 80, seed: int = 7,
) -> list[MFNSnapshot]:
    """Oscillatory + decaying dynamics."""
    rng = np.random.default_rng(seed)
    snapshots = []
    x = rng.normal(0, 2, d)
    theta = 0.3
    R = np.eye(d)
    R[0, 0], R[0, 1] = np.cos(theta), -np.sin(theta)
    R[1, 0], R[1, 1] = np.sin(theta), np.cos(theta)
    for _ in range(n):
        snapshots.append(MFNSnapshot(state_vector=x.copy()))
        x = 0.93 * R @ x + rng.normal(0, 0.1, d)
    return snapshots


@pytest.fixture(scope="module")
def contracting() -> list[MFNSnapshot]:
    return _make_contracting_trajectory()


@pytest.fixture(scope="module")
def oscillatory() -> list[MFNSnapshot]:
    return _make_oscillatory_trajectory()


# ── POD tests ─────────────────────────────────────────────────


class TestPOD:
    def test_energy_threshold(self, contracting) -> None:
        """POD captures >= 99% energy with r modes, r <= d."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        assert pod.energy_captured() >= 0.99
        assert pod.r <= 8  # d=8
        assert pod.r > 0

    def test_projection_reconstruction(self, contracting) -> None:
        """Mean relative reconstruction error < 50%."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        err = pod.projection_error(contracting)
        assert err < 0.5, f"Reconstruction error {err:.4f} too high"

    def test_project_reconstruct_roundtrip(self, contracting) -> None:
        """Project then reconstruct preserves shape."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        x = np.asarray(contracting[50].state_vector, dtype=np.float64)
        a = pod.project(x)
        x_r = pod.reconstruct(a)
        assert a.shape == (pod.r,)
        assert x_r.shape == x.shape

    def test_minimum_snapshots(self) -> None:
        """Fewer than 10 snapshots raises ValueError."""
        pod = PODProjector()
        few = [MFNSnapshot(state_vector=np.zeros(4)) for _ in range(5)]
        with pytest.raises(ValueError, match="Need >= 10"):
            pod.fit(few)


# ── Galerkin ODE tests ────────────────────────────────────────


class TestGalerkin:
    def test_fit_error_finite_and_small(self, contracting) -> None:
        """Galerkin modal fit error is finite and < 0.01.

        Note: polynomial proxy may have lower fit error in full space (more
        parameters) but diverges at boundary. Galerkin advantage is stability,
        not raw fit accuracy.
        # EVIDENCE TYPE: numerical on synthetic trajectory
        """
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        assert gal.fit_error < 0.01, f"Galerkin fit error {gal.fit_error:.6f} too high"
        assert np.isfinite(gal.fit_error)

    def test_spectral_radius_contracting(self, contracting) -> None:
        """Spectral radius rho(A) < 1 for contracting dynamics."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        rho = gal.spectral_radius()
        assert rho < 1.0, f"rho(A) = {rho:.4f}, not contracting"

    def test_predict_modal_shape(self, contracting) -> None:
        """predict_modal returns vector of size r."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        a = pod.project(np.asarray(contracting[0].state_vector, dtype=np.float64))
        a_next = gal.predict_modal(a)
        assert a_next.shape == (pod.r,)
        assert np.all(np.isfinite(a_next))


# ── Modal ellipsoid tests ────────────────────────────────────


class TestModalEllipsoid:
    def test_positive_definite(self, contracting) -> None:
        """Modal ellipsoid P_a has all eigenvalues > 0."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        v4 = CertifiedViabilityV4(pod, gal)
        v4.fit_modal_ellipsoid(contracting)

        summary = v4.modal_ellipsoid.certificate_summary()
        assert summary["min_eigenvalue"] > 0
        assert summary["certificate_valid"]


# ── SOS comparison V3 vs V4 ──────────────────────────────────


class TestSOSComparison:
    def test_v4_fewer_violations_than_v3(self, contracting) -> None:
        """V4 modal SOS violation rate < V3 polynomial SOS violation rate.

        V3 baseline: 56.5% violations (Phase 4).
        V4 target: < 20% violations.

        # EVIDENCE TYPE: numerical comparison, same trajectory
        """
        # V4
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        v4 = CertifiedViabilityV4(pod, gal)
        v4.fit_modal_ellipsoid(contracting)
        sos4 = v4.sos_modal_check(n_boundary=300)

        # V3
        data = np.array([s.state_vector for s in contracting])
        ce = CertifiedEllipsoid.from_data(data, 0.95)
        pda = PolynomialDynamicsApproximator().fit(contracting, degree=2)
        v3 = CertifiedViabilityV3(ce, pda)
        sos3 = v3.sos_verify_invariance()

        assert sos4["violation_rate"] < sos3["violation_rate"], (
            f"V4 ({sos4['violation_rate']}) not better than V3 ({sos3['violation_rate']})"
        )
        assert sos4["violation_rate"] < 0.20, (
            f"V4 violation rate {sos4['violation_rate']} >= 0.20"
        )

    def test_v4_empirical_on_oscillatory(self, oscillatory) -> None:
        """V4 achieves EMPIRICAL or PARTIAL on oscillatory dynamics."""
        pod = PODProjector(energy_threshold=0.99).fit(oscillatory)
        gal = GalerkinODE(order=1).fit(oscillatory, pod)
        v4 = CertifiedViabilityV4(pod, gal)
        v4.fit_modal_ellipsoid(oscillatory)
        sos = v4.sos_modal_check(n_boundary=300)
        assert sos["sos_status"] in ("EMPIRICAL", "PARTIAL"), (
            f"Expected EMPIRICAL or PARTIAL, got {sos['sos_status']} "
            f"(violations={sos['violation_rate']})"
        )


# ── Recovery trajectory V4 ───────────────────────────────────


class TestRecoveryV4:
    def test_center_recovers_immediately(self, contracting) -> None:
        """Center of operational data is viable at step 0."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        v4 = CertifiedViabilityV4(pod, gal)
        v4.fit_modal_ellipsoid(contracting)

        reached, reason = v4.has_recovery_trajectory_v4(pod.mean)
        assert reached, f"Center not viable: {reason}"
        assert "step_0" in reason


# ── End-to-end pipeline ──────────────────────────────────────


class TestEndToEnd:
    def test_full_v4_pipeline(self, contracting) -> None:
        """Full pipeline: fit POD -> fit Galerkin -> fit ellipsoid -> check SOS."""
        pod = PODProjector(energy_threshold=0.99).fit(contracting)
        gal = GalerkinODE(order=1).fit(contracting, pod)
        v4 = CertifiedViabilityV4(pod, gal, horizon=20)
        v4.fit_modal_ellipsoid(contracting)

        # All components fitted
        assert pod.is_fitted
        assert gal.is_fitted
        assert v4.modal_ellipsoid is not None

        # Modal viability check works
        assert v4.is_viable_modal(pod.mean)

        # SOS produces valid result
        sos = v4.sos_modal_check()
        assert "sos_status" in sos
        assert isinstance(sos["violation_rate"], float)
        assert sos["n_boundary_pts"] > 0
