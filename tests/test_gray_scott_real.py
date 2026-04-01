"""
Gray-Scott reaction-diffusion real substrate test.
γ is DERIVED from PDE simulation parameter sweep — never assigned.
"""

import sys

sys.path.insert(0, ".")


class TestGrayScottReal:
    def test_adapter_creates(self):
        from substrates.gray_scott.adapter import GrayScottAdapter

        adapter = GrayScottAdapter(seed=42)
        assert len(adapter._equilibria) == 20
        assert adapter.domain == "reaction_diffusion"

    def test_topo_varies(self):
        """Different F values must produce different v_mass."""
        from substrates.gray_scott.adapter import GrayScottAdapter

        adapter = GrayScottAdapter(seed=42)
        masses = [eq["v_mass"] for eq in adapter._equilibria]
        assert max(masses) > min(masses) * 1.5, "Insufficient topo range"

    def test_gamma_metastable(self):
        """γ must be in METASTABLE or WARNING zone."""
        from substrates.gray_scott.adapter import validate_standalone

        result = validate_standalone()
        assert abs(result["gamma"] - 1.0) < 0.30, f"γ={result['gamma']:.4f} outside WARNING zone"

    def test_gamma_ci_contains_unity(self):
        """95% CI should contain 1.0."""
        from substrates.gray_scott.adapter import validate_standalone

        result = validate_standalone()
        ci = result["ci"]
        assert ci[0] <= 1.0 <= ci[1], f"CI {ci} doesn't contain 1.0"

    def test_protocol_compatible(self):
        from substrates.gray_scott.adapter import GrayScottAdapter

        adapter = GrayScottAdapter(seed=42)
        state = adapter.state()
        assert isinstance(state, dict)
        assert len(state) <= 4
        t = adapter.topo()
        c = adapter.thermo_cost()
        assert t > 0 and c > 0

    def test_engine_integration(self):
        from neosynaptex import Neosynaptex
        from substrates.gray_scott.adapter import GrayScottAdapter

        adapter = GrayScottAdapter(seed=42)
        nx = Neosynaptex(window=20)
        nx.register(adapter)
        last = None
        for _ in range(30):
            last = nx.observe()
        assert last is not None
