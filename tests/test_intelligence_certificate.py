"""Tests for core.intelligence_certificate — proof-of-intelligence artifact."""

from __future__ import annotations

import json

import numpy as np
import pytest

from core.coherence_state_space import CoherenceState, CoherenceStateSpace
from core.intelligence_certificate import (
    IntelligenceCertificate,
    certify,
    verify_certificate,
)


def _living_trajectory(n: int = 200, seed: int = 42) -> np.ndarray:
    """Generate a living trajectory from CoherenceStateSpace."""
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.4, gamma=1.05, E_obj=0.05, sigma2=1e-3)
    return model.rollout(x0, n_steps=n, rng=np.random.default_rng(seed))


def _dead_trajectory(n: int = 200) -> np.ndarray:
    """Constant flatline → dead equilibrium."""
    return np.ones((n, 4)) * 0.5


class TestCertifyLiving:
    def test_returns_certificate(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        assert isinstance(cert, IntelligenceCertificate)
        assert cert.version == "1.0.0"

    def test_living_system_certified(self) -> None:
        traj = _living_trajectory(300, seed=7)
        cert = certify(traj, dt=0.1)
        assert cert.verdict in ("CERTIFIED", "INCONCLUSIVE")
        assert cert.gradient_diagnosis in ("living_gradient", "transient")

    def test_seal_intact(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        assert verify_certificate(cert) is True

    def test_trajectory_hash_deterministic(self) -> None:
        traj = _living_trajectory(seed=99)
        c1 = certify(traj, dt=0.1)
        c2 = certify(traj, dt=0.1)
        assert c1.trajectory_sha256 == c2.trajectory_sha256

    def test_expelliarmus_tested(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        assert isinstance(cert.expelliarmus_resilient, bool)
        assert cert.expelliarmus_recovery_time >= 0

    def test_mathematical_depth_populated(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        assert cert.renyi_shannon > 0
        assert cert.fisher_info > 0
        assert isinstance(cert.lyapunov_is_chaotic, bool)


class TestCertifyDead:
    def test_dead_system_denied(self) -> None:
        traj = _dead_trajectory()
        cert = certify(traj, dt=0.1)
        assert cert.verdict == "DENIED"
        assert "violated" in cert.reason.lower() or "disarmed" in cert.reason.lower()

    def test_dead_gradient_diagnosis(self) -> None:
        traj = _dead_trajectory()
        cert = certify(traj, dt=0.1)
        assert cert.gradient_diagnosis in ("dead_equilibrium", "static_capacitor")


class TestSerialization:
    def test_json_roundtrip(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        j = cert.to_json()
        restored = IntelligenceCertificate.from_json(j)
        assert restored.certificate_sha256 == cert.certificate_sha256
        assert restored.verdict == cert.verdict

    def test_json_is_valid(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        parsed = json.loads(cert.to_json())
        assert "verdict" in parsed
        assert "certificate_sha256" in parsed


class TestVerification:
    def test_tampered_cert_fails(self) -> None:
        traj = _living_trajectory()
        cert = certify(traj, dt=0.1)
        # Tamper with verdict
        d = json.loads(cert.to_json())
        d["verdict"] = "CERTIFIED"  # force certified
        tampered = IntelligenceCertificate(**d)
        # If verdict was already CERTIFIED, tamper with gamma
        if cert.verdict == "CERTIFIED":
            d["gamma_mean"] = 999.0
            tampered = IntelligenceCertificate(**d)
        assert verify_certificate(tampered) is False


class TestEdgeCases:
    def test_short_trajectory_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 20"):
            certify(np.zeros((10, 4)))

    def test_1d_input_handled(self) -> None:
        """1-D signal auto-expanded to (T, 1)."""
        x = np.random.default_rng(0).normal(1.0, 0.1, size=100)
        cert = certify(x, dt=1.0, gamma_column=0)
        assert cert.trajectory_dim == 1
