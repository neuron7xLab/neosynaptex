"""Experiment runner — runs scenarios on real MFN simulator.

# EVIDENCE TYPE: real_simulation
All snapshots from actual MFN R-D simulation, not synthetic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.core.thermodynamic_kernel import FreeEnergyTracker
from mycelium_fractal_net.interpretability import (
    GammaDiagnostics,
    MFNFeatureExtractor,
)
from mycelium_fractal_net.tau_control import IdentityEngine

from .scenarios import (
    ABLATION_CONFIGS,
    SCENARIO_HEALTHY,
    SCENARIO_PATHOLOGICAL,
    ScenarioConfig,
)

__all__ = [
    "AblationResult",
    "ExperimentRunner",
    "RunResult",
    "ScenarioResult",
]


@dataclass
class RunResult:
    """Result from one simulation run."""

    gamma: float
    gamma_r2: float
    features: list[dict[str, float]]
    free_energy_trajectory: list[float]
    deviation_origin: str
    v_trajectory: list[float]
    mode_counts: dict[str, int]
    n_transforms: int


@dataclass
class ScenarioResult:
    """Aggregated results from all runs of one scenario."""

    config: ScenarioConfig
    runs: list[RunResult]
    gamma_mean: float = 0.0
    gamma_std: float = 0.0
    elapsed_s: float = 0.0

    def __post_init__(self) -> None:
        gammas = [r.gamma for r in self.runs]
        if gammas:
            self.gamma_mean = float(np.mean(gammas))
            self.gamma_std = float(np.std(gammas))


class ExperimentRunner:
    """Runs real MFN simulations for γ-scaling evidence."""

    def run_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """Run all replicates of one scenario."""
        t0 = time.perf_counter()
        runs: list[RunResult] = []

        for run_idx in range(config.n_runs):
            run = self._single_run(config, run_seed=run_idx * 100 + 42)
            runs.append(run)

        elapsed = time.perf_counter() - t0
        return ScenarioResult(config=config, runs=runs, elapsed_s=elapsed)

    def _single_run(self, config: ScenarioConfig, run_seed: int) -> RunResult:
        """One replicate: generate sequences, compute gamma, extract features."""

        # Generate diverse sequences
        seqs: list[mfn.FieldSequence] = []
        for i in range(config.n_sequences):
            spec = mfn.SimulationSpec(
                steps=config.n_steps_base + i * config.n_steps_increment,
                seed=run_seed + i * 7,
                **config.sim_params,  # type: ignore[arg-type]
            )
            seqs.append(simulate_history(spec))

        # Gamma via morphology descriptors
        gamma_result = _compute_gamma(seqs)
        gamma_val = gamma_result.get("gamma", 0.0)
        gamma_r2 = gamma_result.get("r2", 0.0)

        # Feature extraction on last sequence
        extractor = MFNFeatureExtractor()
        features = []
        for seq in seqs[-5:]:
            fv = extractor.extract_all(seq)
            features.append(fv.to_dict())

        # Free energy trajectory
        _gs: int = int(str(config.sim_params.get("grid_size", 32)))
        fet = FreeEnergyTracker(grid_size=_gs)
        free_energies = [fet.total_energy(seq.field) for seq in seqs]

        # Gamma diagnostics
        diag = GammaDiagnostics()
        gamma_values = [gamma_val] * len(seqs)  # constant per run
        report = diag.diagnose(seqs, gamma_values)
        deviation = report.deviation_origin

        # Identity engine
        engine = IdentityEngine(state_dim=7)
        v_trajectory: list[float] = []
        mode_counts: dict[str, int] = {}
        for j, seq in enumerate(seqs):
            fv = extractor.extract_all(seq)
            state_vec = fv.to_array()[:7]  # first 7 features as state
            ir = engine.process(
                state_vector=state_vec,
                free_energy=free_energies[j],
                phase_is_collapsing=False,
                coherence=0.8,
                recovery_succeeded=True,
            )
            v_trajectory.append(ir.lyapunov.v_total)
            m = ir.tau_state.mode
            mode_counts[m] = mode_counts.get(m, 0) + 1

        return RunResult(
            gamma=gamma_val,
            gamma_r2=gamma_r2,
            features=features,
            free_energy_trajectory=free_energies,
            deviation_origin=deviation,
            v_trajectory=v_trajectory,
            mode_counts=mode_counts,
            n_transforms=engine.transform.transform_count,
        )

    def run_all(self) -> dict[str, ScenarioResult]:
        """Run healthy + pathological scenarios."""
        return {
            "healthy": self.run_scenario(SCENARIO_HEALTHY),
            "pathological": self.run_scenario(SCENARIO_PATHOLOGICAL),
        }

    def run_cross_condition_diagnostics(
        self,
        healthy: ScenarioResult,
        pathological: ScenarioResult,
    ) -> str:
        """Run GammaDiagnostics across BOTH conditions so gamma varies.

        # EVIDENCE TYPE: real_simulation, cross-condition attribution
        When gamma varies across sequences, Pearson correlation is meaningful.
        Returns deviation_origin from the combined analysis.
        """
        # Regenerate sequences from both conditions
        combined_seqs: list[mfn.FieldSequence] = []
        combined_gammas: list[float] = []

        for result in [healthy, pathological]:
            cfg = result.config
            for i in range(min(cfg.n_sequences, 5)):
                spec = mfn.SimulationSpec(
                    steps=cfg.n_steps_base + i * cfg.n_steps_increment,
                    seed=42 + i * 7,
                    **cfg.sim_params,  # type: ignore[arg-type]
                )
                combined_seqs.append(simulate_history(spec))
                combined_gammas.append(result.gamma_mean)

        diag = GammaDiagnostics()
        report = diag.diagnose(combined_seqs, combined_gammas)
        return report.deviation_origin

    def run_ablation_experiment(
        self,
        n_sequences: int = 10,
        n_steps_base: int = 30,
        n_steps_increment: int = 3,
        seed: int = 42,
    ) -> AblationResult:
        """Parameter-level ablation: modify one mechanism, measure Δγ.

        # EVIDENCE TYPE: interventional (parameter ablation), not correlational
        # APPROXIMATION: parameter ablation ≠ perfect do-calculus intervention
        """
        gammas: dict[str, float] = {}

        for name, params in ABLATION_CONFIGS.items():
            seqs: list[mfn.FieldSequence] = []
            for i in range(n_sequences):
                spec = mfn.SimulationSpec(
                    steps=n_steps_base + i * n_steps_increment,
                    seed=seed + i * 7,
                    **params,  # type: ignore[arg-type]
                )
                seqs.append(simulate_history(spec))
            result = _compute_gamma(seqs)
            gammas[name] = result.get("gamma", 0.0)

        baseline_gamma = gammas.get("baseline", 0.0)
        attributions: dict[str, float] = {}
        for name, gamma in gammas.items():
            if name == "baseline":
                continue
            group = name.replace("ablate_", "")
            attributions[group] = abs(baseline_gamma - gamma)

        total = sum(attributions.values()) + 1e-12
        normalized = {k: v / total for k, v in attributions.items()}

        return AblationResult(
            gammas=gammas,
            attributions=normalized,
            baseline_gamma=baseline_gamma,
        )


@dataclass
class AblationResult:
    """Result from parameter-level ablation experiment.

    # EVIDENCE TYPE: interventional (parameter ablation)
    # APPROXIMATION: parameter ablation ≠ perfect do-calculus intervention
    """

    gammas: dict[str, float]
    attributions: dict[str, float]  # normalized, sums to 1.0
    baseline_gamma: float = 0.0

    @property
    def top_causal_group(self) -> str:
        if not self.attributions:
            return "unknown"
        return max(self.attributions, key=self.attributions.get)  # type: ignore[arg-type]

    @property
    def top_weight(self) -> float:
        if not self.attributions:
            return 0.0
        return max(self.attributions.values())


def _compute_gamma_robust(
    x: np.ndarray,
    y: np.ndarray,
    n_bootstrap: int = 1000,
    rng_seed: int = 42,
) -> dict[str, Any]:
    """Gamma-scaling with Theil-Sen + bootstrap CI95 + permutation p-value.

    # EVIDENCE TYPE: real_simulation
    Ref: Theil (1950), Sen (1968), Efron & Tibshirani (1994)
    """
    n = len(x)
    if n < 3:
        return {"gamma": 0.0, "r2": 0.0, "ci95_lo": 0.0, "ci95_hi": 0.0,
                "p_value": 1.0, "se": 0.0, "n_points": n,
                "valid": False, "method": "insufficient_data"}

    # OLS
    coeffs_ols = np.polyfit(x, y, 1)
    gamma_ols = float(coeffs_ols[0])
    y_pred = np.polyval(coeffs_ols, x)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2_ols = 1.0 - ss_res / (ss_tot + 1e-12)

    # Theil-Sen: median of all pairwise slopes
    slopes = []
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
    rng = np.random.default_rng(rng_seed)
    boot_gammas = []
    for _ in range(n_bootstrap):
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
    null = [float(np.polyfit(x, rng.permutation(y), 1)[0])
            for _ in range(n_bootstrap)]
    p_value = max(float(np.mean(np.abs(null) >= abs(gamma_ts))),
                  1.0 / n_bootstrap)

    ci_excludes_zero = not (ci_lo <= 0.0 <= ci_hi)
    gate_pass = (ci_excludes_zero and p_value < 0.05
                 and abs(gamma_ts) > 0.3 and r2_ts > 0.3)

    return {
        "gamma": round(gamma_ts, 4),
        "gamma_ols": round(gamma_ols, 4),
        "r2": round(r2_ts, 6),
        "r2_ols": round(r2_ols, 6),
        "ci95_lo": round(ci_lo, 4),
        "ci95_hi": round(ci_hi, 4),
        "p_value": round(p_value, 6),
        "se": round(se, 4),
        "n_points": n,
        "valid": gate_pass,
        "method": "theil_sen_bootstrap",
    }


def _compute_gamma(seqs: list[mfn.FieldSequence]) -> dict[str, Any]:
    """Compute gamma-scaling across a sequence of FieldSequences.

    # EVIDENCE TYPE: real_simulation
    Uses morphology descriptors from real MFN simulation data.
    """
    if len(seqs) < 5:
        return {"gamma": 0.0, "r2": 0.0, "n_points": 0, "valid": False,
                "ci95_lo": 0.0, "ci95_hi": 0.0, "p_value": 1.0}

    from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor

    descriptors = [compute_morphology_descriptor(seq) for seq in seqs]

    entropies = [d.complexity.get("temporal_lzc", 0.0) for d in descriptors]
    bettis = [d.stability.get("instability_index", 0.0) for d in descriptors]

    log_dH: list[float] = []
    log_beta: list[float] = []
    for i in range(len(entropies)):
        for j in range(i + 2, min(i + 6, len(entropies))):
            dH = abs(entropies[j] - entropies[i])
            b_sum = abs(bettis[j]) + abs(bettis[i]) + 1e-12
            if dH > 1e-6:
                log_dH.append(np.log(dH))
                log_beta.append(np.log(b_sum))

    if len(log_dH) < 3:
        return {"gamma": 0.0, "r2": 0.0, "n_points": len(log_dH), "valid": False,
                "ci95_lo": 0.0, "ci95_hi": 0.0, "p_value": 1.0}

    return _compute_gamma_robust(np.array(log_beta), np.array(log_dH))
