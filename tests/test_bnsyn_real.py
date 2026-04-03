"""BN-Syn spiking neural criticality real substrate test."""

import sys

sys.path.insert(0, ".")


class TestBnSynReal:
    def test_adapter_creates(self):
        from substrates.bn_syn.adapter import BnSynAdapter

        a = BnSynAdapter(seed=42)
        assert a.domain == "spike"

    def test_gamma_finite_size_deviation(self):
        """BN-Syn with honest branching process shows finite-size γ < 1.0.

        With N=200, k=10, the sparse network deviates from mean-field
        prediction (γ=1.0). This is expected and validates that the
        framework does NOT trivially produce γ≈1.0.
        """
        from substrates.bn_syn.adapter import BnSynAdapter

        a = BnSynAdapter(seed=42)
        topos, costs = a.get_all_pairs()
        from core.gamma import compute_gamma

        r = compute_gamma(topos, costs)
        # Honest result: γ ≈ 0.47, well below 1.0
        assert r.gamma < 0.8, f"γ={r.gamma} too close to 1.0 for finite-size"
        assert r.gamma > 0.1, f"γ={r.gamma} implausibly low"

    def test_engine_integration(self):
        from neosynaptex import Neosynaptex
        from substrates.bn_syn.adapter import BnSynAdapter

        a = BnSynAdapter(seed=42)
        nx = Neosynaptex(window=30)
        nx.register(a)
        last = None
        for _ in range(40):
            last = nx.observe()
        assert last is not None
