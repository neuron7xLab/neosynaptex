"""Validation tests for memory trace and consolidation ledger.

Parameters
----------
None

Returns
-------
None

Notes
-----
Longer validation tests marked with @pytest.mark.validation.

References
----------
docs/features/memory.md
"""

from __future__ import annotations

import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.memory import ConsolidationLedger, MemoryTrace
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams


@pytest.mark.validation
def test_memory_with_network_states() -> None:
    """Test memory trace with real network states."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=50)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )

    trace = MemoryTrace(capacity=200)

    # run network and store states
    for _ in range(200):
        net.step()
        if _ % 10 == 0:
            trace.tag(net.state.V_mV, importance=0.5)

    state = trace.get_state()
    assert state["count"] == 20


@pytest.mark.validation
def test_consolidation_ledger_long_run() -> None:
    """Test consolidation ledger over long run."""
    ledger = ConsolidationLedger()

    for i in range(1000):
        ledger.record_event(
            gate=0.5 + (i % 10) * 0.05,
            temperature=1.0 - i * 0.0005,
            step=i,
        )

    history = ledger.get_history()
    assert len(history) == 1000

    # hash should be stable
    hash1 = ledger.compute_hash()
    hash2 = ledger.compute_hash()
    assert hash1 == hash2
