"""CMA-ES parameter optimizer for BioConfig.

Ref: Hansen & Ostermeier (2001) — CMA-ES
     cmaes package (CyberAgent) — ask-and-tell interface

8-dim parameter space over bio mechanism configs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "DEFAULT_PARAMS",
    "PARAM_BOUNDS",
    "PARAM_NAMES",
    "BioEvolutionOptimizer",
    "BioEvolutionResult",
    "compute_fitness",
    "params_to_bio_config",
]

PARAM_NAMES = [
    "physarum_gamma",
    "physarum_alpha",
    "anastomosis_gamma",
    "anastomosis_D_tip",
    "fhn_a",
    "fhn_Du",
    "chemotaxis_chi0",
    "dispersal_alpha_levy",
]

PARAM_BOUNDS = np.array(
    [
        [0.3, 1.8],
        [0.001, 0.1],
        [0.01, 0.2],
        [0.01, 0.2],
        [0.05, 0.4],
        [0.1, 5.0],
        [0.5, 5.0],
        [1.1, 1.9],
    ],
    dtype=np.float64,
)

DEFAULT_PARAMS = np.array([1.0, 0.01, 0.05, 0.05, 0.13, 1.0, 2.0, 1.5])


def params_to_bio_config(params: np.ndarray) -> Any:
    """Convert flat parameter vector to BioConfig with NaN/Inf safety."""
    from mycelium_fractal_net.bio.anastomosis import AnastomosisConfig
    from mycelium_fractal_net.bio.chemotaxis import ChemotaxisConfig
    from mycelium_fractal_net.bio.dispersal import DispersalConfig
    from mycelium_fractal_net.bio.extension import BioConfig
    from mycelium_fractal_net.bio.fhn import FHNConfig
    from mycelium_fractal_net.bio.physarum import PhysarumConfig

    safe = np.where(np.isfinite(params), params, DEFAULT_PARAMS)
    p = np.clip(safe, PARAM_BOUNDS[:, 0], PARAM_BOUNDS[:, 1])
    return BioConfig(
        physarum=PhysarumConfig(gamma=float(p[0]), alpha=float(p[1])),
        anastomosis=AnastomosisConfig(gamma_anastomosis=float(p[2]), D_tip=float(p[3])),
        fhn=FHNConfig(a=float(p[4]), Du=float(p[5])),
        chemotaxis=ChemotaxisConfig(chi0=float(p[6])),
        dispersal=DispersalConfig(alpha_levy=float(p[7])),
    )


def compute_fitness(bio_report: Any, diagnosis: Any) -> float:
    """Additive fitness — each component contributes independently.

    Components (all in [0, 1], weighted sum):
        ews_stability:   1 - ews_score (lower EWS = more stable = better)
        causal:          causal gate pass rate
        transport_diff:  physarum conductivity differentiation
        growth:          hyphal density growth proxy
        spiking_ok:      FHN spiking near optimal 8%
    """
    ews = float(diagnosis.warning.ews_score) if diagnosis else 0.5
    causal_val = diagnosis.causal.decision.value if diagnosis else "degraded"
    causal = {"pass": 1.0, "degraded": 0.7, "fail": 0.0}.get(causal_val, 0.5)

    spiking = float(bio_report.fhn.get("spiking_fraction", 0.0))
    spiking_ok = max(0.0, 1.0 - abs(spiking - 0.08) * 5.0)

    d_max = float(bio_report.physarum.get("conductivity_max", 1.0))
    d_mean = float(bio_report.physarum.get("conductivity_mean", 1.0))
    transport_diff = min(1.0, max(0.0, (d_max - d_mean) / (d_mean + 1e-6)))

    hyphae = float(bio_report.anastomosis.get("hyphal_density_mean", 0.0))
    growth = min(1.0, hyphae * 200.0)

    f = (
        0.30 * (1.0 - ews)
        + 0.25 * causal
        + 0.20 * transport_diff
        + 0.15 * growth
        + 0.10 * spiking_ok
    )
    return float(np.clip(f, 0.0, 1.0))


@dataclass
class BioEvolutionResult:
    """Bio evolution result."""

    best_params: np.ndarray
    best_fitness: float
    best_config: Any
    generation_history: list[dict[str, Any]]
    total_evaluations: int
    converged: bool
    elapsed_seconds: float

    def summary(self) -> str:
        """Summary."""
        return (
            f"[EVOLUTION] best={self.best_fitness:.4f} evals={self.total_evaluations} "
            f"gen={len(self.generation_history)} ({self.elapsed_seconds:.1f}s)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "best_params": {
                PARAM_NAMES[i]: float(self.best_params[i]) for i in range(len(PARAM_NAMES))
            },
            "best_fitness": self.best_fitness,
            "total_evaluations": self.total_evaluations,
            "converged": self.converged,
            "elapsed_seconds": self.elapsed_seconds,
        }


class BioEvolutionOptimizer:
    """Bio evolution optimizer."""

    def __init__(
        self, grid_size: int = 16, steps: int = 20, bio_steps: int = 5, seed: int = 42
    ) -> None:
        self.grid_size = grid_size
        self.steps = steps
        self.bio_steps = bio_steps
        self.seed = seed

    def evaluate(self, params: np.ndarray) -> float:
        """Evaluate fitness of a parameter vector via simulation."""
        from mycelium_fractal_net.bio.extension import BioExtension
        from mycelium_fractal_net.core.diagnose import diagnose
        from mycelium_fractal_net.core.simulate import simulate_history
        from mycelium_fractal_net.types.field import SimulationSpec

        config = params_to_bio_config(params)
        try:
            spec = SimulationSpec(grid_size=self.grid_size, steps=self.steps, seed=self.seed)
            seq = simulate_history(spec)
            bio = BioExtension.from_sequence(seq, config=config).step(n=self.bio_steps)
            diagnosis = diagnose(seq, skip_intervention=True, mode="fast")
            return compute_fitness(bio.report(), diagnosis)
        except Exception:
            return 0.0

    def run(
        self,
        n_generations: int = 20,
        population_size: int | None = None,
        sigma0: float = 0.3,
        verbose: bool = True,
    ) -> BioEvolutionResult:
        """Run CMA-ES optimization over the parameter space."""
        t0 = time.perf_counter()
        n = len(PARAM_NAMES)
        history: list[dict[str, Any]] = []
        best_f, best_p = 0.0, DEFAULT_PARAMS.copy()
        total_evals = 0

        lo, hi = PARAM_BOUNDS[:, 0], PARAM_BOUNDS[:, 1]
        rng_es = np.random.default_rng(self.seed)

        try:
            from cmaes import CMA

            pop = population_size or 4 + int(3 * np.log(n))
            x0 = (DEFAULT_PARAMS - lo) / (hi - lo)
            opt = CMA(
                mean=x0,
                sigma=sigma0,
                bounds=np.tile([0.0, 1.0], (n, 1)),
                seed=self.seed,
                population_size=pop,
            )
            converged = False
            for gen in range(n_generations):
                sols, fits = [], []
                for _ in range(opt.population_size):
                    xn = opt.ask()
                    x = np.clip(xn, 0, 1) * (hi - lo) + lo
                    f = self.evaluate(x)
                    sols.append((xn, -f))
                    fits.append(f)
                    total_evals += 1
                    if f > best_f:
                        best_f, best_p = f, x.copy()
                opt.tell(sols)
                history.append(
                    {
                        "gen": gen,
                        "best": best_f,
                        "mean": float(np.mean(fits)),
                        "sigma": float(opt._sigma),
                    }
                )
                if verbose:
                    pass
                if opt.should_stop():
                    converged = True
                    break
        except ImportError:
            converged = False
            x = (DEFAULT_PARAMS - lo) / (hi - lo)
            sigma = sigma0
            fc = self.evaluate(DEFAULT_PARAMS)
            best_f, best_p = fc, DEFAULT_PARAMS.copy()
            total_evals = 1
            ns = 0
            for gen in range(n_generations):
                xn = np.clip(x + sigma * rng_es.standard_normal(n), 0, 1)
                xr = xn * (hi - lo) + lo
                fn = self.evaluate(xr)
                total_evals += 1
                if fn > fc:
                    x, fc = xn, fn
                    ns += 1
                    if fn > best_f:
                        best_f, best_p = fn, xr.copy()
                if (gen + 1) % 5 == 0:
                    sigma *= 1.22 if ns / 5 > 0.2 else 0.82
                    ns = 0
                history.append({"gen": gen, "best": best_f, "sigma": sigma})

        return BioEvolutionResult(
            best_params=best_p,
            best_fitness=best_f,
            best_config=params_to_bio_config(best_p),
            generation_history=history,
            total_evaluations=total_evals,
            converged=converged,
            elapsed_seconds=time.perf_counter() - t0,
        )
