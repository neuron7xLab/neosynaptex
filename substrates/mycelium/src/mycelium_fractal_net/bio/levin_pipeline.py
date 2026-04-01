"""LevinPipeline — unified entry point for all three Levin modules.

Orchestrates: Morphospace → Memory Anonymization → Persuasion
in one call, returns LevinReport with summary() method.

Usage:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio.levin_pipeline import LevinPipeline

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
    pipeline = LevinPipeline.from_sequence(seq)
    report = pipeline.run()
    print(report.summary())

Integrates with DiagnosisReport via report.to_dict() → metadata field.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["LevinPipeline", "LevinPipelineConfig", "LevinReport"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LevinPipelineConfig:
    """Configuration for the unified Levin pipeline."""

    # Morphospace
    n_pca_components: int = 5
    n_basin_samples: int = 500
    perturbation_scale: float = 0.3
    # Memory anonymization
    D_hdv: int = 500
    alpha_diffusion: float = 3.0
    n_anon_steps: int = 10
    # Persuasion
    n_gramian_modes: int = 10
    # General
    seed: int = 42


@dataclass
class LevinReport:
    """Unified report from all three Levin modules."""

    # Morphospace
    morphospace_pc1_variance: float
    basin_stability: float
    basin_error: float
    trajectory_length: float

    # Memory Anonymization
    anonymity_score: float
    cosine_anonymity: float
    fiedler_value: float

    # Persuasion
    persuadability_score: float
    log_det_gramian: float
    n_controllable_modes: int
    free_energy_final: float
    intervention_level: str

    # Basin CI
    basin_ci_low: float = 0.0
    basin_ci_high: float = 1.0

    # Meta
    compute_time_ms: float = 0.0
    grid_size: int = 0
    n_frames: int = 0

    @property
    def min_control_energy(self) -> float:
        """Minimum control energy (proxy via free energy)."""
        return self.free_energy_final

    @property
    def spectral_gap(self) -> float:
        """Alias for fiedler_value."""
        return self.fiedler_value

    @property
    def gramian_log_det(self) -> float:
        """Alias for log_det_gramian."""
        return self.log_det_gramian

    @property
    def free_energy(self) -> float:
        """Alias for free_energy_final."""
        return self.free_energy_final

    def summary(self) -> str:
        """Single-line summary of all Levin metrics."""
        return (
            f"[LEVIN] "
            f"pc1={self.morphospace_pc1_variance:.3f} "
            f"S_B={self.basin_stability:.3f} [{self.basin_ci_low:.3f},{self.basin_ci_high:.3f}] "
            f"traj={self.trajectory_length:.1f} | "
            f"anon={self.cosine_anonymity:.3f} "
            f"fiedler={self.fiedler_value:.4f} | "
            f"persuade={self.persuadability_score:.3f} "
            f"modes={self.n_controllable_modes} "
            f"F={self.free_energy_final:.4f} "
            f"({self.compute_time_ms:.0f}ms)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "morphospace": {
                "pc1_variance": round(self.morphospace_pc1_variance, 4),
                "basin_stability": round(self.basin_stability, 4),
                "basin_error": round(self.basin_error, 4),
                "basin_ci_low": round(self.basin_ci_low, 4),
                "basin_ci_high": round(self.basin_ci_high, 4),
                "trajectory_length": round(self.trajectory_length, 2),
            },
            "memory_anonymization": {
                "anonymity_score": round(self.anonymity_score, 4),
                "cosine_anonymity": round(self.cosine_anonymity, 4),
                "fiedler_value": round(self.fiedler_value, 6),
            },
            "persuasion": {
                "persuadability_score": round(self.persuadability_score, 4),
                "log_det_gramian": round(self.log_det_gramian, 4),
                "n_controllable_modes": self.n_controllable_modes,
                "free_energy_final": round(self.free_energy_final, 6),
                "intervention_level": self.intervention_level,
            },
            "meta": {
                "compute_time_ms": round(self.compute_time_ms, 1),
                "grid_size": self.grid_size,
                "n_frames": self.n_frames,
            },
        }

    def interpretation(self) -> str:
        """Human-readable interpretation of key metrics."""
        lines: list[str] = []
        if self.basin_stability > 0.7:
            lines.append(
                f"System is robust — S_B={self.basin_stability:.2f} means "
                f"{self.basin_stability * 100:.0f}% of perturbations return to attractor"
            )
        elif self.basin_stability > 0.4:
            lines.append(
                f"System is moderately stable — S_B={self.basin_stability:.2f}, "
                f"approaching transition possible"
            )
        else:
            lines.append(f"System near critical transition — S_B={self.basin_stability:.2f} is low")
        if self.cosine_anonymity > 0.5:
            lines.append(
                f"Memory is largely collective (anonymity={self.cosine_anonymity:.2f}) "
                f"— strong gap junction coupling"
            )
        else:
            lines.append(
                f"Memory is still individual (anonymity={self.cosine_anonymity:.2f}) "
                f"— weak coupling or early stage"
            )
        if self.n_controllable_modes > 5:
            lines.append(
                f"Persuadable system ({self.n_controllable_modes} controllable modes) "
                f"— SIGNAL interventions effective"
            )
        else:
            lines.append(
                f"Requires stronger intervention — only "
                f"{self.n_controllable_modes} controllable modes"
            )
        return " | ".join(lines)


class LevinPipeline:
    """Unified pipeline: FieldSequence → LevinReport in one call.

    Runs all three Levin modules in dependency order:
    1. Morphospace (PCA + basin stability)
    2. Memory Anonymization (HDV diffusion via Physarum conductances)
    3. Persuasion (active inference + controllability Gramian)
    """

    def __init__(
        self,
        history: np.ndarray,
        field: np.ndarray,
        config: LevinPipelineConfig | None = None,
    ) -> None:
        self.history = history
        self.field = field
        self.N = field.shape[0]
        self.config = config or LevinPipelineConfig()

    @classmethod
    def from_sequence(
        cls,
        seq: Any,
        config: LevinPipelineConfig | None = None,
    ) -> LevinPipeline:
        """Construct from FieldSequence."""
        return cls(
            history=seq.history,
            field=seq.field,
            config=config,
        )

    def run(
        self,
        target_field: np.ndarray | None = None,
        verbose: bool = False,
        physarum_state: Any = None,
    ) -> LevinReport:
        """Run full Levin pipeline and return unified report."""
        cfg = self.config
        t_start = time.perf_counter()

        # ── 1. Morphospace ─────────────────────────────────────────
        from .morphospace import (
            BasinStabilityAnalyzer,
            MorphospaceBuilder,
            MorphospaceConfig,
        )

        if verbose:
            logger.info("[1/3] Morphospace...")

        morph_cfg = MorphospaceConfig(
            n_components=cfg.n_pca_components,
            n_basin_samples=cfg.n_basin_samples,
            perturbation_scale=cfg.perturbation_scale,
            random_seed=cfg.seed,
        )
        builder = MorphospaceBuilder(morph_cfg)
        coords = builder.fit(self.history)

        terminal_field = self.field

        def fast_sim(perturbed: np.ndarray) -> np.ndarray:
            """RD relaxation: diffusion + attractor pull.

            Hybrid approach: 5 explicit Euler diffusion steps for local
            smoothing, then gentle attractor pull (20% blend toward
            terminal field). This gives physically motivated relaxation
            while ensuring basin stability is measurable.
            """
            f = perturbed.copy().astype(np.float64)
            alpha_d = 0.18
            for _ in range(5):
                lap = (
                    np.roll(f, 1, 0)
                    + np.roll(f, -1, 0)
                    + np.roll(f, 1, 1)
                    + np.roll(f, -1, 1)
                    - 4.0 * f
                )
                f = f + alpha_d * lap
            # Attractor pull: perturbed state relaxes toward terminal
            f = f * 0.8 + terminal_field * 0.2
            return f

        basin_analyzer = BasinStabilityAnalyzer(simulator_fn=fast_sim, config=morph_cfg)
        basin_result = basin_analyzer.compute(coords)

        # ── 2. Memory Anonymization ────────────────────────────────
        from .memory_anonymization import (
            AnonymizationConfig,
            GapJunctionDiffuser,
            HDVFieldEncoder,
        )
        from .physarum import PhysarumEngine

        if verbose:
            logger.info("[2/3] Memory Anonymization...")

        N = self.N
        enc = HDVFieldEncoder(D=cfg.D_hdv, neighborhood=1, seed=cfg.seed)
        memory_original = enc.encode(self.field)

        # Physarum state: reuse if provided, otherwise compute
        if physarum_state is not None:
            phys = physarum_state
        else:
            eng = PhysarumEngine(N)
            src = self.field > 0
            snk = self.field < -0.05
            phys = eng.initialize(src, snk)
            for _ in range(3):
                phys = eng.step(phys, src, snk)

        anon_cfg = AnonymizationConfig(
            alpha=cfg.alpha_diffusion,
            dt=0.1,
            n_diffusion_steps=cfg.n_anon_steps,
        )
        diffuser = GapJunctionDiffuser(anon_cfg)
        _diffused, anon_metrics = diffuser.diffuse(memory_original, phys.D_h, phys.D_v)

        # ── 3. Persuasion ─────────────────────────────────────────
        from .persuasion import FieldActiveInference, PersuadabilityAnalyzer

        if verbose:
            logger.info("[3/3] Persuasion...")

        persuad_analyzer = PersuadabilityAnalyzer(
            n_integration_steps=20,  # 20 vs 50: 2.5× faster, sufficient precision
        )
        persuad_result = persuad_analyzer.from_field_history(
            self.history, n_modes=min(cfg.n_gramian_modes, 5)
        )

        # Active inference: free energy relative to target
        target = target_field if target_field is not None else self.field
        afi = FieldActiveInference(target)
        fe_result = afi.compute_free_energy(self.field)

        # ── Report ─────────────────────────────────────────────────
        elapsed = (time.perf_counter() - t_start) * 1000

        return LevinReport(
            morphospace_pc1_variance=float(coords.explained_variance[0]),
            basin_stability=basin_result.basin_stability,
            basin_error=basin_result.error_bound,
            basin_ci_low=basin_result.ci_low,
            basin_ci_high=basin_result.ci_high,
            trajectory_length=coords.trajectory_length(),
            anonymity_score=anon_metrics.anonymization_score,
            cosine_anonymity=anon_metrics.cosine_anonymity,
            fiedler_value=anon_metrics.spectral_gap,
            persuadability_score=persuad_result.persuadability_score,
            log_det_gramian=persuad_result.gramian_det_log,
            n_controllable_modes=persuad_result.n_controllable_modes,
            free_energy_final=fe_result.free_energy,
            intervention_level=persuad_result.intervention_level.name,
            compute_time_ms=elapsed,
            grid_size=N,
            n_frames=self.history.shape[0],
        )
