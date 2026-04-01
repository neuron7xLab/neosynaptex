"""Structural plasticity engine for activity-dependent rewiring.

Implements pruning of weak/inactive synapses and sprouting of new
synapses between correlated but unconnected neuron pairs.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from bnsyn.connectivity.sparse import SparseConnectivity

BoolArray = NDArray[np.bool_]
Float64Array = NDArray[np.float64]


@dataclass(frozen=True)
class StructuralPlasticityParams:
    """Parameters controlling structural plasticity dynamics."""

    enabled: bool = False
    theta_prune: float = 0.01
    theta_calcium: float = 0.1
    theta_sprout: float = 0.3
    tau_calcium_ms: float = 1000.0
    tau_correlation_ms: float = 500.0
    rewiring_rate: float = 0.001
    w0_sprout: float = 0.05
    synapse_count_band: float = 0.2
    update_interval: int = 50


@dataclass(frozen=True)
class StructuralPlasticityReport:
    """Report from a single structural plasticity step."""

    synapses_pruned: int
    synapses_sprouted: int
    current_nnz_exc: int
    current_nnz_inh: int
    density_exc: float
    density_inh: float
    topology_delta: float  # Jaccard distance from initial connectivity


class StructuralPlasticityEngine:
    """Activity-dependent structural rewiring of excitatory synapses.

    Prunes weak, low-activity synapses and sprouts new ones between
    correlated but unconnected neuron pairs.

    Parameters
    ----------
    W_exc : SparseConnectivity
        Excitatory weight matrix, shape (N, nE) -- post x pre.
    W_inh : SparseConnectivity
        Inhibitory weight matrix, shape (N, nI) -- post x pre. Not modified.
    nE : int
        Number of excitatory neurons (pre-synaptic dimension of W_exc).
    params : StructuralPlasticityParams
        Plasticity hyperparameters.
    rng : np.random.Generator
        Random number generator for tie-breaking.
    """

    def __init__(
        self,
        W_exc: SparseConnectivity,
        W_inh: SparseConnectivity,
        nE: int,
        params: StructuralPlasticityParams,
        rng: np.random.Generator,
    ) -> None:
        self.W_exc = W_exc
        self.W_inh = W_inh
        self.nE = nE
        self.params = params
        self.rng = rng

        N = W_exc.shape[0]
        self.N = N

        # Dense view for tracking
        W_dense = W_exc.to_dense()
        self.initial_mask: BoolArray = W_dense > 0
        self.initial_nnz: int = int(np.count_nonzero(W_dense))

        # Calcium proxy: EMA of co-spiking per synapse slot, shape (N, nE)
        self.calcium_proxy: Float64Array = np.zeros((N, nE), dtype=np.float64)

        # Correlation proxy: EMA for non-connected pairs, shape (N, nE)
        self.correlation_proxy: Float64Array = np.zeros((N, nE), dtype=np.float64)

        self._step_counter: int = 0
        self._max_rewirings: int = max(1, math.floor(N * params.rewiring_rate))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(
        self, pre_spiked: BoolArray, post_spiked: BoolArray, dt_ms: float
    ) -> None:
        """Record spike observations for calcium and correlation tracking.

        Parameters
        ----------
        pre_spiked : BoolArray
            Boolean spike vector for all neurons (length >= nE).
            Only the first nE entries (excitatory) are used as pre-synaptic.
        post_spiked : BoolArray
            Boolean spike vector for all N post-synaptic neurons.
        dt_ms : float
            Time step in milliseconds.
        """
        if not self.params.enabled:
            return

        p = self.params
        decay_ca = math.exp(-dt_ms / p.tau_calcium_ms)
        decay_corr = math.exp(-dt_ms / p.tau_correlation_ms)

        # Decay
        self.calcium_proxy *= decay_ca
        self.correlation_proxy *= decay_corr

        # Pre-synaptic excitatory spikes (columns of W_exc)
        pre_exc = pre_spiked[: self.nE]  # shape (nE,)
        # Post-synaptic spikes (rows of W_exc)
        post = post_spiked  # shape (N,)

        # Outer product: which (post_j, pre_i) pairs both spiked
        # co_spike[j, i] = post[j] & pre_exc[i]
        post_idx = np.where(post)[0]
        pre_idx = np.where(pre_exc)[0]

        if post_idx.size > 0 and pre_idx.size > 0:
            # Get current connectivity mask
            W_dense = self.W_exc.to_dense()
            connected = W_dense > 0  # shape (N, nE)

            # Update calcium for connected pairs that co-spiked
            for j in post_idx:
                self.calcium_proxy[j, pre_idx] += 1.0

            # Update correlation for non-connected pairs that co-spiked
            for j in post_idx:
                non_conn_mask = ~connected[j, pre_idx]
                non_conn_pre = pre_idx[non_conn_mask]
                if non_conn_pre.size > 0:
                    self.correlation_proxy[j, non_conn_pre] += 1.0

    def step(self) -> StructuralPlasticityReport:
        """Execute one structural plasticity step.

        Returns
        -------
        StructuralPlasticityReport
            Summary of pruning/sprouting actions taken.
        """
        self._step_counter += 1

        W_dense = self.W_exc.to_dense()
        current_nnz_exc = int(np.count_nonzero(W_dense))

        if (
            not self.params.enabled
            or self._step_counter % self.params.update_interval != 0
        ):
            current_mask = W_dense > 0
            jd = self._jaccard_distance(current_mask)
            return StructuralPlasticityReport(
                synapses_pruned=0,
                synapses_sprouted=0,
                current_nnz_exc=current_nnz_exc,
                current_nnz_inh=self.W_inh.metrics.nnz,
                density_exc=self.W_exc.metrics.density,
                density_inh=self.W_inh.metrics.density,
                topology_delta=jd,
            )

        p = self.params
        pruned = 0
        sprouted = 0
        changed = False

        # Bounds on synapse count
        nnz_lo = int(math.floor((1.0 - p.synapse_count_band) * self.initial_nnz))
        nnz_hi = int(math.ceil((1.0 + p.synapse_count_band) * self.initial_nnz))

        # --- Pruning ---
        if current_nnz_exc > nnz_lo:
            # Candidates: connected, weak weight, low calcium
            connected = W_dense > 0
            weak = np.abs(W_dense) < p.theta_prune
            low_calcium = self.calcium_proxy < p.theta_calcium
            prune_candidates = connected & weak & low_calcium

            prune_rows, prune_cols = np.where(prune_candidates)
            if prune_rows.size > 0:
                # Limit to max_rewirings and synapse band
                max_prune = min(
                    self._max_rewirings,
                    prune_rows.size,
                    current_nnz_exc - nnz_lo,
                )
                if max_prune > 0:
                    # Random subset if too many candidates
                    if prune_rows.size > max_prune:
                        idx = self.rng.choice(
                            prune_rows.size, max_prune, replace=False
                        )
                        prune_rows = prune_rows[idx]
                        prune_cols = prune_cols[idx]
                    else:
                        prune_rows = prune_rows[:max_prune]
                        prune_cols = prune_cols[:max_prune]

                    W_dense[prune_rows, prune_cols] = 0.0
                    self.calcium_proxy[prune_rows, prune_cols] = 0.0
                    pruned = len(prune_rows)
                    current_nnz_exc -= pruned
                    changed = True

        # --- Sprouting ---
        if current_nnz_exc < nnz_hi:
            not_connected = W_dense == 0
            high_corr = self.correlation_proxy > p.theta_sprout
            sprout_candidates = not_connected & high_corr

            sprout_rows, sprout_cols = np.where(sprout_candidates)
            if sprout_rows.size > 0:
                max_sprout = min(
                    self._max_rewirings,
                    sprout_rows.size,
                    nnz_hi - current_nnz_exc,
                )
                if max_sprout > 0:
                    if sprout_rows.size > max_sprout:
                        idx = self.rng.choice(
                            sprout_rows.size, max_sprout, replace=False
                        )
                        sprout_rows = sprout_rows[idx]
                        sprout_cols = sprout_cols[idx]
                    else:
                        sprout_rows = sprout_rows[:max_sprout]
                        sprout_cols = sprout_cols[:max_sprout]

                    W_dense[sprout_rows, sprout_cols] = p.w0_sprout
                    self.correlation_proxy[sprout_rows, sprout_cols] = 0.0
                    sprouted = len(sprout_rows)
                    current_nnz_exc += sprouted
                    changed = True

        # Rebuild W_exc from modified dense if anything changed
        if changed:
            nz = np.nonzero(W_dense)
            self.W_exc.rebuild_from_coo(
                nz[0].astype(np.int32),
                nz[1].astype(np.int32),
                W_dense[nz],
            )

        current_mask = W_dense > 0
        jd = self._jaccard_distance(current_mask)

        return StructuralPlasticityReport(
            synapses_pruned=pruned,
            synapses_sprouted=sprouted,
            current_nnz_exc=self.W_exc.metrics.nnz,
            current_nnz_inh=self.W_inh.metrics.nnz,
            density_exc=self.W_exc.metrics.density,
            density_inh=self.W_inh.metrics.density,
            topology_delta=jd,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _jaccard_distance(self, current_mask: BoolArray) -> float:
        """Compute Jaccard distance between initial and current connectivity."""
        intersection = int(np.count_nonzero(self.initial_mask & current_mask))
        union = int(np.count_nonzero(self.initial_mask | current_mask))
        if union == 0:
            return 0.0
        return 1.0 - intersection / union
