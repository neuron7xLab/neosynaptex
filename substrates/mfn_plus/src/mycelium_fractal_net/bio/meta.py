"""MetaOptimizer: Memory-Augmented CMA-ES (MA-CMA-ES).

Combines HDV episodic memory with CMA-ES. The memory allows:
- O(D) fitness prediction for similar-to-seen parameter vectors
- Warm-start across optimization runs
- Cognitive map of the parameter-behavior space

This combination for reaction-diffusion + bio systems is novel.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from .evolution import (
    DEFAULT_PARAMS,
    PARAM_BOUNDS,
    PARAM_NAMES,
    BioEvolutionOptimizer,
    BioEvolutionResult,
    params_to_bio_config,
)
from .memory import BioMemory, HDVEncoder

__all__ = ["MetaOptimizer", "MetaOptimizerResult"]

META_D = 10_000
CACHE_THRESHOLD = 0.75


@dataclass
class MetaOptimizerResult:
    """Meta optimizer result."""

    evolution_result: BioEvolutionResult
    cache_hits: int
    total_queries: int
    memory_size: int
    fitness_landscape: dict[str, float]
    speedup_ratio: float

    def summary(self) -> str:
        """Summary."""
        er = self.evolution_result
        return (
            f"[META-OPT] best={er.best_fitness:.4f} evals={er.total_evaluations} "
            f"cache={self.cache_hits}/{self.total_queries} ({self.speedup_ratio:.0%}) "
            f"mem={self.memory_size} ({er.elapsed_seconds:.1f}s)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        d = self.evolution_result.to_dict()
        d.update(
            {
                "cache_hits": self.cache_hits,
                "total_queries": self.total_queries,
                "memory_size": self.memory_size,
                "speedup_ratio": self.speedup_ratio,
                "fitness_landscape": self.fitness_landscape,
            }
        )
        return d


class MetaOptimizer:
    """Memory-Augmented CMA-ES for BioConfig optimization.

    Usage::

        meta = MetaOptimizer(grid_size=16, steps=20, bio_steps=5)
        result = meta.run(n_generations=10)
        print(result.summary())
        # Transfer memory: meta2.memory = meta.memory
    """

    def __init__(
        self,
        grid_size: int = 16,
        steps: int = 20,
        bio_steps: int = 5,
        memory_capacity: int = 500,
        cache_threshold: float = CACHE_THRESHOLD,
        D: int = META_D,
        seed: int = 42,
    ) -> None:
        self.encoder = HDVEncoder(n_features=len(PARAM_NAMES), D=D, sigma=0.5, seed=seed)
        self.memory = BioMemory(self.encoder, capacity=memory_capacity)
        self._base = BioEvolutionOptimizer(
            grid_size=grid_size, steps=steps, bio_steps=bio_steps, seed=seed
        )
        self._cache_threshold = cache_threshold
        self._cache_hits = 0
        self._total_queries = 0
        self.seed = seed

    def _norm(self, p: np.ndarray) -> np.ndarray:
        return (p - PARAM_BOUNDS[:, 0]) / (PARAM_BOUNDS[:, 1] - PARAM_BOUNDS[:, 0])

    def _denorm(self, pn: np.ndarray) -> np.ndarray:
        result: np.ndarray = (
            np.clip(pn, 0, 1) * (PARAM_BOUNDS[:, 1] - PARAM_BOUNDS[:, 0]) + PARAM_BOUNDS[:, 0]
        )
        return result

    def memory_aware_evaluate(self, params: np.ndarray) -> tuple[float, bool]:
        """Evaluate with HDV memory cache — returns (fitness, was_cached)."""
        self._total_queries += 1
        hdv = self.encoder.encode(self._norm(params))
        fam = self.memory.superposition_familiarity(hdv)

        if fam > self._cache_threshold and self.memory.size >= 5:
            self._cache_hits += 1
            return self.memory.predict_fitness(hdv, k=min(5, self.memory.size)), True

        true_f = self._base.evaluate(params)
        self.memory.store(
            hdv=hdv,
            fitness=true_f,
            params={PARAM_NAMES[i]: float(params[i]) for i in range(len(params))},
            metadata={"familiarity": fam},
            step=self._total_queries,
        )
        return true_f, False

    def run(
        self,
        n_generations: int = 15,
        population_size: int | None = None,
        sigma0: float = 0.3,
        verbose: bool = True,
    ) -> MetaOptimizerResult:
        """Run memory-augmented CMA-ES optimization."""
        t0 = time.perf_counter()
        n = len(PARAM_NAMES)
        _lo, _hi = PARAM_BOUNDS[:, 0], PARAM_BOUNDS[:, 1]
        history: list[dict[str, Any]] = []
        best_f, best_p = 0.0, DEFAULT_PARAMS.copy()
        total_evals = 0

        try:
            from cmaes import CMA

            pop = population_size or 4 + int(3 * np.log(n))
            x0 = self._norm(DEFAULT_PARAMS)
            opt = CMA(
                mean=x0,
                sigma=sigma0,
                bounds=np.tile([0.0, 1.0], (n, 1)),
                seed=self.seed,
                population_size=pop,
            )
            converged = False

            for gen in range(n_generations):
                sols, fits, ch = [], [], 0
                for _ in range(opt.population_size):
                    xn = opt.ask()
                    x = self._denorm(xn)
                    f, cached = self.memory_aware_evaluate(x)
                    sols.append((xn, -f))
                    fits.append(f)
                    total_evals += 1
                    if cached:
                        ch += 1
                    if f > best_f:
                        best_f, best_p = f, x.copy()
                opt.tell(sols)
                history.append(
                    {
                        "gen": gen,
                        "best": best_f,
                        "mean": float(np.mean(fits)),
                        "sigma": float(opt._sigma),
                        "cache_hits": ch,
                        "mem": self.memory.size,
                    }
                )
                if verbose:
                    pass
                if opt.should_stop():
                    converged = True
                    break

        except ImportError:
            converged = False
            rng = np.random.default_rng(self.seed)
            x = self._norm(DEFAULT_PARAMS)
            sigma = sigma0
            fc, _ = self.memory_aware_evaluate(DEFAULT_PARAMS)
            best_f, best_p = fc, DEFAULT_PARAMS.copy()
            total_evals = 1
            ns = 0
            for gen in range(n_generations):
                xn = np.clip(x + sigma * rng.standard_normal(n), 0, 1)
                fn, cached = self.memory_aware_evaluate(self._denorm(xn))
                total_evals += 1
                if fn > fc:
                    x, fc = xn, fn
                    ns += 1
                    if fn > best_f:
                        best_f, best_p = fn, self._denorm(xn).copy()
                if (gen + 1) % 5 == 0:
                    sigma *= 1.22 if ns / 5 > 0.2 else 0.82
                    ns = 0
                history.append(
                    {"gen": gen, "best": best_f, "sigma": sigma, "mem": self.memory.size}
                )

        elapsed = time.perf_counter() - t0

        return MetaOptimizerResult(
            evolution_result=BioEvolutionResult(
                best_params=best_p,
                best_fitness=best_f,
                best_config=params_to_bio_config(best_p),
                generation_history=history,
                total_evaluations=total_evals,
                converged=converged,
                elapsed_seconds=elapsed,
            ),
            cache_hits=self._cache_hits,
            total_queries=self._total_queries,
            memory_size=self.memory.size,
            fitness_landscape=self.memory.fitness_landscape(),
            speedup_ratio=self._cache_hits / max(self._total_queries, 1),
        )
