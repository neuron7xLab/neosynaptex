"""Tests for Observatory — unified diagnostic view."""


from mycelium_fractal_net.core.observatory import ObservatoryReport, observe
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.field import SimulationSpec


class TestObservatory:
    def test_observe_returns_report(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=20, seed=42))
        report = observe(seq)
        assert isinstance(report, ObservatoryReport)
        assert report.grid_size == 16
        assert report.compute_time_ms > 0

    def test_report_str(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=20, seed=42))
        report = observe(seq)
        text = str(report)
        assert "OBSERVATORY" in text
        assert "THERMODYNAMICS" in text
        assert "TOPOLOGY" in text
        assert "INVARIANTS" in text

    def test_report_to_dict(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=20, seed=42))
        report = observe(seq)
        d = report.to_dict()
        assert "grid_size" in d
        assert "lambda2" in d
        assert "anomaly_label" in d

    def test_all_sections_populated(self):
        seq = simulate_history(SimulationSpec(grid_size=16, steps=30, seed=42))
        report = observe(seq)
        assert report.entropy_production >= 0
        assert report.beta_0 >= 0
        assert report.d_box > 0
        assert report.anomaly_label != ""
        assert report.criticality_verdict != ""

    def test_observe_via_mfn(self):
        import mycelium_fractal_net as mfn
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        report = mfn.observe(seq)
        assert isinstance(report, mfn.ObservatoryReport)
