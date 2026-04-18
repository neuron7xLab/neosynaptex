"""Property-based tests for ``core.decision_bridge``.

Falsification battery: for every valid ingress, the bridge's contract
must hold. We don't test specific numbers — we test invariants that
should hold for *any* admissible input.

Contracts under test:
    I-DB-1  evaluate(valid input) never raises.
    I-DB-2  evaluate(non-finite input) always raises ValueError.
    I-DB-3  snapshot.critic_gain ∈ [0.01, 1.0] always.
    I-DB-4  snapshot.energy_remaining_frac ∈ [0.0, 1.0] always.
    I-DB-5  snapshot.controller_integral ∈ [-5.0, 5.0] always (anti-windup).
    I-DB-6  snapshot.confidence ∈ [0.0, 1.0] always.
    I-DB-7  snapshot.alive_frac ∈ [0.0, 1.0]; snapshot.dynamic_frac ∈ [0.0, 1.0].
    I-DB-8  snapshot.system_health ∈ valid verdict set.
    I-DB-9  snapshot.operating_regime ∈ valid regime set.
    I-DB-10 snapshot.gradient_diagnosis ∈ valid diagnosis set.
    I-DB-11 snapshot.hallucination_risk ∈ valid risk set.
    I-DB-12 Idempotence: evaluate(tick=t) twice returns the same object.
    I-DB-13 If prediction_available, prediction_residual is finite.
    I-DB-14 If gamma_fdt_available, estimate and uncertainty are finite.
    I-DB-15 SensorGate.sanitize is idempotent (bit-identical output on repeat).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from core.constants import SENSOR_GAMMA_MAX_ABS, SENSOR_PHI_MAX_ABS
from core.decision_bridge import (
    DecisionBridge,
    OnlinePredictor,
    PIController,
    SensorGate,
)

# ── Hypothesis strategies ────────────────────────────────────────────────
_VALID_HEALTH = {"OPTIMAL", "DEGRADED", "CRITICAL", "DEAD"}
_VALID_REGIME = {"frozen", "critical", "chaotic"}
_VALID_DIAGNOSIS = {
    "living_gradient",
    "static_capacitor",
    "dead_equilibrium",
    "transient",
    "unknown",
}
_VALID_RISK = {"low", "moderate", "high"}

_SETTINGS = settings(
    max_examples=60,
    deadline=None,  # CI machines vary; we care about correctness, not wall time.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


def _finite_floats(
    min_value: float, max_value: float, allow_extreme: bool = True
) -> st.SearchStrategy[float]:
    return st.floats(
        min_value=min_value,
        max_value=max_value,
        allow_nan=False,
        allow_infinity=False,
        allow_subnormal=allow_extreme,
    )


def _finite_history(
    min_n: int = 4, max_n: int = 40, dim: int = 4
) -> st.SearchStrategy[tuple[np.ndarray, np.ndarray]]:
    return st.integers(min_value=min_n, max_value=max_n).flatmap(
        lambda n: st.tuples(
            hnp.arrays(
                dtype=np.float64,
                shape=(n, dim),
                elements=_finite_floats(-2.0, 2.0),
            ),
            hnp.arrays(
                dtype=np.float64,
                shape=(n,),
                elements=_finite_floats(0.0, 3.0),
            ),
        )
    )


# ─────────────────────────────────────────────────────────────────────────
# I-DB-1 · I-DB-3 … I-DB-11 — evaluate never raises on valid input, and
# every enumerable field lies in its valid range / set.
# ─────────────────────────────────────────────────────────────────────────


class TestEvaluateInvariants:
    @given(
        history=_finite_history(),
        gamma_std=_finite_floats(0.0, 1.0),
        spectral_radius=_finite_floats(0.0, 2.0),
        tick=st.integers(min_value=0, max_value=10_000),
    )
    @_SETTINGS
    def test_evaluate_satisfies_all_range_invariants(
        self,
        history: tuple[np.ndarray, np.ndarray],
        gamma_std: float,
        spectral_radius: float,
        tick: int,
    ) -> None:
        bridge = DecisionBridge()
        phi, gamma = history

        snap = bridge.evaluate(
            tick=tick,
            gamma_mean=float(np.mean(gamma)),
            gamma_std=gamma_std,
            spectral_radius=spectral_radius,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )

        # I-DB-3 / I-DB-4 / I-DB-5
        assert 0.01 - 1e-12 <= snap.critic_gain <= 1.0 + 1e-12
        assert 0.0 - 1e-12 <= snap.energy_remaining_frac <= 1.0 + 1e-12
        assert -5.0 - 1e-12 <= snap.controller_integral <= 5.0 + 1e-12

        # I-DB-6 / I-DB-7
        assert 0.0 <= snap.confidence <= 1.0
        assert 0.0 <= snap.alive_frac <= 1.0
        assert 0.0 <= snap.dynamic_frac <= 1.0

        # I-DB-8 / I-DB-9 / I-DB-10 / I-DB-11
        assert snap.system_health in _VALID_HEALTH
        assert snap.operating_regime in _VALID_REGIME
        assert snap.gradient_diagnosis in _VALID_DIAGNOSIS
        assert snap.hallucination_risk in _VALID_RISK

        # I-DB-13 / I-DB-14
        if snap.prediction_available:
            assert math.isfinite(snap.prediction_residual)
        if snap.gamma_fdt_available:
            assert math.isfinite(snap.gamma_fdt_estimate)
            assert math.isfinite(snap.gamma_fdt_uncertainty)


# ─────────────────────────────────────────────────────────────────────────
# I-DB-2 — evaluate(non-finite input) always raises.
# ─────────────────────────────────────────────────────────────────────────


class TestIngressFailsClosed:
    @given(
        n=st.integers(min_value=4, max_value=15),
        bad_index=st.integers(min_value=0, max_value=14),
        bad_value=st.sampled_from([float("nan"), float("inf"), float("-inf")]),
        which=st.sampled_from(["phi", "gamma"]),
    )
    @_SETTINGS
    def test_any_non_finite_raises(
        self, n: int, bad_index: int, bad_value: float, which: str
    ) -> None:
        bridge = DecisionBridge()
        phi = np.zeros((n, 4), dtype=np.float64)
        gamma = np.ones(n, dtype=np.float64)
        idx = min(bad_index, n - 1)
        if which == "phi":
            phi[idx, 0] = bad_value
        else:
            gamma[idx] = bad_value
        with pytest.raises(ValueError, match="non-finite"):
            bridge.evaluate(
                tick=1,
                gamma_mean=1.0,
                gamma_std=0.1,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )


# ─────────────────────────────────────────────────────────────────────────
# I-DB-12 — idempotence per tick (fresh bridge per test to avoid state leak).
# ─────────────────────────────────────────────────────────────────────────


class TestIdempotenceProperty:
    @given(history=_finite_history(), tick=st.integers(min_value=0, max_value=1000))
    @_SETTINGS
    def test_same_tick_is_memoised(self, history: tuple[np.ndarray, np.ndarray], tick: int) -> None:
        bridge = DecisionBridge()
        phi, gamma = history
        a = bridge.evaluate(
            tick=tick,
            gamma_mean=float(np.mean(gamma)),
            gamma_std=0.1,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        b = bridge.evaluate(
            tick=tick,
            gamma_mean=float(np.mean(gamma)),
            gamma_std=0.1,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert a is b


# ─────────────────────────────────────────────────────────────────────────
# I-DB-15 — SensorGate.sanitize is idempotent across arbitrary inputs.
# ─────────────────────────────────────────────────────────────────────────


class TestSensorGateSanitizeIdempotenceProperty:
    @given(
        phi=hnp.arrays(
            dtype=np.float64,
            shape=st.tuples(
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=6),
            ),
            elements=_finite_floats(-4 * SENSOR_PHI_MAX_ABS, 4 * SENSOR_PHI_MAX_ABS),
        ),
    )
    @_SETTINGS
    def test_phi_sanitize_is_idempotent(self, phi: np.ndarray) -> None:
        gate = SensorGate()
        gamma = np.ones(phi.shape[0], dtype=np.float64)
        phi1, gamma1, _ = gate.sanitize(phi, gamma)
        phi2, gamma2, report2 = gate.sanitize(phi1, gamma1)
        np.testing.assert_array_equal(phi1, phi2)
        np.testing.assert_array_equal(gamma1, gamma2)
        # Second pass finds nothing left to clip.
        assert report2.phi_n_clipped == 0

    @given(
        n=st.integers(min_value=1, max_value=20),
        gamma_raw=st.lists(
            _finite_floats(-4 * SENSOR_GAMMA_MAX_ABS, 4 * SENSOR_GAMMA_MAX_ABS),
            min_size=1,
            max_size=20,
        ),
    )
    @_SETTINGS
    def test_gamma_sanitize_is_idempotent(self, n: int, gamma_raw: list[float]) -> None:
        gate = SensorGate()
        gamma = np.asarray(
            gamma_raw[:n] if len(gamma_raw) >= n else (gamma_raw + [1.0] * (n - len(gamma_raw))),
            dtype=np.float64,
        )
        phi = np.zeros((gamma.shape[0], 2), dtype=np.float64)
        _, gamma1, _ = gate.sanitize(phi, gamma)
        _, gamma2, report2 = gate.sanitize(phi, gamma1)
        np.testing.assert_array_equal(gamma1, gamma2)
        assert report2.gamma_n_clipped == 0


# ─────────────────────────────────────────────────────────────────────────
# Predictor / PI controller property-level invariants.
# ─────────────────────────────────────────────────────────────────────────


class TestPredictorProperty:
    @given(
        values=st.lists(_finite_floats(0.0, 1.0), min_size=5, max_size=200),
    )
    @_SETTINGS
    def test_residuals_are_finite_or_nan(self, values: list[float]) -> None:
        pred = OnlinePredictor()
        for v in values:
            r = pred.observe(float(v))
            assert math.isfinite(r) or math.isnan(r)


class TestControllerProperty:
    @given(
        errors=st.lists(
            _finite_floats(-10.0, 10.0),
            min_size=1,
            max_size=500,
        ),
    )
    @_SETTINGS
    def test_gain_and_integral_always_bounded(self, errors: list[float]) -> None:
        pi = PIController()
        for e in errors:
            pi.step(float(e))
            assert 0.01 - 1e-12 <= pi.gain <= 1.0 + 1e-12
            assert -5.0 - 1e-12 <= pi.integral <= 5.0 + 1e-12

    @given(
        errors=st.lists(
            _finite_floats(-1.0, 1.0),
            min_size=1,
            max_size=200,
        ),
    )
    @_SETTINGS
    def test_determinism_under_replay(self, errors: list[float]) -> None:
        a = PIController()
        b = PIController()
        for e in errors:
            a.step(float(e))
            b.step(float(e))
        assert a.gain == b.gain
        assert a.integral == b.integral
