"""Tests for structural plasticity engine.

Covers pruning, sprouting, synapse-count bounding, topology tracking,
and the disabled-engine no-op path.
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.connectivity.sparse import SparseConnectivity
from bnsyn.plasticity.structural import (
    StructuralPlasticityEngine,
    StructuralPlasticityParams,
)


def _make_weights(N: int, nE: int, nI: int, rng: np.random.Generator):
    """Build simple excitatory and inhibitory SparseConnectivity objects."""
    # Excitatory: random sparse with some very weak weights
    W_exc_dense = np.zeros((N, nE), dtype=np.float64)
    for i in range(N):
        cols = rng.choice(nE, size=max(1, nE // 5), replace=False)
        W_exc_dense[i, cols] = rng.uniform(0.1, 1.0, size=cols.size)
    W_exc = SparseConnectivity(W_exc_dense, force_format="sparse")

    # Inhibitory: small random
    W_inh_dense = np.zeros((N, nI), dtype=np.float64)
    for i in range(N):
        cols = rng.choice(nI, size=max(1, nI // 5), replace=False)
        W_inh_dense[i, cols] = rng.uniform(0.1, 0.5, size=cols.size)
    W_inh = SparseConnectivity(W_inh_dense, force_format="sparse")

    return W_exc, W_inh


class TestPruning:
    """Test that weak synapses with low calcium are pruned."""

    def test_pruning_removes_weak_synapses(self):
        rng = np.random.default_rng(42)
        N, nE, nI = 50, 40, 10

        W_exc, W_inh = _make_weights(N, nE, nI, rng)

        # Inject very weak weights that should be prunable
        W_dense = W_exc.to_dense()
        connected = np.argwhere(W_dense > 0)
        # Make some synapses very weak (below theta_prune=0.01)
        n_weaken = min(20, len(connected))
        for k in range(n_weaken):
            r, c = connected[k]
            W_dense[r, c] = 0.005  # below theta_prune
        # Rebuild
        nz = np.nonzero(W_dense)
        W_exc.rebuild_from_coo(nz[0].astype(np.int32), nz[1].astype(np.int32), W_dense[nz])

        params = StructuralPlasticityParams(
            enabled=True,
            theta_prune=0.01,
            theta_calcium=0.1,
            update_interval=1,  # execute every step
            rewiring_rate=0.1,  # allow enough rewiring
        )

        engine = StructuralPlasticityEngine(W_exc, W_inh, nE, params, rng)

        # Observe with NO spikes so calcium stays at zero (below theta_calcium)
        pre = np.zeros(N, dtype=bool)
        post = np.zeros(N, dtype=bool)
        for _ in range(10):
            engine.observe(pre, post, dt_ms=1.0)

        report = engine.step()
        assert report.synapses_pruned > 0, "Expected at least one synapse to be pruned"


class TestSprouting:
    """Test that correlated non-connected pairs get new synapses."""

    def test_sprouting_adds_new_synapses(self):
        rng = np.random.default_rng(123)
        N, nE, nI = 30, 20, 10

        W_exc, W_inh = _make_weights(N, nE, nI, rng)

        params = StructuralPlasticityParams(
            enabled=True,
            theta_sprout=0.3,
            tau_correlation_ms=500.0,
            update_interval=1,
            rewiring_rate=0.1,
            w0_sprout=0.05,
        )

        engine = StructuralPlasticityEngine(W_exc, W_inh, nE, params, rng)

        # Find non-connected pairs and make them fire together
        W_dense = W_exc.to_dense()
        non_conn = np.argwhere(W_dense == 0)
        if len(non_conn) == 0:
            pytest.skip("No non-connected pairs available")

        # Pick some non-connected pairs and drive correlated spiking
        targets = non_conn[:20]
        for _ in range(100):
            pre = np.zeros(N, dtype=bool)
            post = np.zeros(N, dtype=bool)
            for row, col in targets:
                if col < nE:
                    pre[col] = True
                post[row] = True
            engine.observe(pre, post, dt_ms=1.0)

        report = engine.step()
        assert report.synapses_sprouted > 0, "Expected at least one synapse to be sprouted"


class TestSynapseCountBounded:
    """Test that synapse count stays within [0.8*initial, 1.2*initial]."""

    def test_synapse_count_bounded(self):
        rng = np.random.default_rng(7)
        N, nE, nI = 40, 30, 10

        W_exc, W_inh = _make_weights(N, nE, nI, rng)

        # Make ALL weights very weak so pruning is aggressive
        W_dense = W_exc.to_dense()
        W_dense[W_dense > 0] = 0.005  # all below theta_prune
        nz = np.nonzero(W_dense)
        W_exc.rebuild_from_coo(nz[0].astype(np.int32), nz[1].astype(np.int32), W_dense[nz])
        initial_nnz = W_exc.metrics.nnz

        params = StructuralPlasticityParams(
            enabled=True,
            theta_prune=0.01,
            theta_calcium=0.1,
            update_interval=1,
            rewiring_rate=0.5,  # aggressive
            synapse_count_band=0.2,
        )

        engine = StructuralPlasticityEngine(W_exc, W_inh, nE, params, rng)

        # Run many pruning steps with no spiking
        pre = np.zeros(N, dtype=bool)
        post = np.zeros(N, dtype=bool)
        for _ in range(200):
            engine.observe(pre, post, dt_ms=1.0)
            report = engine.step()

        lo_bound = int(np.floor(0.8 * initial_nnz))
        assert report.current_nnz_exc >= lo_bound, (
            f"nnz {report.current_nnz_exc} fell below lower bound {lo_bound}"
        )


class TestJaccard:
    """Test that Jaccard distance increases when topology changes."""

    def test_jaccard_increases_with_rewiring(self):
        rng = np.random.default_rng(99)
        N, nE, nI = 30, 20, 10

        W_exc, W_inh = _make_weights(N, nE, nI, rng)

        # Inject weak weights for pruning
        W_dense = W_exc.to_dense()
        connected = np.argwhere(W_dense > 0)
        n_weaken = min(10, len(connected))
        for k in range(n_weaken):
            r, c = connected[k]
            W_dense[r, c] = 0.005
        nz = np.nonzero(W_dense)
        W_exc.rebuild_from_coo(nz[0].astype(np.int32), nz[1].astype(np.int32), W_dense[nz])

        params = StructuralPlasticityParams(
            enabled=True,
            theta_prune=0.01,
            theta_calcium=0.1,
            update_interval=1,
            rewiring_rate=0.1,
        )

        engine = StructuralPlasticityEngine(W_exc, W_inh, nE, params, rng)

        pre = np.zeros(N, dtype=bool)
        post = np.zeros(N, dtype=bool)
        for _ in range(5):
            engine.observe(pre, post, dt_ms=1.0)

        report = engine.step()
        if report.synapses_pruned > 0:
            assert report.topology_delta > 0, (
                "Expected positive Jaccard distance after pruning"
            )
        else:
            # If nothing was pruned, topology_delta should be 0
            assert report.topology_delta == 0.0


class TestDisabled:
    """Test that disabled engine does nothing."""

    def test_no_change_when_disabled(self):
        rng = np.random.default_rng(0)
        N, nE, nI = 20, 15, 5

        W_exc, W_inh = _make_weights(N, nE, nI, rng)
        initial_nnz = W_exc.metrics.nnz

        params = StructuralPlasticityParams(enabled=False)

        engine = StructuralPlasticityEngine(W_exc, W_inh, nE, params, rng)

        pre = np.ones(N, dtype=bool)
        post = np.ones(N, dtype=bool)
        for _ in range(100):
            engine.observe(pre, post, dt_ms=1.0)

        report = engine.step()
        assert report.synapses_pruned == 0
        assert report.synapses_sprouted == 0
        assert report.current_nnz_exc == initial_nnz
