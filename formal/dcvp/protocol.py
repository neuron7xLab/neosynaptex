"""DCVP v2.1 data structures + configuration.

All dataclasses are frozen and fully immutable; `DCVPConfig` hashes
deterministically so the reproducibility hash is well defined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "DCVPConfig",
    "DCVPReport",
    "DCVPVerdict",
    "PairSpec",
    "PerturbationSpec",
    "CausalityRow",
    "CASCADE_LAG_CV_LIMIT",
    "JITTER_SURVIVAL_FLOOR",
    "ALIGNMENT_SENSITIVITY_LIMIT",
    "GRANGER_P_LIMIT",
    "TE_Z_FLOOR",
]


# ── Hard thresholds from protocol spec ─────────────────────────────────
GRANGER_P_LIMIT: float = 0.01
TE_Z_FLOOR: float = 3.0
TE_NULL_N_MIN: int = 500
CASCADE_LAG_CV_LIMIT: float = 0.15
JITTER_SURVIVAL_FLOOR: float = 0.75
ALIGNMENT_SENSITIVITY_LIMIT: float = 0.20
NAN_SEGMENT_LIMIT: float = 0.05
MIN_SEEDS: int = 5
MIN_PERTURBATION_TYPES: int = 3
MIN_SUBSTRATE_PAIRS: int = 2


PerturbationKind = Literal["noise", "delay", "topology"]


@dataclass(frozen=True)
class PerturbationSpec:
    """One perturbation injected pre-adapter into the raw input stream."""

    kind: PerturbationKind
    sigma: float  # amplitude in [0.1, 1.0] — spec §II
    delay_ticks: int = 0  # used when kind == "delay"
    topology_swap_frac: float = 0.0  # used when kind == "topology"


@dataclass(frozen=True)
class PairSpec:
    """A pair of independent substrates to probe for γ propagation."""

    name: str
    a: str  # adapter identifier resolved by pairs.py registry
    b: str


@dataclass(frozen=True)
class DCVPConfig:
    """Full configuration of a DCVP run. Hashed for reproducibility."""

    pair: PairSpec
    seeds: tuple[int, ...]
    perturbations: tuple[PerturbationSpec, ...]
    n_ticks: int = 256
    te_null_n: int = TE_NULL_N_MIN
    jitter_max_ticks: int = 5
    jitter_dropout: float = 0.05
    granger_max_lag: int = 10
    # Environment isolation
    blas_threads: int = 1
    force_fresh_interpreter: bool = True


@dataclass(frozen=True)
class CausalityRow:
    """Per-seed, per-perturbation causality diagnostics."""

    seed: int
    perturbation: PerturbationSpec
    granger_p: float
    granger_lag: int
    te_z: float
    te_value: float
    cascade_lag: int
    cascade_lag_cv: float
    jitter_survival: float
    alignment_sensitivity: float
    effect_size: float
    baseline_drift: float
    passes: bool
    fail_reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DCVPVerdict:
    """Aggregate verdict: ALL / PARTIAL / ARTIFACT."""

    label: Literal["CAUSAL_INVARIANT", "CONDITIONAL", "ARTIFACT"]
    positive_frac: float  # fraction of perturbed rows that pass
    controls_all_failed: bool  # required for CAUSAL_INVARIANT
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DCVPReport:
    """Full reproducible output bundle — spec §IX."""

    config: DCVPConfig
    gamma_a: dict[int, tuple[float, ...]]  # keyed by seed — raw γ_A(t)
    gamma_b: dict[int, tuple[float, ...]]  # keyed by seed — raw γ_B(t)
    aligned: dict[int, tuple[tuple[float, ...], tuple[float, ...]]]
    causality_matrix: tuple[CausalityRow, ...]
    cascade_profile: tuple[tuple[int, float], ...]  # (lag, effect_size) per seed
    controls: dict[str, bool]  # control_name → TRUE means control falsely signaled causality
    verdict: DCVPVerdict
    reproducibility_hash: str
    code_hash: str
    data_hash: str
