"""Distributed Causal Validation Protocol (DCVP) v2.1.

Validates that γ propagation between two substrates is a genuine causal
invariant, not a shared-environment artifact. Hard constraints:

* zero shared runtime (separate processes, isolated RNGs, BLAS thread pinning)
* data-level perturbation sweep (σ ∈ [0.1, 1.0], 3+ perturbation types)
* DTW alignment with jitter robustness
* causality battery: Granger p<0.01, TE z>3.0, stable cascade lag, jitter survival ≥0.75
* four negative controls (randomize, time-reverse, cross-run mismatch, noise-only)
* reproducibility hash over config + seeds + data digest + source digest

Principle: do not prove γ — destroy every alternative explanation.
"""

from __future__ import annotations

from formal.dcvp.protocol import (
    DCVPConfig,
    DCVPReport,
    DCVPVerdict,
    PairSpec,
    PerturbationSpec,
)

__all__ = [
    "DCVPConfig",
    "DCVPReport",
    "DCVPVerdict",
    "PairSpec",
    "PerturbationSpec",
]
