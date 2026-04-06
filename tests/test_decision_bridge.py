"""Tests for core.decision_bridge — unified analytical convergence."""

from __future__ import annotations

import numpy as np
import pytest

from core.decision_bridge import DecisionBridge, DecisionSnapshot


def _make_healthy_data(n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Generate phi_history and gamma_history for a healthy system."""
    rng = np.random.default_rng(42)
    phi = rng.normal(0, 0.1, size=(n, 4))
    gamma = 1.0 + rng.normal(0, 0.02, size=n)
    return phi, gamma


def _make_dead_data(n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Constant state → dead equilibrium."""
    phi = np.ones((n, 4)) * 0.5
    gamma = np.ones(n) * 1.0
    return phi, gamma


class TestConstruction:
    def test_default_bridge(self) -> None:
        bridge = DecisionBridge()
        assert bridge._oeb_gain == 0.05

    def test_reset(self) -> None:
        bridge = DecisionBridge()
        bridge._oeb_gain = 0.99
        bridge._oeb_energy = 0.01
        bridge.reset()
        assert bridge._oeb_gain == 0.05
        assert bridge._oeb_energy == 1.0


class TestEvaluateHealthy:
    def test_returns_snapshot(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.02,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert isinstance(snap, DecisionSnapshot)
        assert snap.tick == 20

    def test_healthy_system_optimal(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(30)
        snap = bridge.evaluate(
            tick=30,
            gamma_mean=1.01,
            gamma_std=0.02,
            spectral_radius=0.85,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.system_health == "OPTIMAL"
        assert snap.hallucination_risk == "low"
        assert snap.confidence > 0.5

    def test_operating_regime_detected(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.operating_regime in ("frozen", "critical", "chaotic")


class TestEvaluateDead:
    def test_dead_system(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_dead_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.0,
            spectral_radius=0.5,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.gradient_diagnosis == "dead_equilibrium"
        assert snap.system_health == "DEAD"

    def test_dead_has_zero_alive_frac(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_dead_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.0,
            spectral_radius=0.5,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.alive_frac < 0.1


class TestDegradation:
    def test_high_halluc_risk_degrades(self) -> None:
        bridge = DecisionBridge()
        # Declining gamma → coherence dropping → hallucination risk
        gamma = np.linspace(1.0, 0.5, 20)
        phi = np.random.default_rng(0).normal(size=(20, 4))
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=0.6,
            gamma_std=0.2,
            spectral_radius=1.3,
            phase="DIVERGING",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.hallucination_risk in ("moderate", "high")
        assert snap.system_health in ("DEGRADED", "CRITICAL")


class TestOEBDynamics:
    def test_oeb_gain_increases_under_risk(self) -> None:
        bridge = DecisionBridge()
        initial_gain = bridge._oeb_gain
        # High risk scenario
        gamma = np.linspace(1.0, 0.3, 20)
        phi = np.random.default_rng(0).normal(size=(20, 4))
        bridge.evaluate(
            tick=20,
            gamma_mean=0.4,
            gamma_std=0.3,
            spectral_radius=1.5,
            phase="DIVERGING",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert bridge._oeb_gain > initial_gain

    def test_oeb_energy_depletes(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        for t in range(50):
            bridge.evaluate(
                tick=t,
                gamma_mean=1.0,
                gamma_std=0.02,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
        assert bridge._oeb_energy < 1.0


class TestConfidence:
    def test_low_confidence_on_short_history(self) -> None:
        bridge = DecisionBridge()
        phi = np.random.default_rng(0).normal(size=(2, 4))
        gamma = np.array([1.0, 1.01])
        snap = bridge.evaluate(
            tick=2,
            gamma_mean=1.0,
            gamma_std=0.01,
            spectral_radius=0.9,
            phase="INITIALIZING",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.confidence < 0.5

    def test_full_confidence_on_long_history(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(30)
        snap = bridge.evaluate(
            tick=30,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.confidence >= 1.0


class TestFDT:
    def test_fdt_not_available_on_short_history(self) -> None:
        bridge = DecisionBridge()
        phi = np.random.default_rng(0).normal(size=(5, 4))
        gamma = np.array([1.0, 1.01, 1.02, 1.01, 1.0])
        snap = bridge.evaluate(
            tick=5,
            gamma_mean=1.0,
            gamma_std=0.01,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.gamma_fdt_available is False


class TestSnapshotImmutability:
    def test_frozen(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        with pytest.raises(AttributeError):
            snap.tick = 999  # type: ignore[misc]
