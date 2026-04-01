"""BN-Syn spiking neural criticality real substrate test."""

import sys

sys.path.insert(0, ".")


class TestBnSynReal:
    def test_adapter_creates(self):
        from substrates.bn_syn.adapter import BnSynAdapter

        a = BnSynAdapter(seed=42)
        assert a.domain == "spike"

    def test_gamma_not_collapsed(self):
        from substrates.bn_syn.adapter import validate_standalone

        r = validate_standalone()
        assert abs(r["gamma"] - 1.0) < 0.50, f"γ={r['gamma']}"

    def test_ci_contains_unity(self):
        from substrates.bn_syn.adapter import validate_standalone

        r = validate_standalone()
        assert r["ci"][0] <= 1.0 <= r["ci"][1], f"CI {r['ci']}"

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
