"""Tests for SERO M0 — the REAL Hormonal Vector Regulation engine.

These are not toy tests. Each test validates a specific equation from the
SERO v0.5 whitepaper against its formal properties.
"""

from __future__ import annotations

from neuron7x_agents.regulation.sero_m0 import (
    AdmissionController,
    BurstLoad,
    DependencyBlackhole,
    EWMAForecaster,
    FalseAlarm,
    GradualDegradation,
    HVRConfig,
    HVREngine,
    SLOTargets,
    StateVector,
    StepInputFault,
    StressAggregator,
    run_scenario,
    sparkline,
)

# ═══════════════════════════════════════════════════════════════════════
#  Eq.10: State Vector
# ═══════════════════════════════════════════════════════════════════════


class TestStateVector:
    def test_to_vector_length(self) -> None:
        sv = StateVector()
        assert len(sv.to_vector()) == 10  # 7 SLIs + 3 dep_health

    def test_to_vector_values(self) -> None:
        sv = StateVector(error_rate=0.5, cpu_saturation=0.9)
        v = sv.to_vector()
        assert v[0] == 0.5
        assert v[4] == 0.9


# ═══════════════════════════════════════════════════════════════════════
#  EWMA Forecaster — generative model at M0
# ═══════════════════════════════════════════════════════════════════════


class TestEWMAForecaster:
    def test_first_prediction_is_identity(self) -> None:
        f = EWMAForecaster(alpha=0.3)
        x = [1.0, 2.0, 3.0]
        pred = f.predict(x)
        assert pred == x

    def test_prediction_error_is_zero_for_constant(self) -> None:
        f = EWMAForecaster(alpha=0.3)
        x = [1.0, 1.0, 1.0]
        f.update(x)
        error = f.update(x)
        assert all(e == 0.0 for e in error)

    def test_error_nonzero_for_change(self) -> None:
        f = EWMAForecaster(alpha=0.3)
        f.update([0.0, 0.0])
        error = f.update([1.0, 1.0])
        assert all(e > 0 for e in error)


# ═══════════════════════════════════════════════════════════════════════
#  Eq.6 + Eq.7: Stress Aggregation + Damping
# ═══════════════════════════════════════════════════════════════════════


class TestStressAggregator:
    def test_zero_error_zero_stress(self) -> None:
        agg = StressAggregator(HVRConfig(), SLOTargets())
        stress = agg.step([0.0] * 10)
        assert stress == 0.0

    def test_stress_rises_under_fault(self) -> None:
        agg = StressAggregator(HVRConfig(), SLOTargets())
        error = [0.5] * 10  # all channels erroring
        s1 = agg.step(error)
        s2 = agg.step(error)
        assert s2 >= s1  # damped rise

    def test_stress_bounded_by_smax(self) -> None:
        cfg = HVRConfig(S_max=5.0)
        agg = StressAggregator(cfg, SLOTargets())
        # Hammer with massive errors
        for _ in range(200):
            agg.step([100.0] * 10)
        assert agg.current_stress <= cfg.S_max + 1e-10


# ═══════════════════════════════════════════════════════════════════════
#  Eq.3 + Eq.4: Admission Control + Safety Invariant
# ═══════════════════════════════════════════════════════════════════════


class TestAdmissionController:
    def test_zero_stress_full_throughput(self) -> None:
        ac = AdmissionController(HVRConfig())
        t = ac.compute_throughput(0.0)
        assert abs(t - 1.0) < 1e-10

    def test_infinite_stress_tmin(self) -> None:
        ac = AdmissionController(HVRConfig())
        t = ac.compute_throughput(1e10)
        assert abs(t - 0.05) < 1e-6

    def test_safety_invariant_holds(self) -> None:
        ac = AdmissionController(HVRConfig())
        for s in [0.0, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]:
            ac.compute_throughput(s)
        assert ac.verify_safety_invariant()


# ═══════════════════════════════════════════════════════════════════════
#  HVR Engine — full integration
# ═══════════════════════════════════════════════════════════════════════


class TestHVREngine:
    def test_step_returns_result(self) -> None:
        engine = HVREngine()
        r = engine.step(StateVector())
        assert "tick" in r
        assert "stress" in r
        assert "throughput" in r
        assert "safety_ok" in r

    def test_baseline_throughput(self) -> None:
        engine = HVREngine()
        r = engine.step(StateVector())
        assert r["throughput"] >= 0.95

    def test_verify_invariants(self) -> None:
        engine = HVREngine()
        for _ in range(20):
            engine.step(StateVector())
        inv = engine.verify_all_invariants()
        assert inv["safety_invariant_T_min"]
        assert inv["stress_bounded_S_max"]


# ═══════════════════════════════════════════════════════════════════════
#  Chaos Scenarios — the real validation
# ═══════════════════════════════════════════════════════════════════════


class TestChaosScenarios:
    """Each scenario is a falsifiable prediction from the SERO whitepaper."""

    def test_step_input_fault(self) -> None:
        result = run_scenario(StepInputFault())
        assert result["all_pass"], f"Step-Input Fault failed: {result['criteria']}"

    def test_burst_load(self) -> None:
        result = run_scenario(BurstLoad())
        assert result["all_pass"], f"Burst Load failed: {result['criteria']}"

    def test_dependency_blackhole(self) -> None:
        result = run_scenario(DependencyBlackhole())
        assert result["all_pass"], f"Dependency Blackhole failed: {result['criteria']}"

    def test_false_alarm(self) -> None:
        result = run_scenario(FalseAlarm())
        assert result["all_pass"], f"False Alarm failed: {result['criteria']}"

    def test_gradual_degradation(self) -> None:
        result = run_scenario(GradualDegradation())
        assert result["all_pass"], f"Gradual Degradation failed: {result['criteria']}"

    def test_global_safety_invariant_all_scenarios(self) -> None:
        """T(t) >= T_min for ALL ticks across ALL scenarios."""
        for scenario_cls in [StepInputFault, BurstLoad, DependencyBlackhole, FalseAlarm, GradualDegradation]:
            result = run_scenario(scenario_cls())
            assert result["final_invariants"]["safety_invariant_T_min"], (
                f"Safety invariant violated in {scenario_cls.__name__}"
            )

    def test_global_stress_bounded(self) -> None:
        """S(t) <= S_max for ALL ticks across ALL scenarios."""
        for scenario_cls in [StepInputFault, BurstLoad, DependencyBlackhole, FalseAlarm, GradualDegradation]:
            result = run_scenario(scenario_cls())
            assert result["final_invariants"]["stress_bounded_S_max"], (
                f"Stress bound violated in {scenario_cls.__name__}"
            )


# ═══════════════════════════════════════════════════════════════════════
#  Utilities
# ═══════════════════════════════════════════════════════════════════════


class TestSparkline:
    def test_sparkline_output(self) -> None:
        line = sparkline([0.0, 0.5, 1.0], width=3)
        assert len(line) == 3

    def test_sparkline_empty(self) -> None:
        assert sparkline([]) == ""
