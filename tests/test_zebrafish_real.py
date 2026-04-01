"""
Zebrafish real data integration test.
γ is DERIVED from McGuirl 2020 .mat files — never assigned.
"""
import pytest
import numpy as np
import sys
sys.path.insert(0, ".")


def _has_data():
    from pathlib import Path
    return Path("/home/neuro7/data/zebrafish/data/sample_inputs/Out_WT_default_1.mat").exists()


@pytest.mark.skipif(not _has_data(), reason="Zebrafish .mat data not available")
class TestZebrafishReal:

    def test_wt_adapter_loads(self):
        from substrates.zebrafish.adapter import ZebrafishAdapter
        adapter = ZebrafishAdapter("WT")
        adapter._ensure_loaded()
        assert adapter._n_days == 46
        assert adapter._loaded

    def test_wt_topo_increases(self):
        """Cell density must increase over development."""
        from substrates.zebrafish.adapter import ZebrafishAdapter
        adapter = ZebrafishAdapter("WT")
        adapter._ensure_loaded()
        first = adapter._densities[0]
        last = adapter._densities[-1]
        assert last > first * 2, f"Density didn't grow enough: {first:.4f} → {last:.4f}"

    def test_wt_cost_decreases(self):
        """Pattern disorder (NN CV) should decrease as pattern organizes."""
        from substrates.zebrafish.adapter import ZebrafishAdapter
        adapter = ZebrafishAdapter("WT")
        adapter._ensure_loaded()
        cvs = adapter._nn_cvs
        valid = cvs[np.isfinite(cvs)]
        early = np.mean(valid[:10])
        late = np.mean(valid[-10:])
        assert late < early, f"NN_CV didn't decrease: {early:.4f} → {late:.4f}"

    def test_wt_gamma_not_collapsed(self):
        """WT γ must not be in COLLAPSE zone (|γ-1| < 0.50)."""
        from substrates.zebrafish.adapter import validate_standalone
        results = validate_standalone()
        gamma = results["WT"]["gamma"]
        assert abs(gamma - 1.0) < 0.50, f"WT γ={gamma:.4f} in COLLAPSE zone"

    def test_wt_gamma_ci_contains_unity(self):
        """WT 95% CI should contain 1.0."""
        from substrates.zebrafish.adapter import validate_standalone
        results = validate_standalone()
        ci = results["WT"]["ci"]
        assert ci[0] <= 1.0 <= ci[1], f"CI [{ci[0]:.3f}, {ci[1]:.3f}] doesn't contain 1.0"

    def test_wt_closer_to_unity_than_mutants(self):
        """WT |γ-1| must be smaller than mutant mean |γ-1|."""
        from substrates.zebrafish.adapter import validate_standalone
        results = validate_standalone()
        wt_dist = abs(results["WT"]["gamma"] - 1.0)
        mut_dists = [
            abs(results[p]["gamma"] - 1.0)
            for p in ["pfef", "shady"]
            if p in results and "gamma" in results[p]
        ]
        if not mut_dists:
            pytest.skip("No mutant data available")
        mut_mean = sum(mut_dists) / len(mut_dists)
        assert wt_dist < mut_mean, (
            f"WT |γ-1|={wt_dist:.4f} not closer to unity than mutant mean {mut_mean:.4f}"
        )

    def test_adapter_protocol_compatible(self):
        """Adapter must implement full DomainAdapter interface."""
        from substrates.zebrafish.adapter import ZebrafishAdapter
        adapter = ZebrafishAdapter("WT")
        assert adapter.domain == "zebrafish"
        assert len(adapter.state_keys) >= 3
        state = adapter.state()
        assert isinstance(state, dict)
        assert all(isinstance(v, float) for v in state.values())
        topo = adapter.topo()
        cost = adapter.thermo_cost()
        assert isinstance(topo, float) and topo > 0
        assert isinstance(cost, float) and cost > 0

    def test_engine_integration(self):
        """ZebrafishAdapter works through neosynaptex.py engine."""
        from substrates.zebrafish.adapter import ZebrafishAdapter
        from neosynaptex import Neosynaptex

        adapter = ZebrafishAdapter("WT")
        nx = Neosynaptex(window=46)
        nx.register(adapter)

        last = None
        for _ in range(56):
            last = nx.observe()

        assert last is not None
        assert last.phase in ("METASTABLE", "WARNING", "CRITICAL", "TRANSIENT")
        # gamma should be finite
        if np.isfinite(last.gamma_mean):
            assert abs(last.gamma_mean - 1.0) < 1.5, f"γ={last.gamma_mean} too far from unity"
