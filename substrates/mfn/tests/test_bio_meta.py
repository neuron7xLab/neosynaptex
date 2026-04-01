"""Tests for HDV Memory + CMA-ES + MetaOptimizer."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.bio.evolution import (
    DEFAULT_PARAMS,
    BioEvolutionOptimizer,
    params_to_bio_config,
)
from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder
from mycelium_fractal_net.bio.meta import MetaOptimizer


class TestHDVEncoder:
    def test_shape(self) -> None:
        enc = HDVEncoder(n_features=8, D=1000, seed=42)
        hdv = enc.encode(np.random.default_rng(0).standard_normal(8))
        assert hdv.shape == (1000,)
        assert set(np.unique(hdv)).issubset({-1.0, 1.0})

    def test_self_similarity(self) -> None:
        enc = HDVEncoder(n_features=8, D=10000, seed=42)
        f = np.array([1.0, 0.5, -0.3, 0.8, 0.1, 2.0, 1.5, 1.2])
        a = enc.encode(f)
        assert enc.similarity(a, a) == pytest.approx(1.0)

    def test_orthogonality(self) -> None:
        enc = HDVEncoder(n_features=8, D=10000, seed=42)
        rng = np.random.default_rng(0)
        a = enc.encode(rng.standard_normal(8))
        b = enc.encode(rng.standard_normal(8))
        assert abs(enc.similarity(a, b)) < 0.15


class TestBioMemory:
    def test_store_query(self) -> None:
        enc = HDVEncoder(n_features=8, D=1000, seed=0)
        mem = BioMemory(enc, capacity=100)
        assert mem.is_empty
        hdv = enc.encode(np.ones(8))
        mem.store(hdv, fitness=0.75, params={"gamma": 1.0}, step=1)
        assert mem.size == 1
        results = mem.query(hdv, k=1)
        assert len(results) == 1
        assert results[0][1] == pytest.approx(0.75)
        assert results[0][0] == pytest.approx(1.0)

    def test_predict_fitness(self) -> None:
        enc = HDVEncoder(n_features=8, D=1000, seed=1)
        mem = BioMemory(enc, capacity=50)
        rng = np.random.default_rng(0)
        for i in range(10):
            mem.store(
                enc.encode(rng.standard_normal(8)), fitness=rng.uniform(0, 1), params={}, step=i
            )
        pred = mem.predict_fitness(enc.encode(rng.standard_normal(8)), k=3)
        assert 0.0 <= pred <= 1.0

    def test_capacity_eviction(self) -> None:
        enc = HDVEncoder(n_features=4, D=100, seed=0)
        mem = BioMemory(enc, capacity=5)
        rng = np.random.default_rng(0)
        for i in range(10):
            mem.store(enc.encode(rng.standard_normal(4)), fitness=float(i), params={}, step=i)
        assert mem.size == 5

    def test_fitness_landscape(self) -> None:
        enc = HDVEncoder(n_features=4, D=100, seed=0)
        mem = BioMemory(enc, capacity=50)
        rng = np.random.default_rng(0)
        for _ in range(5):
            mem.store(enc.encode(rng.standard_normal(4)), fitness=rng.uniform(0, 1), params={})
        ls = mem.fitness_landscape()
        assert "mean" in ls
        assert "max" in ls


class TestEvolution:
    def test_params_to_config(self) -> None:
        config = params_to_bio_config(DEFAULT_PARAMS)
        assert config is not None
        assert config.physarum.gamma == pytest.approx(1.0)

    def test_single_eval(self) -> None:
        opt = BioEvolutionOptimizer(grid_size=8, steps=10, bio_steps=2, seed=0)
        f = opt.evaluate(DEFAULT_PARAMS)
        assert isinstance(f, float)
        assert 0.0 <= f <= 1.0


class TestMetaOptimizer:
    def test_smoke(self) -> None:
        meta = MetaOptimizer(grid_size=8, steps=10, bio_steps=2, memory_capacity=20, seed=42)
        result = meta.run(n_generations=2, population_size=4, verbose=False)
        assert result.evolution_result.best_fitness >= 0.0
        assert result.total_queries > 0
        assert isinstance(result.summary(), str)
        assert isinstance(result.to_dict(), dict)

    def test_warm_start(self) -> None:
        m1 = MetaOptimizer(grid_size=8, steps=8, bio_steps=2, seed=0)
        m1.run(n_generations=2, population_size=3, verbose=False)
        m2 = MetaOptimizer(grid_size=8, steps=8, bio_steps=2, seed=1)
        m2.memory = m1.memory
        assert m2.memory.size == m1.memory.size
        r2 = m2.run(n_generations=2, population_size=3, verbose=False)
        assert isinstance(r2.summary(), str)
