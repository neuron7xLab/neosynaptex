"""Observatory — unified diagnostic view of an R-D system.

One call. Every lens. Every metric. One truth.

    report = mfn.observe(seq)
    print(report)

This is what you show Dario and Elon.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = ["ObservatoryReport", "observe"]


@dataclass
class ObservatoryReport:
    """Complete multi-lens observation of a morphogenetic field."""

    # Identity
    grid_size: int = 0
    n_steps: int = 0
    seed: int | None = None

    # Thermodynamics
    free_energy: float = 0.0
    entropy_production: float = 0.0
    entropy_regime: str = ""
    lyapunov_lambda1: float = 0.0
    thermo_verdict: str = ""

    # Topology
    beta_0: int = 0
    beta_1: int = 0
    pattern_type: str = ""
    topological_entropy: float = 0.0
    complexity_class: str = ""
    genome_fingerprint_norm: float = 0.0

    # Geometry
    fisher_trace: float = 0.0
    fisher_curvature: float = 0.0
    anisotropy: float = 0.0
    coherence: float = 0.0
    defect_count: int = 0
    geodesic_from_initial: float = 0.0

    # Dynamics
    kuramoto_R: float = 0.0
    kuramoto_coherence: str = ""
    criticality_score: float = 0.0
    criticality_verdict: str = ""
    correlation_length: float = 0.0

    # Invariants
    lambda2: float = 0.0
    lambda2_cv: float = 0.0
    lambda5: float = 0.0
    lambda6: float = 0.0

    # Anomaly
    anomaly_label: str = ""
    anomaly_score: float = 0.0
    ews_score: float = 0.0

    # Landscape
    n_attractors: int = 0
    landscape_roughness: float = 0.0

    # Scale
    d_box: float = 0.0

    # Performance
    compute_time_ms: float = 0.0

    # Diagnostics: which lenses failed to compute
    lens_errors: list[str] = field(default_factory=list)

    @property
    def n_lenses_computed(self) -> int:
        return 8 - len(self.lens_errors)

    def __str__(self) -> str:
        w = 60
        lines = [
            "",
            "╔" + "═" * w + "╗",
            "║" + " MFN OBSERVATORY REPORT ".center(w) + "║",
            "╠" + "═" * w + "╣",
            f"║  Grid: {self.grid_size}×{self.grid_size}  Steps: {self.n_steps}  Seed: {self.seed}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            "║" + " THERMODYNAMICS".ljust(w) + "║",
            f"║    Free energy F     = {self.free_energy:.6f}".ljust(w + 1) + "║",
            f"║    Entropy prod σ    = {self.entropy_production:.6f} ({self.entropy_regime})".ljust(w + 1) + "║",
            f"║    Lyapunov λ₁       = {self.lyapunov_lambda1:.6f}".ljust(w + 1) + "║",
            f"║    Verdict           = {self.thermo_verdict}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            "║" + " TOPOLOGY".ljust(w) + "║",
            f"║    β₀={self.beta_0}  β₁={self.beta_1}  pattern={self.pattern_type}".ljust(w + 1) + "║",
            f"║    D_box={self.d_box:.3f}  H_topo={self.topological_entropy:.3f}  class={self.complexity_class}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            "║" + " GEOMETRY".ljust(w) + "║",
            f"║    Fisher Tr(g)={self.fisher_trace:.4f}  R={self.fisher_curvature:.4f}".ljust(w + 1) + "║",
            f"║    Anisotropy={self.anisotropy:.3f}  Coherence={self.coherence:.3f}  Defects={self.defect_count}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            "║" + " DYNAMICS".ljust(w) + "║",
            f"║    Kuramoto R={self.kuramoto_R:.3f} ({self.kuramoto_coherence})".ljust(w + 1) + "║",
            f"║    Criticality={self.criticality_score:.3f} ({self.criticality_verdict})  ξ={self.correlation_length:.1f}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            "║" + " INVARIANTS (Vasylenko 2026)".ljust(w) + "║",
            f"║    Λ₂ = {self.lambda2:.4f}  CV={self.lambda2_cv:.4f}".ljust(w + 1) + "║",
            f"║    Λ₅ = {self.lambda5:.6f}".ljust(w + 1) + "║",
            f"║    Λ₆ = {self.lambda6:.4f}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            "║" + " ANOMALY + LANDSCAPE".ljust(w) + "║",
            f"║    Detection: {self.anomaly_label} (score={self.anomaly_score:.3f})".ljust(w + 1) + "║",
            f"║    EWS: {self.ews_score:.3f}  Attractors: {self.n_attractors}  Roughness: {self.landscape_roughness:.4f}".ljust(w + 1) + "║",
            "╠" + "─" * w + "╣",
            f"║  Lenses: {self.n_lenses_computed}/8 computed in {self.compute_time_ms:.0f}ms".ljust(w + 1) + "║",
        ]
        if self.lens_errors:
            lines.append("╠" + "─" * w + "╣")
            lines.append("║" + " WARNINGS".ljust(w) + "║")
            for err in self.lens_errors:
                lines.append(f"║    {err}".ljust(w + 1) + "║")
        lines += [
            "╚" + "═" * w + "╝",
            "",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


def observe(seq: Any) -> ObservatoryReport:
    """Complete multi-lens observation. One call, every metric.

    >>> report = mfn.observe(seq)
    >>> print(report)
    """
    t0 = time.perf_counter()
    report = ObservatoryReport()

    field = seq.field
    history = seq.history
    report.grid_size = field.shape[0]
    report.n_steps = history.shape[0] if history is not None else 0
    report.seed = seq.spec.seed if seq.spec else None

    # ── Thermodynamics ────────────────────────────────────
    try:
        from mycelium_fractal_net.analytics.entropy_production import compute_entropy_production
        ep = compute_entropy_production(field)
        report.entropy_production = ep.sigma
        report.entropy_regime = ep.regime

        from mycelium_fractal_net.core.thermodynamic_kernel import FreeEnergyTracker
        tracker = FreeEnergyTracker(grid_size=field.shape[0])
        report.free_energy = tracker.total_energy(field)
    except Exception as _e:
        report.lens_errors.append("thermodynamics: " + str(_e)[:60])

    # ── Topology ──────────────────────────────────────────
    try:
        from mycelium_fractal_net.analytics.tda_ews import compute_tda
        tda = compute_tda(field)
        report.beta_0 = tda.beta_0
        report.beta_1 = tda.beta_1
        report.pattern_type = tda.pattern_type

        from mycelium_fractal_net.analytics.pattern_genome import encode_genome
        genome = encode_genome(field)
        report.topological_entropy = genome.topological_entropy
        report.complexity_class = genome.complexity_class
        report.genome_fingerprint_norm = float(np.linalg.norm(genome.fingerprint()))
    except Exception as _e:
        report.lens_errors.append("topology: " + str(_e)[:60])

    # ── Geometry ──────────────────────────────────────────
    try:
        from mycelium_fractal_net.analytics.information_geometry import compute_fisher_rao_metric
        fr = compute_fisher_rao_metric(field)
        report.fisher_trace = fr.metric_trace
        report.fisher_curvature = fr.scalar_curvature

        from mycelium_fractal_net.analytics.morphogenetic_field_tensor import compute_field_tensor
        tensor = compute_field_tensor(field)
        report.anisotropy = tensor.mean_anisotropy
        report.coherence = tensor.coherence
        report.defect_count = tensor.defect_count
    except Exception as _e:
        report.lens_errors.append("geometry: " + str(_e)[:60])

    # ── Dynamics ──────────────────────────────────────────
    try:
        from mycelium_fractal_net.analytics.synchronization import kuramoto_order_parameter
        k = kuramoto_order_parameter(field)
        report.kuramoto_R = k.R
        report.kuramoto_coherence = k.coherence

        from mycelium_fractal_net.analytics.criticality_detector import detect_criticality
        crit = detect_criticality(field, history=history)
        report.criticality_score = crit.criticality_score
        report.criticality_verdict = crit.verdict
        report.correlation_length = crit.correlation_length
    except Exception as _e:
        report.lens_errors.append("dynamics: " + str(_e)[:60])

    # ── Invariants ────────────────────────────────────────
    if history is not None and history.shape[0] >= 5:
        try:
            from mycelium_fractal_net.analytics.invariant_operator import InvariantOperator
            op = InvariantOperator()
            L2 = op.Lambda2(history)
            report.lambda2 = float(np.mean(L2))
            report.lambda2_cv = float(np.std(L2) / (np.mean(L2) + 1e-12))
            report.lambda5 = op.Lambda5(history)
            report.lambda6 = op.Lambda6(history)
        except Exception as _e:
            report.lens_errors.append("invariants: " + str(_e)[:60])

    # ── Anomaly ───────────────────────────────────────────
    try:
        from mycelium_fractal_net.core.detect import detect_anomaly
        det = detect_anomaly(seq)
        report.anomaly_label = det.label
        report.anomaly_score = det.score

        from mycelium_fractal_net.core.early_warning import early_warning
        ews = early_warning(seq)
        report.ews_score = ews.ews_score
    except Exception as _e:
        report.lens_errors.append("anomaly: " + str(_e)[:60])

    # ── Landscape ─────────────────────────────────────────
    if history is not None and history.shape[0] >= 10:
        try:
            from mycelium_fractal_net.analytics.attractor_landscape import reconstruct_landscape
            landscape = reconstruct_landscape(history, n_bins=15)
            report.n_attractors = landscape.n_attractors
            report.landscape_roughness = landscape.landscape_roughness
        except Exception as _e:
            report.lens_errors.append("landscape: " + str(_e)[:60])

    # ── Scale ─────────────────────────────────────────────
    try:
        from mycelium_fractal_net.analytics.fractal_features import compute_box_counting_dimension
        report.d_box = compute_box_counting_dimension(field)
    except Exception as _e:
        report.lens_errors.append("scale: " + str(_e)[:60])

    report.compute_time_ms = (time.perf_counter() - t0) * 1000
    return report
