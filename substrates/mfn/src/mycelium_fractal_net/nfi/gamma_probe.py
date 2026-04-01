"""GammaEmergenceProbe — read-only post-hoc analysis of gamma emergence.

NOT part of the closure loop. Receives List[NFIStateContract], never FieldSequence.
Uses the same Theil-Sen + bootstrap estimator as experiments/runner.py.

Ref: Vasylenko (2026)
     Theil (1950), Sen (1968), Efron & Tibshirani (1994)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import warnings

import numpy as np

from .contract import NFIStateContract

__all__ = ["GammaEmergenceProbe", "GammaEmergenceReport"]

_LABEL = Literal["EMERGENT", "NOT_EMERGED", "INSUFFICIENT_DATA"]

_MIN_CONTRACTS = 8  # minimum series length for analysis


@dataclass(frozen=True)
class GammaEmergenceReport:
    """Result of post-hoc gamma emergence analysis.

    label: EMERGENT | NOT_EMERGED | INSUFFICIENT_DATA
    gamma_value: estimated gamma (None if not emerged)
    r_squared: R^2 of the fit (None if not emerged)
    ci95: (lo, hi) bootstrap confidence interval (None if not emerged)
    mechanistic_source: which contract component drives gamma (None if not emerged)
    n_contracts: number of contracts analyzed
    details: dict with full statistical output
    """

    label: str  # _LABEL at runtime
    gamma_value: float | None
    r_squared: float | None
    ci95: tuple[float, float] | None
    mechanistic_source: str | None
    n_contracts: int
    details: dict


class GammaEmergenceProbe:
    """Read-only probe: does gamma emerge as structural property of a contract series?

    Usage:
        probe = GammaEmergenceProbe()
        report = probe.analyze(contracts)
    """

    def __init__(self, n_bootstrap: int = 500, rng_seed: int = 42) -> None:
        self._n_bootstrap = n_bootstrap
        self._rng_seed = rng_seed

    def analyze(self, contracts: list[NFIStateContract]) -> GammaEmergenceReport:
        """Analyze a series of NFIStateContracts for emergent gamma."""
        n = len(contracts)
        if n < _MIN_CONTRACTS:
            return GammaEmergenceReport(
                label="INSUFFICIENT_DATA",
                gamma_value=None,
                r_squared=None,
                ci95=None,
                mechanistic_source=None,
                n_contracts=n,
                details={"reason": f"need >= {_MIN_CONTRACTS} contracts, got {n}"},
            )

        # Extract trajectory vectors from contracts
        energies = [
            c.mfn_snapshot.free_energy if c.mfn_snapshot.free_energy is not None else 0.0
            for c in contracts
        ]
        bettis = [
            float(c.mfn_snapshot.betti_0) if c.mfn_snapshot.betti_0 is not None else 0.0
            for c in contracts
        ]
        d_boxes = [
            c.mfn_snapshot.d_box if c.mfn_snapshot.d_box is not None else 1.0
            for c in contracts
        ]
        coherences = [c.coherence for c in contracts]

        # Build log-log pairs: log(beta_sum) vs log(dH)
        # Same structure as _compute_gamma in experiments/runner.py
        log_dH: list[float] = []
        log_beta: list[float] = []
        for i in range(n):
            for j in range(i + 2, min(i + 6, n)):
                dH = abs(energies[j] - energies[i])
                b_sum = abs(bettis[j]) + abs(bettis[i]) + 1e-12
                if dH > 1e-6:
                    log_dH.append(np.log(dH))
                    log_beta.append(np.log(b_sum))

        if len(log_dH) < 3:
            return GammaEmergenceReport(
                label="INSUFFICIENT_DATA",
                gamma_value=None,
                r_squared=None,
                ci95=None,
                mechanistic_source=None,
                n_contracts=n,
                details={"reason": "insufficient log-log pairs after filtering"},
            )

        x = np.array(log_beta)
        y = np.array(log_dH)
        result = self._theil_sen_bootstrap(x, y)

        # Determine mechanistic source via attribution
        source = self._attribute_source(energies, bettis, d_boxes, coherences, y)

        if result["valid"]:
            return GammaEmergenceReport(
                label="EMERGENT",
                gamma_value=result["gamma"],
                r_squared=result["r2"],
                ci95=(result["ci95_lo"], result["ci95_hi"]),
                mechanistic_source=source,
                n_contracts=n,
                details=result,
            )
        else:
            return GammaEmergenceReport(
                label="NOT_EMERGED",
                gamma_value=result["gamma"],
                r_squared=result["r2"],
                ci95=(result["ci95_lo"], result["ci95_hi"]),
                mechanistic_source=None,
                n_contracts=n,
                details=result,
            )

    def _theil_sen_bootstrap(
        self, x: np.ndarray, y: np.ndarray
    ) -> dict:
        """Theil-Sen + bootstrap CI95 + permutation p-value.

        Re-implements _compute_gamma_robust logic to avoid importing
        from experiments.runner (which has heavier dependencies).
        The algorithm is identical: Theil-Sen median slope, bootstrap CI95,
        permutation p-value, same gate criteria.
        """
        # ASSUMPTION: duplicating the ~30-line algorithm is acceptable
        # to avoid coupling nfi/ to experiments/runner.py
        n = len(x)

        # OLS baseline (suppress RankWarning for near-collinear bootstrap samples)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.exceptions.RankWarning)
            coeffs = np.polyfit(x, y, 1)
        gamma_ols = float(coeffs[0])
        y_pred = np.polyval(coeffs, x)
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2_ols = 1.0 - ss_res / (ss_tot + 1e-12)

        # Theil-Sen: median of pairwise slopes
        slopes: list[float] = []
        for i in range(n):
            for j in range(i + 1, n):
                dx = x[j] - x[i]
                if abs(dx) > 1e-10:
                    slopes.append((y[j] - y[i]) / dx)
        gamma_ts = float(np.median(slopes)) if slopes else gamma_ols
        intercept_ts = float(np.median(y - gamma_ts * x))
        y_pred_ts = gamma_ts * x + intercept_ts
        r2_ts = float(1.0 - np.sum((y - y_pred_ts) ** 2) / (ss_tot + 1e-12))

        # Bootstrap CI95
        rng = np.random.default_rng(self._rng_seed)
        boot_gammas: list[float] = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.exceptions.RankWarning)
            for _ in range(self._n_bootstrap):
                idx = rng.integers(0, n, n)
                xi, yi = x[idx], y[idx]
                if len(np.unique(xi)) >= 2:
                    boot_gammas.append(float(np.polyfit(xi, yi, 1)[0]))

        if len(boot_gammas) >= 10:
            ci_lo = float(np.percentile(boot_gammas, 2.5))
            ci_hi = float(np.percentile(boot_gammas, 97.5))
            se = float(np.std(boot_gammas))
        else:
            ci_lo = ci_hi = gamma_ts
            se = 0.0

        # Permutation p-value
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.exceptions.RankWarning)
            null = [
                float(np.polyfit(x, rng.permutation(y), 1)[0])
                for _ in range(self._n_bootstrap)
            ]
        p_value = max(float(np.mean(np.abs(null) >= abs(gamma_ts))), 1.0 / self._n_bootstrap)

        ci_excludes_zero = not (ci_lo <= 0.0 <= ci_hi)
        gate_pass = (
            ci_excludes_zero
            and p_value < 0.05
            and abs(gamma_ts) > 0.3
            and r2_ts > 0.3
        )

        return {
            "gamma": round(gamma_ts, 4),
            "gamma_ols": round(gamma_ols, 4),
            "r2": round(r2_ts, 6),
            "r2_ols": round(r2_ols, 6),
            "ci95_lo": round(ci_lo, 4),
            "ci95_hi": round(ci_hi, 4),
            "p_value": round(p_value, 6),
            "se": round(se, 4),
            "n_points": len(x),
            "valid": gate_pass,
            "method": "theil_sen_bootstrap",
        }

    @staticmethod
    def _attribute_source(
        energies: list[float],
        bettis: list[float],
        d_boxes: list[float],
        coherences: list[float],
        log_dH: np.ndarray,
    ) -> str:
        """Determine which component drives gamma via max |correlation|.

        # APPROXIMATION: Pearson correlation, not interventional causation.
        """
        n = min(len(log_dH), len(energies))
        if n < 3:
            return "undetermined"

        # Truncate all to same length as log_dH
        candidates = {
            "free_energy_trajectory": np.array(energies[:n]),
            "betti_trajectory": np.array(bettis[:n]),
            "d_box_trajectory": np.array(d_boxes[:n]),
            "coherence": np.array(coherences[:n]),
        }

        best_name = "undetermined"
        best_corr = 0.0
        target = log_dH[:n]

        for name, arr in candidates.items():
            if np.std(arr) < 1e-12 or np.std(target) < 1e-12:
                continue
            corr = abs(float(np.corrcoef(arr, target)[0, 1]))
            if corr > best_corr:
                best_corr = corr
                best_name = name

        return best_name
