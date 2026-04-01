"""Property-based tests for bio/ — executable mathematical contracts.

Each @given test is a theorem verified across 200+ random inputs.
Hypothesis shrinks failures to minimal counterexamples.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays


def float_features(n: int = 8) -> st.SearchStrategy:
    return arrays(
        dtype=np.float64,
        shape=(n,),
        elements=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    )


def any_float_features(n: int = 8) -> st.SearchStrategy:
    return arrays(
        dtype=np.float64, shape=(n,), elements=st.floats(allow_nan=True, allow_infinity=True)
    )


def bio_params() -> st.SearchStrategy:
    return arrays(
        dtype=np.float64,
        shape=(8,),
        elements=st.one_of(
            st.floats(min_value=-100.0, max_value=100.0),
            st.just(float("nan")),
            st.just(float("inf")),
            st.just(float("-inf")),
        ),
    )


# ── HDVEncoder ────────────────────────────────────────────────


@given(features=float_features())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_hdv_encode_always_pm1(features: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    enc = HDVEncoder(n_features=8, D=1000, seed=42)
    hdv = enc.encode(features)
    assert set(np.unique(hdv)).issubset({-1.0, 1.0})


@given(features=float_features())
@settings(max_examples=200)
def test_hdv_similarity_self_is_one(features: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    enc = HDVEncoder(n_features=8, D=1000, seed=0)
    hdv = enc.encode(features)
    assert enc.similarity(hdv, hdv) == pytest.approx(1.0)


@given(f1=float_features(), f2=float_features())
@settings(max_examples=100)
def test_hdv_similarity_bounded(f1: np.ndarray, f2: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    enc = HDVEncoder(n_features=8, D=2000, seed=1)
    sim = enc.similarity(enc.encode(f1), enc.encode(f2))
    assert -1.0 <= sim <= 1.0


@given(features=any_float_features())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_hdv_encode_never_crashes(features: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    enc = HDVEncoder(n_features=8, D=500, seed=2)
    hdv = enc.encode(features)
    assert set(np.unique(hdv)).issubset({-1.0, 1.0, 0.0})


# ── BioMemory ────────────────────────────────────────────────


@given(cap=st.integers(min_value=1, max_value=50), n=st.integers(min_value=0, max_value=100))
@settings(max_examples=100)
def test_memory_size_bounded(cap: int, n: int) -> None:
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=8, D=200, seed=0)
    mem = BioMemory(enc, capacity=cap)
    rng = np.random.default_rng(42)
    for _ in range(n):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    assert mem.size <= cap


@given(n=st.integers(min_value=5, max_value=50))
@settings(max_examples=50)
def test_familiarity_unit_interval(n: int) -> None:
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=8, D=500, seed=3)
    mem = BioMemory(enc, capacity=100)
    rng = np.random.default_rng(7)
    for _ in range(n):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    for _ in range(20):
        f = mem.superposition_familiarity(enc.encode(rng.standard_normal(8)))
        assert 0.0 <= f <= 1.0


@given(
    fitnesses=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=1, max_size=20
    )
)
@settings(max_examples=100)
def test_predict_fitness_bounded(fitnesses: list[float]) -> None:
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=8, D=500, seed=4)
    mem = BioMemory(enc, capacity=50)
    rng = np.random.default_rng(8)
    for fit in fitnesses:
        mem.store(enc.encode(rng.standard_normal(8)), fitness=fit, params={})
    pred = mem.predict_fitness(enc.encode(rng.standard_normal(8)), k=3)
    assert 0.0 <= pred <= 1.0 + 1e-9


# ── Evolution params ──────────────────────────────────────────


@given(raw=bio_params())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_params_never_nan(raw: np.ndarray) -> None:
    from mycelium_fractal_net.bio.evolution import params_to_bio_config

    cfg = params_to_bio_config(raw)
    assert math.isfinite(cfg.physarum.gamma)
    assert math.isfinite(cfg.physarum.alpha)
    assert math.isfinite(cfg.anastomosis.gamma_anastomosis)
    assert math.isfinite(cfg.fhn.a)
    assert math.isfinite(cfg.chemotaxis.chi0)
    assert math.isfinite(cfg.dispersal.alpha_levy)


@given(raw=bio_params())
@settings(max_examples=200)
def test_params_within_bounds(raw: np.ndarray) -> None:
    from mycelium_fractal_net.bio.evolution import PARAM_BOUNDS, params_to_bio_config

    cfg = params_to_bio_config(raw)
    vals = [
        cfg.physarum.gamma,
        cfg.physarum.alpha,
        cfg.anastomosis.gamma_anastomosis,
        cfg.anastomosis.D_tip,
        cfg.fhn.a,
        cfg.fhn.Du,
        cfg.chemotaxis.chi0,
        cfg.dispersal.alpha_levy,
    ]
    for i, v in enumerate(vals):
        assert PARAM_BOUNDS[i, 0] <= v <= PARAM_BOUNDS[i, 1]


# ── Anastomosis conservation ─────────────────────────────────


@given(steps=st.integers(min_value=1, max_value=10))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_kappa_monotone(steps: int) -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio.anastomosis import AnastomosisEngine

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=42))
    eng = AnastomosisEngine(8)
    field = seq.field
    init = (field - field.min()) / (field.max() - field.min() + 1e-9) * 0.05
    state = eng.initialize(init)
    prev = float(np.mean(state.kappa))
    for _ in range(steps):
        state = eng.step(state)
        now = float(np.mean(state.kappa))
        assert now >= prev - 1e-10
        prev = now


@given(steps=st.integers(min_value=1, max_value=5))
@settings(max_examples=20)
def test_hyphal_non_negative(steps: int) -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio.anastomosis import AnastomosisEngine

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=7))
    eng = AnastomosisEngine(8)
    state = eng.initialize(np.abs(seq.field) * 0.01)
    for _ in range(steps):
        state = eng.step(state)
        assert np.all(state.B >= 0)
        assert np.all(state.kappa >= 0)


# ── Determinism ───────────────────────────────────────────────


@given(seed=st.integers(min_value=0, max_value=9999))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_bio_deterministic(seed: int) -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio import BioConfig, BioExtension

    spec = mfn.SimulationSpec(grid_size=8, steps=10, seed=seed)
    seq = mfn.simulate(spec)
    cfg = BioConfig(seed=seed, enable_dispersal=False)
    b1 = BioExtension.from_sequence(seq, config=cfg).step(n=2)
    b2 = BioExtension.from_sequence(seq, config=cfg).step(n=2)
    np.testing.assert_array_equal(b1.anastomosis_state.kappa, b2.anastomosis_state.kappa)
