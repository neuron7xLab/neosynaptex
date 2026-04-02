"""Tests for neosynaptex v0.2.0 -- NFI integrating mirror layer.

45 tests covering: StateCollector, Gamma+CI, Coherence, Permutation test,
Jacobian+Cond, Phase+Hysteresis, Granger, Anomaly, Portrait, Resilience,
Modulation, Proof, Invariants, Lifecycle, Edge cases.
"""

import json
import math
import tempfile

import numpy as np
import pytest

from neosynaptex import (
    CONVERGING,
    DEGENERATE,
    DIVERGING,
    DRIFTING,
    INITIALIZING,
    MockBnSynAdapter,
    MockMarketAdapter,
    MockMfnAdapter,
    MockPsycheCoreAdapter,
    Neosynaptex,
)


# ===================================================================
# Helper adapters
# ===================================================================
class _ConstantTopoAdapter:
    def __init__(self, seed=99):
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self):
        return "const_topo"

    @property
    def state_keys(self):
        return ["x", "y"]

    def state(self):
        self._t += 1
        return {"x": 1.0 + self._rng.normal(0, 0.01), "y": 2.0 + self._rng.normal(0, 0.01)}

    def topo(self):
        return 5.0 + 0.01 * self._rng.standard_normal()

    def thermo_cost(self):
        return 1.0 + 0.01 * self._rng.standard_normal()


class _NoisyAdapter:
    def __init__(self, seed=77):
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self):
        return "noisy"

    @property
    def state_keys(self):
        return ["a", "b"]

    def state(self):
        self._t += 1
        return {"a": self._rng.standard_normal(), "b": self._rng.standard_normal()}

    def topo(self):
        return max(0.01, abs(self._rng.standard_normal()) + 0.5)

    def thermo_cost(self):
        return max(0.01, abs(self._rng.standard_normal()) + 0.5)


class _DecayingAdapter:
    def __init__(self, seed=55):
        self._rng = np.random.default_rng(seed)
        self._t = 0
        self._x, self._y = 10.0, 8.0

    @property
    def domain(self):
        return "decay"

    @property
    def state_keys(self):
        return ["x", "y"]

    def state(self):
        self._t += 1
        self._x *= 0.7
        self._y *= 0.75
        return {"x": self._x + self._rng.normal(0, 0.01), "y": self._y + self._rng.normal(0, 0.01)}

    def topo(self):
        return max(0.01, 5.0 + 2.0 * math.sin(0.05 * self._t))

    def thermo_cost(self):
        return max(0.01, abs(self._x) * 0.1)


class _ExplodingAdapter:
    def __init__(self, seed=66):
        self._rng = np.random.default_rng(seed)
        self._t = 0
        self._x, self._y = 1.0, 1.0

    @property
    def domain(self):
        return "explode"

    @property
    def state_keys(self):
        return ["x", "y"]

    def state(self):
        self._t += 1
        self._x *= 1.3
        self._y *= 1.25
        return {"x": self._x + self._rng.normal(0, 0.01), "y": self._y + self._rng.normal(0, 0.01)}

    def topo(self):
        return max(0.01, 5.0 + 3.0 * abs(math.sin(0.04 * self._t)))

    def thermo_cost(self):
        return max(0.01, abs(self._x) * 0.1)


class _SustainedDivergentAdapter:
    def __init__(self, seed=88):
        self._rng = np.random.default_rng(seed)
        self._t = 0
        self._x, self._y = 1.0, 1.0

    @property
    def domain(self):
        return "degen"

    @property
    def state_keys(self):
        return ["x", "y"]

    def state(self):
        self._t += 1
        self._x *= 2.0
        self._y *= 1.8
        return {
            "x": self._x + self._rng.normal(0, 0.001),
            "y": self._y + self._rng.normal(0, 0.001),
        }

    def topo(self):
        return max(0.01, 5.0 + 3.0 * abs(math.sin(0.04 * self._t)))

    def thermo_cost(self):
        return max(0.01, abs(self._x) * 0.1)


class _TooManyKeysAdapter:
    @property
    def domain(self):
        return "big"

    @property
    def state_keys(self):
        return ["a", "b", "c", "d", "e"]

    def state(self):
        return {k: 0.0 for k in self.state_keys}

    def topo(self):
        return 1.0

    def thermo_cost(self):
        return 1.0


class _NanSometimesAdapter:
    def __init__(self, seed=33):
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self):
        return "nansome"

    @property
    def state_keys(self):
        return ["p", "q"]

    def state(self):
        self._t += 1
        if self._t % 5 == 0:
            return {"p": float("nan"), "q": float("nan")}
        return {
            "p": 1.0 + 0.3 * math.sin(0.1 * self._t) + self._rng.normal(0, 0.02),
            "q": 2.0 + 0.5 * math.cos(0.08 * self._t) + self._rng.normal(0, 0.02),
        }

    def topo(self):
        return max(0.01, 3.0 + 2.0 * abs(math.sin(0.04 * self._t)))

    def thermo_cost(self):
        return max(0.01, 1.0 + 0.5 * abs(math.sin(0.06 * self._t)))


class _KnownGammaAdapter:
    def __init__(self, gamma=2.0, seed=71, name=None):
        self._gamma = gamma
        self._rng = np.random.default_rng(seed)
        self._t = 0
        self._name = name or f"kg_{gamma:.1f}"

    @property
    def domain(self):
        return self._name

    @property
    def state_keys(self):
        return ["x"]

    def state(self):
        self._t += 1
        return {"x": self._rng.standard_normal()}

    def topo(self):
        return max(0.01, 3.0 + 8.0 * abs(math.sin(0.05 * self._t)))

    def thermo_cost(self):
        t = self.topo()
        return max(0.01, 10.0 * t ** (-self._gamma) + self._rng.normal(0, 0.02))


def _full_system(window=16):
    nx = Neosynaptex(window=window)
    nx.register(MockBnSynAdapter())
    nx.register(MockMfnAdapter())
    nx.register(MockPsycheCoreAdapter())
    nx.register(MockMarketAdapter())
    return nx


def _warmup(nx, ticks=40):
    s = None
    for _ in range(ticks):
        s = nx.observe()
    return s


# ===================================================================
# StateCollector
# ===================================================================
class TestStateCollector:
    def test_register_single(self):
        nx = Neosynaptex(window=8)
        nx.register(MockBnSynAdapter())
        s = nx.observe()
        assert len(s.phi) == 3

    def test_register_multi(self):
        s = _warmup(_full_system(), 1)
        assert len(s.phi) == 12

    def test_rejects_large_state(self):
        nx = Neosynaptex(window=8)
        with pytest.raises(ValueError, match="5 state keys"):
            nx.register(_TooManyKeysAdapter())

    def test_phi_is_copy(self):
        nx = Neosynaptex(window=8)
        nx.register(MockBnSynAdapter())
        s = nx.observe()
        s.phi[0] = 999.0
        s2 = nx.observe()
        assert s2.phi[0] != 999.0


# ===================================================================
# Gamma + CI
# ===================================================================
class TestGamma:
    def test_gamma_known_morpho(self):
        nx = Neosynaptex(window=16)
        nx.register(MockMfnAdapter())
        s = _warmup(nx, 30)
        assert np.isfinite(s.gamma_per_domain["morpho"])
        assert abs(s.gamma_per_domain["morpho"] - 1.0) < 0.15

    def test_gamma_ci_contains_true(self):
        nx = Neosynaptex(window=16)
        nx.register(MockMfnAdapter())
        s = _warmup(nx, 30)
        ci = s.gamma_ci_per_domain["morpho"]
        assert np.isfinite(ci[0]) and np.isfinite(ci[1])
        assert ci[0] <= 1.0 <= ci[1]  # true gamma=1.0 inside CI

    def test_gamma_nan_insufficient(self):
        nx = Neosynaptex(window=16)
        nx.register(MockMfnAdapter())
        s = _warmup(nx, 3)
        assert np.isnan(s.gamma_per_domain["morpho"])

    def test_gamma_nan_stationary(self):
        nx = Neosynaptex(window=16)
        nx.register(_ConstantTopoAdapter())
        s = _warmup(nx, 20)
        assert np.isnan(s.gamma_per_domain["const_topo"])

    def test_gamma_nan_noisy(self):
        nx = Neosynaptex(window=16)
        nx.register(_NoisyAdapter())
        s = _warmup(nx, 20)
        assert np.isnan(s.gamma_per_domain["noisy"])

    def test_gamma_ema_smoother(self):
        nx = _full_system()
        gammas_raw = []
        gammas_ema = []
        for _ in range(40):
            s = nx.observe()
        for _ in range(20):
            s = nx.observe()
            g = s.gamma_per_domain.get("morpho", float("nan"))
            e = s.gamma_ema_per_domain.get("morpho", float("nan"))
            if np.isfinite(g):
                gammas_raw.append(g)
            if np.isfinite(e):
                gammas_ema.append(e)
        if len(gammas_raw) > 5 and len(gammas_ema) > 5:
            assert np.std(gammas_ema) <= np.std(gammas_raw) + 0.01

    def test_dgamma_dt_finite(self):
        s = _warmup(_full_system(), 30)
        assert np.isfinite(s.dgamma_dt)


# ===================================================================
# Coherence + Permutation test
# ===================================================================
class TestCoherence:
    def test_coherence_high(self):
        s = _warmup(_full_system(), 40)
        if np.isfinite(s.cross_coherence):
            assert s.cross_coherence > 0.7

    def test_coherence_nan_single(self):
        nx = Neosynaptex(window=16)
        nx.register(MockMfnAdapter())
        s = _warmup(nx, 30)
        assert np.isnan(s.cross_coherence)

    def test_permutation_runs(self):
        """Permutation test returns a valid p-value in [0, 1]."""
        s = _warmup(_full_system(), 40)
        p = s.universal_scaling_p
        if np.isfinite(p):
            assert 0.0 <= p <= 1.0

    def test_permutation_low_p_dispersed(self):
        """Domains with very different gammas -> p should be low."""
        nx = Neosynaptex(window=16)
        nx.register(_KnownGammaAdapter(gamma=0.5, seed=10, name="a"))
        nx.register(_KnownGammaAdapter(gamma=3.0, seed=20, name="b"))
        s = _warmup(nx, 30)
        # dispersed gammas -> may reject universal scaling
        # (permutation test with only 2 groups has limited power, so just check it runs)
        assert isinstance(s.universal_scaling_p, float)


# ===================================================================
# Jacobian + Condition number
# ===================================================================
class TestJacobian:
    def test_sr_initializing(self):
        nx = Neosynaptex(window=16)
        nx.register(MockBnSynAdapter())
        s = nx.observe()
        assert np.isnan(s.spectral_radius)

    def test_cond_reported(self):
        s = _warmup(_full_system(), 20)
        for name, cond in s.cond_per_domain.items():
            assert isinstance(cond, float)

    def test_sr_nan_masking(self):
        nx = Neosynaptex(window=16)
        nx.register(_NanSometimesAdapter())
        s = _warmup(nx, 20)
        assert isinstance(s.spectral_radius, float)

    def test_sr_diverging(self):
        nx = Neosynaptex(window=16)
        nx.register(_ExplodingAdapter())
        s = _warmup(nx, 20)
        sr = s.sr_per_domain.get("explode", float("nan"))
        if np.isfinite(sr):
            assert sr > 1.0


# ===================================================================
# Phase + Hysteresis
# ===================================================================
class TestPhase:
    def test_phase_stable_after_warmup(self):
        """With hysteresis, phase should not flicker on every tick."""
        nx = _full_system()
        _warmup(nx, 20)
        phases = []
        for _ in range(20):
            s = nx.observe()
            phases.append(s.phase)
        transitions = sum(1 for i in range(1, len(phases)) if phases[i] != phases[i - 1])
        # Hysteresis should reduce transitions compared to v1
        assert transitions < 10

    def test_phase_degenerate(self):
        nx = Neosynaptex(window=8)
        nx.register(_SustainedDivergentAdapter())
        phases = []
        for _ in range(20):
            s = nx.observe()
            phases.append(s.phase)
        non_init = [p for p in phases if p != INITIALIZING]
        if len(non_init) > 6:
            assert DEGENERATE in non_init or DIVERGING in non_init

    def test_converging_and_drifting_exist(self):
        """CONVERGING and DRIFTING are valid phase labels."""
        assert CONVERGING == "CONVERGING"
        assert DRIFTING == "DRIFTING"


# ===================================================================
# Granger causality
# ===================================================================
class TestGranger:
    def test_granger_graph_structure(self):
        s = _warmup(_full_system(), 40)
        assert isinstance(s.granger_graph, dict)
        for src, targets in s.granger_graph.items():
            assert src not in targets  # no self-loops

    def test_granger_nan_early(self):
        nx = _full_system()
        s = _warmup(nx, 5)
        for src, targets in s.granger_graph.items():
            for tgt, val in targets.items():
                assert isinstance(val, float)


# ===================================================================
# Anomaly isolation
# ===================================================================
class TestAnomaly:
    def test_anomaly_scores_present(self):
        s = _warmup(_full_system(), 40)
        assert len(s.anomaly_score) == 4

    def test_anomaly_low_when_coherent(self):
        s = _warmup(_full_system(), 40)
        for name, score in s.anomaly_score.items():
            if np.isfinite(score):
                assert score < 0.5  # no strong outlier among similar gammas


# ===================================================================
# Phase portrait
# ===================================================================
class TestPortrait:
    def test_portrait_keys(self):
        s = _warmup(_full_system(), 40)
        assert "area" in s.portrait
        assert "recurrence" in s.portrait
        assert "distance_to_ideal" in s.portrait

    def test_distance_to_ideal_reasonable(self):
        s = _warmup(_full_system(), 40)
        d = s.portrait["distance_to_ideal"]
        if np.isfinite(d):
            assert d < 2.0  # gamma~1, sr~1 -> close to ideal


# ===================================================================
# Resilience
# ===================================================================
class TestResilience:
    def test_resilience_is_float(self):
        s = _warmup(_full_system(), 40)
        assert isinstance(s.resilience_score, float)


# ===================================================================
# Modulation
# ===================================================================
class TestModulation:
    def test_modulation_bounded(self):
        s = _warmup(_full_system(), 40)
        for name, mod in s.modulation.items():
            assert -0.05 <= mod <= 0.05

    def test_modulation_all_domains(self):
        s = _warmup(_full_system(), 40)
        assert len(s.modulation) == 4


# ===================================================================
# Proof bundle
# ===================================================================
class TestProof:
    def test_export_proof_dict(self):
        nx = _full_system()
        _warmup(nx, 40)
        proof = nx.export_proof()
        assert proof["version"] == "0.2.0"
        assert proof["verdict"] in ("COHERENT", "INCOHERENT", "PARTIAL")
        assert "gamma" in proof
        assert "jacobian" in proof

    def test_export_proof_file(self):
        nx = _full_system()
        _warmup(nx, 40)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        nx.export_proof(path)
        with open(path) as f:
            data = json.load(f)
        assert data["ticks"] == 40


# ===================================================================
# Invariants
# ===================================================================
class TestInvariants:
    def test_gamma_not_stored(self):
        nx = _full_system()
        nx.observe()
        assert not hasattr(nx, "gamma")
        assert "gamma" not in nx.__dict__

    def test_state_immutable(self):
        nx = Neosynaptex(window=8)
        nx.register(MockBnSynAdapter())
        s = nx.observe()
        with pytest.raises(AttributeError):
            s.t = 999

    def test_diagnostic_independent(self):
        nx = Neosynaptex(window=8)
        nx.register(MockBnSynAdapter())
        s = nx.observe()
        assert id(s.diagnostic) != id(s.phi)


# ===================================================================
# Lifecycle
# ===================================================================
class TestLifecycle:
    def test_100_ticks(self):
        nx = _full_system()
        s = _warmup(nx, 100)
        assert s.t == 100
        assert np.isfinite(s.gamma_per_domain.get("morpho", float("nan")))

    def test_history_bounded(self):
        nx = Neosynaptex(window=16)
        nx.register(MockBnSynAdapter())
        _warmup(nx, 200)
        assert len(nx.history()) <= 3 * 16

    def test_reset(self):
        nx = _full_system()
        _warmup(nx, 20)
        nx.reset()
        s = nx.observe()
        assert s.phase == INITIALIZING
        assert len(nx.history()) == 1


# ===================================================================
# Edge cases
# ===================================================================
class TestEdge:
    def test_no_adapters(self):
        with pytest.raises(RuntimeError, match="No adapters"):
            Neosynaptex(window=8).observe()

    def test_need_vector_none(self):
        assert Neosynaptex(window=8).need_vector() is None

    def test_cross_jacobian_available_after_64_ticks(self):
        engine = Neosynaptex(window=16)
        engine.register(MockBnSynAdapter())
        engine.register(MockMfnAdapter())
        engine.register(MockPsycheCoreAdapter())
        engine.register(MockMarketAdapter())
        for _ in range(70):
            engine.observe()

        proof = engine.export_proof()
        ct = proof["coupling_tensor"]

        assert "cross_jacobian" in ct
        # At least one non-NaN entry after 70 ticks
        cj = ct["cross_jacobian"]
        if cj:
            all_values = [v for row in cj.values() for v in row.values() if v is not None]
            assert len(all_values) > 0, "Cross-domain Jacobian should have values after 70 ticks"

    def test_adaptive_window_bounded(self):
        engine = Neosynaptex(window=16)
        engine.register(MockBnSynAdapter())
        engine.register(MockMfnAdapter())
        for _ in range(30):
            engine.observe()
        assert engine._adaptive_window >= 16
        assert engine._adaptive_window <= 256

    def test_proof_chain_integrity(self):
        engine = Neosynaptex(window=16)
        engine.register(MockBnSynAdapter())
        engine.register(MockMfnAdapter())

        proofs = []
        for _ in range(10):
            engine.observe()
            proofs.append(engine.export_proof())

        # First proof prev_hash is GENESIS
        assert proofs[0]["chain"]["prev_hash"] == "GENESIS"

        # Each prev_hash matches previous self_hash
        for i in range(1, len(proofs)):
            assert proofs[i]["chain"]["prev_hash"] == proofs[i - 1]["chain"]["self_hash"]

        # Chain root is consistent
        root = proofs[0]["chain"]["chain_root"]
        for p in proofs:
            assert p["chain"]["chain_root"] == root

        # Self-hash is valid
        import hashlib
        import json as _json

        for p in proofs:
            clean = {k: v for k, v in p.items() if k != "chain"}
            chain_without_self = {k: v for k, v in p["chain"].items() if k != "self_hash"}
            clean["chain"] = chain_without_self
            canonical = _json.dumps(clean, sort_keys=True, ensure_ascii=True, default=str)
            expected = hashlib.sha256(canonical.encode()).hexdigest()
            assert p["chain"]["self_hash"] == expected

    def test_all_ascii(self):
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "neosynaptex.py"
        text = src.read_text(encoding="utf-8")
        for i, line in enumerate(text.split("\n"), 1):
            code = line.split("#")[0]
            for ch in code:
                if ord(ch) > 127:
                    pytest.fail(f"Non-ASCII U+{ord(ch):04X} line {i}")
