"""Grid orchestrator for the estimator admissibility trial.

Sweeps every (estimator, γ_true, N, σ) cell, draws M replicates per
cell, computes the 8 per-cell metrics, and returns one structured
result dict ready to be canonicalised + hashed.

The runtime here is O(N_estimators × |γ_grid| × |N_grid| × |σ_grid|
× M × cost_per_fit). At smoke (M=100) this is meant to fit in
~5–15 minutes; at canonical (M=1000) it is ~30 minutes per estimator
in parallel. The orchestrator is single-threaded by design — CI
parallelises across estimators via the workflow matrix, not inside
this module.

The output dict is the *only* thing the verdict module consumes;
keeping it canonical (sorted nested keys, no NaN/Inf in payload-
level scalars) is a hard contract.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np

from tools.phase_3.admissibility.estimators import (
    ESTIMATOR_NAMES,
    ESTIMATOR_REGISTRY,
    EstimatorResult,
)
from tools.phase_3.admissibility.metrics import (
    CellMetrics,
    cell_metrics,
    false_positive_rate_on_null,
)
from tools.phase_3.admissibility.synthetic_data import synthesise, synthesise_null

__all__ = [
    "DEFAULT_GAMMA_GRID",
    "DEFAULT_N_GRID",
    "DEFAULT_SIGMA_GRID",
    "PRIMARY_SIGMA",
    "TrialConfig",
    "run_trial",
]


#: Default γ_true sweep. Spans low (sub-linear), mid, and super-linear
#: regimes. The Phase 3 substrate findings cluster around 1.0 so that
#: value sits at the centre of the grid.
DEFAULT_GAMMA_GRID: tuple[float, ...] = (0.25, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0)

#: Default trajectory-length sweep. N=20 is below the canonical
#: estimator's reported breakdown; N=1024 is the largest length where
#: O(N²) Theil–Sen still fits in the smoke time budget.
DEFAULT_N_GRID: tuple[int, ...] = (20, 64, 128, 256, 512, 1024)

#: Default noise sweep. σ=0 is the noise-free oracle; σ=0.1 is the
#: primary report regime; σ=0.2 is the high-noise stress regime.
DEFAULT_SIGMA_GRID: tuple[float, ...] = (0.0, 0.05, 0.1, 0.2)

PRIMARY_SIGMA: float = 0.1


@dataclass(frozen=True)
class TrialConfig:
    """Frozen configuration for a single trial run.

    All randomness is parametrised by ``seed_base``: replicate ``k``
    of cell ``(estimator, γ_true, N, σ)`` is synthesised with seed
    ``seed_base + offset(γ_true, N, σ, k)``. Two trials with the same
    config produce byte-identical results.
    """

    gamma_grid: tuple[float, ...]
    n_grid: tuple[int, ...]
    sigma_grid: tuple[float, ...]
    estimator_names: tuple[str, ...]
    m_replicates: int
    seed_base: int
    n_replicates_for_window_metrics: int


def _seed_for(seed_base: int, gamma: float, n: int, sigma: float, k: int) -> int:
    """Deterministic per-replicate seed.

    We hash the (γ, N, σ, k) tuple to a 32-bit integer so that
    every replicate has a unique stream that is also reproducible
    across runs. Float bit-patterns are taken via ``struct``-free
    ``np.float64`` view to avoid any platform-endianness issue.
    """
    # Use repr for floats; np.float64.tobytes is portable in CPython
    # but using a tuple-hash via Python's stable hash keyed on a
    # public PRNG seeds the stream cleanly without int overflow.
    g_bits = int.from_bytes(np.float64(gamma).tobytes(), "little")
    s_bits = int.from_bytes(np.float64(sigma).tobytes(), "little")
    return (seed_base ^ (g_bits << 1) ^ (n << 17) ^ (s_bits << 3) ^ k) & 0xFFFFFFFF


def _fit_one_cell(
    estimator_name: str,
    gamma_true: float,
    n: int,
    sigma: float,
    m: int,
    seed_base: int,
    *,
    null_cell: bool,
) -> tuple[list[EstimatorResult], list[np.ndarray], list[np.ndarray]]:
    """Draw M replicates for a cell and return γ̂ + log-axis arrays.

    Returns:
        estimates : list[EstimatorResult] of length M.
        log_c_reps, log_k_reps : list[np.ndarray] of length M.

    NaN-on-fit replicates are returned as NaN ``EstimatorResult`` and
    counted as such by the metrics layer.
    """
    fit_fn = ESTIMATOR_REGISTRY[estimator_name]
    estimates: list[EstimatorResult] = []
    log_c_reps: list[np.ndarray] = []
    log_k_reps: list[np.ndarray] = []
    for k in range(m):
        seed = _seed_for(seed_base, gamma_true, n, sigma, k)
        if null_cell:
            sample = synthesise_null(n=n, sigma=sigma, seed=seed)
        else:
            sample = synthesise(gamma_true=gamma_true, n=n, sigma=sigma, seed=seed)
        log_c = np.log(sample.C)
        log_k = np.log(sample.K)
        log_c_reps.append(log_c)
        log_k_reps.append(log_k)
        try:
            res = fit_fn(log_c, log_k)
        except (ValueError, RuntimeError, np.linalg.LinAlgError):
            res = EstimatorResult(
                gamma=float("nan"),
                ci95_low=float("nan"),
                ci95_high=float("nan"),
            )
        estimates.append(res)
    return estimates, log_c_reps, log_k_reps


def _metrics_to_dict(m: CellMetrics, fpr_null: float | None) -> dict[str, float | int]:
    """Render a CellMetrics into a JSON-serialisable dict.

    NaN in the payload is forbidden by the canonicaliser
    (``allow_nan=False``), so we map non-finite values to ``None``-like
    sentinel strings. We use the literal ``"nan"`` string — verdict
    consumers must explicitly check for the string before applying
    inequalities. The structure carries enough redundancy that a
    silent NaN-coercion bug would surface as a verdict mismatch in
    the test battery.
    """

    def _scalar(x: float) -> float | str:
        if math.isnan(x) or math.isinf(x):
            return "nan"
        return float(x)

    out: dict[str, float | int] = {
        "bias": _scalar(m.bias),  # type: ignore[dict-item]
        "variance": _scalar(m.variance),  # type: ignore[dict-item]
        "rmse": _scalar(m.rmse),  # type: ignore[dict-item]
        "ci95_coverage": _scalar(m.ci95_coverage),  # type: ignore[dict-item]
        "window_delta_max": _scalar(m.window_delta_max),  # type: ignore[dict-item]
        "leave_one_window_out_drift": _scalar(m.leave_one_window_out_drift),  # type: ignore[dict-item]
        "bootstrap_slope_dispersion": _scalar(m.bootstrap_slope_dispersion),  # type: ignore[dict-item]
        "n_replicates_used": int(m.n_replicates_used),
        "nan_fraction": _scalar(m.nan_fraction),  # type: ignore[dict-item]
    }
    if fpr_null is None:
        out["false_positive_rate_on_null"] = "nan"  # type: ignore[assignment]
    else:
        out["false_positive_rate_on_null"] = _scalar(fpr_null)  # type: ignore[assignment]
    return out


def run_trial(config: TrialConfig) -> dict[str, Any]:
    """Execute the full grid sweep and return a structured results dict.

    Output schema (top-level):

        {
          "config": { ... full echo ... },
          "cells": {
            "<estimator>": {
              "<γ_true>": {
                "<N>": {
                  "<σ>": { 8 metrics + housekeeping }
                }
              }
            }
          }
        }

    Numerical keys are stringified deterministically (``repr``-stable
    for ints; canonical ``f"{x:g}"`` for floats) so the resulting JSON
    is sort-key stable across re-runs.
    """
    # First pass: estimate γ̂ on all power-law cells AND compute
    # γ_true=0 null cells for each (N, σ) — those drive the FPR metric.

    cells: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}

    # Pre-compute null FPR per estimator × (N, σ) so the substrate
    # cells (γ_true > 0) can carry the matching FPR for sanity, while
    # the canonical FPR is a function of (estimator, N, σ) only.
    null_fpr: dict[tuple[str, int, str], float] = {}
    for est in config.estimator_names:
        for n in config.n_grid:
            for sigma in config.sigma_grid:
                est_results, _, _ = _fit_one_cell(
                    estimator_name=est,
                    gamma_true=0.0,
                    n=n,
                    sigma=sigma,
                    m=config.m_replicates,
                    seed_base=config.seed_base,
                    null_cell=True,
                )
                null_fpr[(est, n, _fmt_float(sigma))] = false_positive_rate_on_null(est_results)

    for est in config.estimator_names:
        cells[est] = {}
        for gamma_true in config.gamma_grid:
            g_key = _fmt_float(gamma_true)
            cells[est][g_key] = {}
            for n in config.n_grid:
                n_key = str(int(n))
                cells[est][g_key][n_key] = {}
                for sigma in config.sigma_grid:
                    s_key = _fmt_float(sigma)
                    est_results, log_c_reps, log_k_reps = _fit_one_cell(
                        estimator_name=est,
                        gamma_true=gamma_true,
                        n=n,
                        sigma=sigma,
                        m=config.m_replicates,
                        seed_base=config.seed_base,
                        null_cell=False,
                    )
                    metrics = cell_metrics(
                        gamma_true=gamma_true,
                        estimates=est_results,
                        log_c_replicates=log_c_reps,
                        log_k_replicates=log_k_reps,
                        fit_fn=ESTIMATOR_REGISTRY[est],
                        n_replicates_for_window_metrics=config.n_replicates_for_window_metrics,
                    )
                    cells[est][g_key][n_key][s_key] = _metrics_to_dict(
                        metrics,
                        null_fpr[(est, n, s_key)],
                    )

    return {
        "config": {
            "gamma_grid": list(config.gamma_grid),
            "n_grid": list(config.n_grid),
            "sigma_grid": list(config.sigma_grid),
            "estimator_names": list(config.estimator_names),
            "m_replicates": int(config.m_replicates),
            "seed_base": int(config.seed_base),
            "n_replicates_for_window_metrics": int(config.n_replicates_for_window_metrics),
        },
        "cells": cells,
    }


def _fmt_float(x: float) -> str:
    """Stable float→str for use as a JSON key.

    ``f"{x:g}"`` collapses 1.0 to "1", which is fine, but loses the
    distinction between 0.05 and 5e-2; we use ``repr`` of a float that
    has been rounded to 9 significant digits, which is round-trip safe
    for double precision and stable across Python versions.
    """
    if x == 0.0:
        return "0.0"
    return f"{x:.9g}"


def trial_result_keys(results: dict[str, Any]) -> Iterable[tuple[str, str, str, str]]:
    """Iterate over (estimator, γ_key, N_key, σ_key) tuples.

    Convenience iterator for tests / consumers that want to walk the
    full cell grid without re-deriving the keying convention.
    """
    cells = results["cells"]
    for est, gamma_map in cells.items():
        for g_key, n_map in gamma_map.items():
            for n_key, sigma_map in n_map.items():
                for s_key in sigma_map:
                    yield (est, g_key, n_key, s_key)


# Public alias retained for clarity in CLI / tests.
ALL_ESTIMATORS: tuple[str, ...] = ESTIMATOR_NAMES
