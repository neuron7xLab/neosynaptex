"""Negative controls — spec §VI.

Four controls; ALL of them must FAIL the causality battery for the
positive verdict to stand. If any one of them produces a causal-looking
signal, the entire candidate is labeled ARTIFACT.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from formal.dcvp.causality import (
    granger_robust,
    te_null,
)
from formal.dcvp.protocol import GRANGER_P_LIMIT, TE_Z_FLOOR

__all__ = [
    "ControlResult",
    "randomized_source",
    "time_reversed",
    "cross_run_mismatch",
    "synthetic_noise_only",
    "run_all_controls",
]


@dataclass(frozen=True)
class ControlResult:
    name: str
    signaled_causality: bool  # TRUE = control failed (contaminating)
    p_value: float
    te_z: float


def _battery(
    source: np.ndarray,
    target: np.ndarray,
    rng: np.random.Generator,
    granger_max_lag: int,
    te_null_n: int,
) -> tuple[float, float]:
    seed = int(rng.integers(0, 2**31 - 1))
    p, _ = granger_robust(source, target, max_lag=granger_max_lag, seed=seed)
    obs, mu, sigma = te_null(source, target, n_surrogates=te_null_n, rng=rng)
    z = (obs - mu) / (sigma + 1e-12)
    return p, float(z)


def randomized_source(
    source: np.ndarray,
    target: np.ndarray,
    rng: np.random.Generator,
    granger_max_lag: int = 5,
    te_null_n: int = 200,
) -> ControlResult:
    """Shuffle A across time; any surviving A→B is spurious."""
    shuffled = rng.permutation(np.asarray(source, dtype=np.float64))
    p, z = _battery(shuffled, target, rng, granger_max_lag, te_null_n)
    return ControlResult(
        name="randomized_source",
        signaled_causality=(p < GRANGER_P_LIMIT and z > TE_Z_FLOOR),
        p_value=p,
        te_z=z,
    )


def time_reversed(
    source: np.ndarray,
    target: np.ndarray,
    rng: np.random.Generator,
    granger_max_lag: int = 5,
    te_null_n: int = 200,
) -> ControlResult:
    """Reverse the γ stream; physical causality must break under time flip."""
    p, z = _battery(
        np.asarray(source, dtype=np.float64)[::-1],
        np.asarray(target, dtype=np.float64)[::-1],
        rng,
        granger_max_lag,
        te_null_n,
    )
    return ControlResult(
        name="time_reversed",
        signaled_causality=(p < GRANGER_P_LIMIT and z > TE_Z_FLOOR),
        p_value=p,
        te_z=z,
    )


def cross_run_mismatch(
    source_run1: np.ndarray,
    target_run2: np.ndarray,
    rng: np.random.Generator,
    granger_max_lag: int = 5,
    te_null_n: int = 200,
) -> ControlResult:
    """A from run-1 paired with B from run-2; no shared causal history."""
    p, z = _battery(source_run1, target_run2, rng, granger_max_lag, te_null_n)
    return ControlResult(
        name="cross_run_mismatch",
        signaled_causality=(p < GRANGER_P_LIMIT and z > TE_Z_FLOOR),
        p_value=p,
        te_z=z,
    )


def synthetic_noise_only(
    n_ticks: int,
    rng: np.random.Generator,
    granger_max_lag: int = 5,
    te_null_n: int = 200,
) -> ControlResult:
    """Pure white-noise pipeline; any apparent causality is false discovery."""
    a = rng.normal(size=n_ticks)
    b = rng.normal(size=n_ticks)
    p, z = _battery(a, b, rng, granger_max_lag, te_null_n)
    return ControlResult(
        name="synthetic_noise_only",
        signaled_causality=(p < GRANGER_P_LIMIT and z > TE_Z_FLOOR),
        p_value=p,
        te_z=z,
    )


def run_all_controls(
    gamma_a_run1: np.ndarray,
    gamma_b_run1: np.ndarray,
    gamma_a_run2: np.ndarray,
    gamma_b_run2: np.ndarray,
    rng: np.random.Generator,
    n_ticks: int,
    granger_max_lag: int = 5,
    te_null_n: int = 200,
) -> dict[str, ControlResult]:
    """Run all four controls. Each returned value flags contamination."""
    return {
        "randomized_source": randomized_source(
            gamma_a_run1, gamma_b_run1, rng, granger_max_lag, te_null_n
        ),
        "time_reversed": time_reversed(gamma_a_run1, gamma_b_run1, rng, granger_max_lag, te_null_n),
        "cross_run_mismatch": cross_run_mismatch(
            gamma_a_run1, gamma_b_run2, rng, granger_max_lag, te_null_n
        ),
        "synthetic_noise_only": synthetic_noise_only(n_ticks, rng, granger_max_lag, te_null_n),
    }
