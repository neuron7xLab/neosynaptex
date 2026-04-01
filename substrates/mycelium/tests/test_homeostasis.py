"""Tests for HomeostasisLoop — self-regulating entropy balance."""

from mycelium_fractal_net.core.homeostasis import HomeostasisLoop, HomeostasisReport
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.field import SimulationSpec


class TestHomeostasis:
    def test_loop_runs(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=30, seed=42))
        loop = HomeostasisLoop(max_iterations=3, heal_budget=1)
        report = loop.run(seq)
        assert isinstance(report, HomeostasisReport)
        assert report.iterations >= 1
        assert report.compute_time_ms > 0

    def test_entropy_tracked(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=30, seed=42))
        loop = HomeostasisLoop(max_iterations=3)
        report = loop.run(seq)
        assert len(report.entropy_trajectory) >= 1
        assert all(s >= 0 for s in report.entropy_trajectory)

    def test_converges_or_classifies(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=30, seed=42))
        loop = HomeostasisLoop(max_iterations=5, convergence_epsilon=0.1)
        report = loop.run(seq)
        assert report.final_verdict in ("equilibrium", "limit_cycle", "divergent", "timeout")

    def test_report_str(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=20, seed=42))
        report = HomeostasisLoop(max_iterations=2).run(seq)
        text = str(report)
        assert "HOMEOSTASIS" in text
        assert "Iterations" in text

    def test_gate_counted(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=20, seed=42))
        report = HomeostasisLoop(max_iterations=3).run(seq)
        total_gates = report.gate_passes + report.gate_failures
        # Gate may be skipped on convergence iteration
        assert total_gates >= 1
        assert total_gates <= report.iterations
