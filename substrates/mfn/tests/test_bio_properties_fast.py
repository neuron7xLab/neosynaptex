"""Property tests — FAST profile (20 examples on PR, 500 nightly).

Profile controlled by BIO_HYPOTHESIS_PROFILE env var (default: fast).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

_float_vec = arrays(
    dtype=np.float64,
    shape=(8,),
    elements=st.floats(-10.0, 10.0, allow_nan=False, allow_infinity=False),
)
_any_vec = arrays(
    dtype=np.float64,
    shape=(8,),
    elements=st.floats(allow_nan=True, allow_infinity=True),
)
_bio_params = arrays(
    dtype=np.float64,
    shape=(8,),
    elements=st.one_of(
        st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
        st.just(float("nan")),
        st.just(float("inf")),
        st.just(float("-inf")),
    ),
)


@given(_any_vec)
def test_encode_always_pm1(v: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    hdv = HDVEncoder(n_features=8, D=500, seed=0).encode(v)
    assert set(np.unique(hdv)).issubset({-1.0, 0.0, 1.0})


@given(_float_vec)
def test_similarity_reflexive(v: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    enc = HDVEncoder(n_features=8, D=500, seed=0)
    assert enc.similarity(enc.encode(v), enc.encode(v)) == pytest.approx(1.0)


@given(_float_vec, _float_vec)
def test_similarity_bounded(v1: np.ndarray, v2: np.ndarray) -> None:
    from mycelium_fractal_net.bio.memory import HDVEncoder

    enc = HDVEncoder(n_features=8, D=1000, seed=1)
    sim = enc.similarity(enc.encode(v1), enc.encode(v2))
    assert -1.0 <= sim <= 1.0


@given(_bio_params)
def test_params_always_finite(p: np.ndarray) -> None:
    from mycelium_fractal_net.bio.evolution import params_to_bio_config

    cfg = params_to_bio_config(p)
    assert math.isfinite(cfg.physarum.gamma)
    assert math.isfinite(cfg.physarum.alpha)
    assert math.isfinite(cfg.anastomosis.D_tip)
    assert math.isfinite(cfg.fhn.a)
    assert math.isfinite(cfg.fhn.Du)
    assert math.isfinite(cfg.chemotaxis.chi0)
    assert math.isfinite(cfg.dispersal.alpha_levy)


@given(_bio_params)
def test_params_within_bounds(p: np.ndarray) -> None:
    from mycelium_fractal_net.bio.evolution import PARAM_BOUNDS, params_to_bio_config

    cfg = params_to_bio_config(p)
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


@given(st.integers(1, 30), st.integers(0, 60))
def test_memory_size_bounded(cap: int, n: int) -> None:
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=8, D=200, seed=0)
    mem = BioMemory(enc, capacity=cap)
    rng = np.random.default_rng(0)
    for _ in range(n):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    assert mem.size <= cap


@given(st.integers(5, 30))
def test_familiarity_bounded(n: int) -> None:
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=8, D=500, seed=2)
    mem = BioMemory(enc, capacity=50)
    rng = np.random.default_rng(3)
    for _ in range(n):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    for _ in range(10):
        assert 0.0 <= mem.superposition_familiarity(enc.encode(rng.standard_normal(8))) <= 1.0
