"""Unified Diagnostic Engine — one call, one system, one truth.

Integrates all MFN subsystems into a single cognitive pipeline:
  Core:     diagnose() → anomaly + EWS + causal gate
  Bio:      BioExtension → 5 mechanisms + LevinPipeline → 3 Levin modules
  Fractal:  arsenal (f(α), Λ(r), S_bb) + dynamics (Δα(t), DFA H, χ invariant)
  Compute:  ComputeBudget → adaptive resource allocation

One call: engine.analyze(seq) → SystemReport with .summary() and .interpretation()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np

    from mycelium_fractal_net.types.field import FieldSequence

__all__ = ["SystemReport", "UnifiedEngine"]

logger = logging.getLogger(__name__)


@dataclass
class SystemReport:
    """Unified report from all MFN subsystems."""

    # Core diagnosis
    severity: str
    anomaly_label: str
    anomaly_score: float
    ews_score: float
    ews_transition: str
    causal_decision: str

    # Bio layer
    bio_conductivity_max: float
    bio_spiking_fraction: float
    bio_step_count: int

    # Levin cognitive
    basin_stability: float
    basin_error: float
    cosine_anonymity: float
    persuadability_score: float
    intervention_level: str
    free_energy: float

    # Fractal arsenal
    delta_alpha: float
    is_genuine_multifractal: bool
    lacunarity_4: float
    lacunarity_decay: float
    basin_entropy: float

    # Fractal dynamics
    hurst_exponent: float
    is_critical_slowing: bool
    spectral_expanding: bool
    chi_invariant: float
    chi_interpretation: str

    # JKO/HWI unified score
    M_base: float = 0.0
    M_full: float = 0.0
    hwi_holds: bool = True
    M_interpretation: str = "unknown"

    # Meta
    compute_time_ms: float = 0.0
    compute_mode: str = "normal"
    grid_size: int = 0
    n_frames: int = 0

    def summary(self) -> str:
        """Single-line system summary."""
        genuine = "GENUINE" if self.is_genuine_multifractal else "mono"
        critical = "CRITICAL" if self.is_critical_slowing else "stable"
        expanding = "expanding" if self.spectral_expanding else "collapsing"
        hwi = "+" if self.hwi_holds else "!"
        return (
            f"[MFN] {self.severity} | "
            f"M={self.M_full:.3f} HWI={hwi} | "
            f"anomaly={self.anomaly_label}({self.anomaly_score:.2f}) "
            f"ews={self.ews_score:.2f} causal={self.causal_decision} | "
            f"S_B={self.basin_stability:.2f} "
            f"persuade={self.intervention_level} | "
            f"da={self.delta_alpha:.2f}({genuine}) H={self.hurst_exponent:.2f}({critical}) "
            f"chi={self.chi_invariant:.3f}({expanding}) "
            f"({self.compute_time_ms:.0f}ms)"
        )

    def interpretation(self) -> str:
        """Human-readable multi-line interpretation."""
        lines: list[str] = []

        # Unified score M — the thermodynamic spine
        lines.append(
            f"Thermodynamic state: M={self.M_full:.3f} ({self.M_interpretation}). "
            f"HWI {'satisfied' if self.hwi_holds else 'VIOLATED'}."
        )

        # Core health
        if self.severity == "stable":
            lines.append("System is healthy — nominal operation, no intervention needed.")
        elif self.severity == "info":
            lines.append(
                f"System is functional but approaching transition (EWS={self.ews_score:.2f})."
            )
        elif self.severity == "warning":
            lines.append(
                f"WARNING: system under stress — "
                f"anomaly={self.anomaly_label}, EWS={self.ews_score:.2f}."
            )
        else:
            lines.append(
                f"CRITICAL: system in danger — "
                f"anomaly={self.anomaly_label}, causal={self.causal_decision}."
            )

        # Basin stability + entropy invariant
        if self.basin_stability > 0.7 and self.basin_entropy < 0.5:
            lines.append(
                f"Topology robust: S_B={self.basin_stability:.2f}, smooth basin boundaries."
            )
        elif self.basin_stability < 0.4:
            lines.append(
                f"Basin destabilized: S_B={self.basin_stability:.2f} — "
                f"perturbations may not return to attractor."
            )

        # Fractal complexity
        if self.is_genuine_multifractal:
            if self.spectral_expanding:
                lines.append(
                    f"Complexity expanding (da={self.delta_alpha:.2f}, genuine) — "
                    f"system building multi-scale structure."
                )
            else:
                lines.append(
                    f"Complexity collapsing (da={self.delta_alpha:.2f}) — "
                    f"monofractalization approaching, possible phase transition."
                )

        # Critical slowing + persuadability
        if self.is_critical_slowing:
            lines.append(
                f"Critical slowing detected (H={self.hurst_exponent:.2f}) — "
                f"maximum persuadability window. "
                f"Recommended: {self.intervention_level} intervention."
            )

        # Chi diagnostic
        lines.append(f"Invariant chi={self.chi_invariant:.3f}: {self.chi_interpretation}.")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "core": {
                "severity": self.severity,
                "anomaly_label": self.anomaly_label,
                "anomaly_score": round(self.anomaly_score, 4),
                "ews_score": round(self.ews_score, 4),
                "ews_transition": self.ews_transition,
                "causal_decision": self.causal_decision,
            },
            "bio": {
                "conductivity_max": round(self.bio_conductivity_max, 4),
                "spiking_fraction": round(self.bio_spiking_fraction, 4),
                "step_count": self.bio_step_count,
            },
            "levin": {
                "basin_stability": round(self.basin_stability, 4),
                "basin_error": round(self.basin_error, 4),
                "cosine_anonymity": round(self.cosine_anonymity, 4),
                "persuadability_score": round(self.persuadability_score, 4),
                "intervention_level": self.intervention_level,
                "free_energy": round(self.free_energy, 6),
            },
            "fractal": {
                "delta_alpha": round(self.delta_alpha, 4),
                "is_genuine": self.is_genuine_multifractal,
                "lacunarity_4": round(self.lacunarity_4, 4),
                "lacunarity_decay": round(self.lacunarity_decay, 4),
                "basin_entropy": round(self.basin_entropy, 4),
            },
            "dynamics": {
                "hurst_exponent": round(self.hurst_exponent, 4),
                "is_critical": self.is_critical_slowing,
                "spectral_expanding": self.spectral_expanding,
                "chi_invariant": round(self.chi_invariant, 4),
                "chi_interpretation": self.chi_interpretation,
            },
            "unified": {
                "M_base": round(self.M_base, 6),
                "M_full": round(self.M_full, 6),
                "hwi_holds": self.hwi_holds,
                "interpretation": self.M_interpretation,
            },
            "meta": {
                "compute_time_ms": round(self.compute_time_ms, 1),
                "compute_mode": self.compute_mode,
                "grid_size": self.grid_size,
                "n_frames": self.n_frames,
            },
        }


class UnifiedEngine:
    """One call, one system, one truth.

    Usage::

        import mycelium_fractal_net as mfn
        from mycelium_fractal_net.core.unified_engine import UnifiedEngine

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
        engine = UnifiedEngine()
        report = engine.analyze(seq)
        print(report.summary())
        print(report.interpretation())
    """

    def __init__(self, bio_steps: int = 3, verbose: bool = False) -> None:
        self.bio_steps = bio_steps
        self.verbose = verbose
        self._memory: Any = None
        self._metacognition: Any = None

    @property
    def metacognition(self) -> Any:
        """Metacognitive layer — self-awareness of epistemic state."""
        if self._metacognition is None:
            from .metacognition import MetaCognitiveLayer

            self._metacognition = MetaCognitiveLayer()
        return self._metacognition

    @property
    def memory(self) -> Any:
        """Diagnostic memory — accumulates intelligence across runs."""
        if self._memory is None:
            from .diagnostic_memory import DiagnosticMemory

            self._memory = DiagnosticMemory()
        return self._memory

    def analyze(
        self,
        seq: FieldSequence,
        target_field: np.ndarray | None = None,
    ) -> SystemReport:
        """Run all subsystems and return unified report."""
        from .input_guards import validate_field_sequence

        validate_field_sequence(seq, "UnifiedEngine.analyze(seq)")
        t_start = time.perf_counter()

        # ── 1. Core diagnosis ──────────────────────────────────────
        if self.verbose:
            logger.info("[1/4] Core diagnosis...")
        from mycelium_fractal_net.core.diagnose import diagnose

        core = diagnose(seq, mode="fast", skip_intervention=True)

        # ── 2. Bio (creates Physarum state we'll reuse) ───────────
        if self.verbose:
            logger.info("[2/5] Bio extension...")
        from mycelium_fractal_net.bio import BioExtension

        bio = BioExtension.from_sequence(seq).step(n=self.bio_steps)
        bio_report = bio.report()

        # ── 3. Levin (reuse Physarum from bio — avoids double init) ─
        if self.verbose:
            logger.info("[3/5] Levin pipeline...")
        from mycelium_fractal_net.bio.levin_pipeline import (
            LevinPipeline,
            LevinPipelineConfig,
        )

        # Adaptive params: scale D_hdv and samples with grid size
        N = seq.field.shape[0]
        D_hdv = min(300, max(100, 6000 // N))  # N=16→375, N=32→187, N=64→93
        n_samples = min(30, max(10, 500 // N))  # N=16→31, N=32→15, N=64→7
        levin_cfg = LevinPipelineConfig(n_basin_samples=n_samples, D_hdv=D_hdv, n_anon_steps=3)
        levin = LevinPipeline.from_sequence(seq, config=levin_cfg).run(
            target_field=target_field,
            physarum_state=bio.physarum_state,
        )

        # ── 4. Fractal arsenal ─────────────────────────────────────
        if self.verbose:
            logger.info("[4/5] Fractal arsenal...")
        import numpy as np

        from mycelium_fractal_net.analytics.fractal_features import (
            compute_basin_invariant,
            compute_dfa,
            compute_fractal_arsenal,
            compute_spectral_evolution,
        )

        basin_grid = (seq.field > float(np.mean(seq.field))).astype(int)
        arsenal = compute_fractal_arsenal(seq.field, basin_grid)

        # ── 5. Fractal dynamics ────────────────────────────────────
        if self.verbose:
            logger.info("[5/5] Fractal dynamics...")
        n_frames = seq.history.shape[0]
        optimal_stride = max(1, n_frames // 8)
        se = compute_spectral_evolution(seq.history, stride=optimal_stride)
        ts = seq.history.mean(axis=(1, 2))
        dfa = compute_dfa(ts)

        # Basin invariant: connect S_bb with S_B
        basin_inv = compute_basin_invariant(
            S_bb=arsenal.basin_fractality.S_bb if arsenal.basin_fractality else 0.0,
            S_B=levin.basin_stability,
        )

        # ── 6. JKO/HWI unified score ────────────────────────────────
        from mycelium_fractal_net.analytics.tda_ews import compute_tda
        from mycelium_fractal_net.analytics.unified_score import compute_unified_score

        topo = compute_tda(seq.field, min_persistence_frac=0.005)
        try:
            unified = compute_unified_score(
                field_current=seq.history[0],
                field_reference=seq.field,
                CE=0.0,  # CE computed separately; M_base carries the physics
                beta_0=topo.beta_0,
                beta_1=topo.beta_1,
            )
            M_base = unified.M_base
            M_full = unified.M_full
            hwi_ok = unified.hwi.hwi_holds
            M_interp = unified._interpret()
        except Exception:
            M_base = 0.0
            M_full = 0.0
            hwi_ok = True
            M_interp = "unknown"

        # ── Severity integration: fractal dynamics + M enhance core ──
        severity = core.severity
        if dfa.is_critical and severity == "stable":
            severity = "info"
        if dfa.is_critical and se.is_collapsing and severity == "info":
            severity = "warning"
        if levin.basin_stability < 0.4 and severity in ("stable", "info"):
            severity = "warning"
        # HWI violation is a thermodynamic red flag
        if not hwi_ok and severity in ("stable", "info"):
            severity = "warning"

        # ── Assemble ───────────────────────────────────────────────
        elapsed = (time.perf_counter() - t_start) * 1000

        return SystemReport(
            # Core (with integrated severity)
            severity=severity,
            anomaly_label=core.anomaly.label,
            anomaly_score=float(core.anomaly.score),
            ews_score=core.warning.ews_score,
            ews_transition=core.warning.transition_type,
            causal_decision=core.causal.decision.value,
            # Bio
            bio_conductivity_max=bio_report.physarum.get("conductivity_max", 0.0),
            bio_spiking_fraction=bio_report.fhn.get("spiking_fraction", 0.0),
            bio_step_count=bio_report.step_count,
            # Levin
            basin_stability=levin.basin_stability,
            basin_error=levin.basin_error,
            cosine_anonymity=levin.cosine_anonymity,
            persuadability_score=levin.persuadability_score,
            intervention_level=levin.intervention_level,
            free_energy=levin.free_energy_final,
            # Fractal arsenal
            delta_alpha=arsenal.multifractal.delta_alpha,
            is_genuine_multifractal=arsenal.multifractal.is_genuine,
            lacunarity_4=arsenal.lacunarity.lambda_at_4,
            lacunarity_decay=arsenal.lacunarity.decay_exponent,
            basin_entropy=arsenal.basin_fractality.S_bb if arsenal.basin_fractality else 0.0,
            # Fractal dynamics
            hurst_exponent=dfa.hurst_exponent,
            is_critical_slowing=dfa.is_critical,
            spectral_expanding=not se.is_collapsing,
            chi_invariant=basin_inv.chi,
            chi_interpretation=basin_inv.chi_interpretation,
            # JKO/HWI unified
            M_base=M_base,
            M_full=M_full,
            hwi_holds=hwi_ok,
            M_interpretation=M_interp,
            # Meta
            compute_time_ms=elapsed,
            compute_mode="normal",
            grid_size=seq.field.shape[0],
            n_frames=seq.history.shape[0] if seq.history is not None else 1,
        )

    def learn(self, n_seeds: int = 100, grid_size: int = 32, steps: int = 30) -> dict[str, Any]:
        """Run N simulations, accumulate observations, extract intelligence.

        Returns learned rules, calibrated thresholds, and correlations.
        """
        import mycelium_fractal_net as mfn

        logger.info("Learning from %d simulations (N=%d, T=%d)...", n_seeds, grid_size, steps)
        for seed in range(n_seeds):
            seq = mfn.simulate(mfn.SimulationSpec(grid_size=grid_size, steps=steps, seed=seed))
            report = self.analyze(seq)
            self.memory.observe(report)

        rules = self.memory.extract_rules()
        thresholds = self.memory.calibrate_thresholds()
        correlations = self.memory.correlation_matrix()

        # Find strongest correlations (exclude self-correlation)
        strong: list[tuple[str, str, float]] = []
        for ki, row in correlations.items():
            for kj, r in row.items():
                if ki < kj and abs(r) > 0.5:
                    strong.append((ki, kj, r))
        strong.sort(key=lambda x: -abs(x[2]))

        return {
            "n_observations": self.memory.size,
            "rules": [r.to_dict() for r in rules],
            "thresholds": thresholds.to_dict(),
            "top_correlations": [{"a": a, "b": b, "r": round(r, 3)} for a, b, r in strong[:10]],
        }
