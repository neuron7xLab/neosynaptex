"""Stateful property tests — BioMemory RuleBasedStateMachine.

Hypothesis generates arbitrary sequences of store/query/familiarity operations
and checks invariants after EVERY operation in EVERY sequence.
"""

from __future__ import annotations

import numpy as np
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule


class BioMemoryMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

        self._enc = HDVEncoder(n_features=8, D=500, seed=42)
        self._mem = BioMemory(self._enc, capacity=10)
        self._rng = np.random.default_rng(0)
        self._last_hdv = None

    @rule(fitness=st.floats(0.0, 1.0, allow_nan=False, allow_infinity=False))
    def store_random(self, fitness: float) -> None:
        hdv = self._enc.encode(self._rng.standard_normal(8))
        self._mem.store(hdv, fitness=fitness, params={"f": fitness})
        self._last_hdv = hdv

    @rule(k=st.integers(1, 8))
    def query_random(self, k: int) -> None:
        if self._mem.is_empty:
            return
        q = self._enc.encode(self._rng.standard_normal(8))
        results = self._mem.query(q, k=k)
        assert len(results) <= min(k, self._mem.size)
        for sim, fit, _p, _m in results:
            assert -1.0 <= sim <= 1.0
            assert 0.0 <= fit <= 1.0

    @rule()
    def query_last(self) -> None:
        if self._last_hdv is None or self._mem.is_empty:
            return
        results = self._mem.query(self._last_hdv, k=1)
        if results:
            assert results[0][0] >= 0.5

    @rule()
    def check_familiarity(self) -> None:
        q = self._enc.encode(self._rng.standard_normal(8))
        f = self._mem.superposition_familiarity(q)
        assert 0.0 <= f <= 1.0

    @rule()
    def check_predict(self) -> None:
        if self._mem.is_empty:
            return
        q = self._enc.encode(self._rng.standard_normal(8))
        pred = self._mem.predict_fitness(q, k=3)
        assert 0.0 <= pred <= 1.0 + 1e-9

    @invariant()
    def size_bounded(self) -> None:
        assert self._mem.size <= self._mem.capacity

    @invariant()
    def size_non_negative(self) -> None:
        assert self._mem.size >= 0

    @invariant()
    def superposition_shape(self) -> None:
        assert self._mem._superposition.shape == (self._enc.D,)


TestBioMemoryMachine = BioMemoryMachine.TestCase
TestBioMemoryMachine.settings = settings(max_examples=50, stateful_step_count=20)
