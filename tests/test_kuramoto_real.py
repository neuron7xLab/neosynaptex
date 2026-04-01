"""Kuramoto market coherence real substrate test."""

import sys

sys.path.insert(0, ".")


class TestKuramotoReal:
    def test_adapter_creates(self):
        from substrates.kuramoto.adapter import KuramotoAdapter

        adapter = KuramotoAdapter(seed=42)
        assert adapter.domain == "kuramoto_market"

    def test_gamma_near_unity(self):
        from substrates.kuramoto.adapter import validate_standalone

        result = validate_standalone()
        assert abs(result["gamma"] - 1.0) < 0.30, f"γ={result['gamma']}"

    def test_ci_contains_unity(self):
        from substrates.kuramoto.adapter import validate_standalone

        result = validate_standalone()
        ci = result["ci"]
        assert ci[0] <= 1.0 <= ci[1], f"CI {ci}"

    def test_engine_integration(self):
        from neosynaptex import Neosynaptex
        from substrates.kuramoto.adapter import KuramotoAdapter

        adapter = KuramotoAdapter(seed=42)
        nx = Neosynaptex(window=30)
        nx.register(adapter)
        last = None
        for _ in range(40):
            last = nx.observe()
        assert last is not None
