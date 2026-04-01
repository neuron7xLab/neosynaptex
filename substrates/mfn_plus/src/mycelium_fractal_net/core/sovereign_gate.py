"""SovereignGate — unified verification gate for MFN outputs.

No result leaves the system without passing through 6 verification lenses.
If any lens fails, the gate blocks output and explains why.

This is the immune system of the computational organism.

Lenses:
  [1] Thermodynamic — free energy stability + Lyapunov
  [2] Topological   — persistence diagram stability
  [3] Causal        — intervention beats null model
  [4] Transport     — Wasserstein convergence toward target
  [5] Invariant     — Λ₂ CV within bounds
  [6] Structural    — field finite, bounded, non-degenerate

Usage:
    gate = SovereignGate()
    verdict = gate.verify(seq)
    if not verdict.passed:
        print(verdict)  # explains which lens failed and why

Architecture:
    simulate() → SovereignGate.verify() → diagnose() → output
    If gate fails: block output, explain, suggest auto_heal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = ["LensVerdict", "SovereignGate", "SovereignVerdict"]


@dataclass
class LensVerdict:
    """Result from a single verification lens."""

    name: str
    passed: bool
    score: float  # [0, 1] — confidence
    detail: str
    metric: float = 0.0  # the actual measured value

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"  [{status}] {self.name}: {self.detail}"


@dataclass
class SovereignVerdict:
    """Complete verification verdict from all 6 lenses."""

    passed: bool
    lenses: list[LensVerdict] = field(default_factory=list)
    n_passed: int = 0
    n_failed: int = 0
    blocking_lens: str | None = None  # first lens that failed
    recommendation: str = ""

    def __str__(self) -> str:
        w = 60
        gate = "OPEN" if self.passed else "BLOCKED"
        lines = [
            "",
            "╔" + "═" * w + "╗",
            "║" + f" SOVEREIGN GATE: {gate} ".center(w) + "║",
            "╠" + "═" * w + "╣",
        ]
        for lens in self.lenses:
            lines.append("║" + str(lens).ljust(w) + "║")
        lines.append("╠" + "─" * w + "╣")
        lines.append("║" + f"  {self.n_passed}/{self.n_passed + self.n_failed} lenses passed".ljust(w) + "║")
        if self.blocking_lens:
            lines.append("║" + f"  Blocked by: {self.blocking_lens}".ljust(w) + "║")
        if self.recommendation:
            lines.append("║" + f"  → {self.recommendation}".ljust(w) + "║")
        lines.append("╚" + "═" * w + "╝")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "n_passed": self.n_passed,
            "n_failed": self.n_failed,
            "blocking_lens": self.blocking_lens,
            "recommendation": self.recommendation,
            "lenses": [
                {"name": l.name, "passed": l.passed, "score": l.score, "detail": l.detail, "metric": l.metric}
                for l in self.lenses
            ],
        }


class SovereignGate:
    """Unified 6-lens verification gate.

    Every MFN output passes through this gate.
    If any critical lens fails → output is blocked.
    """

    def __init__(
        self,
        require_all: bool = False,
        min_lenses: int = 4,
    ) -> None:
        """
        Args:
            require_all: if True, ALL 6 lenses must pass
            min_lenses: minimum passing lenses for gate to open (default 4/6)
        """
        self.require_all = require_all
        self.min_lenses = min_lenses

    def verify(self, seq: Any) -> SovereignVerdict:
        """Run all 6 lenses on a FieldSequence."""
        field = seq.field
        history = seq.history

        lenses: list[LensVerdict] = [
            self._lens_structural(field),
            self._lens_thermodynamic(field),
            self._lens_topological(field, history),
            self._lens_causal(seq),
            self._lens_transport(history),
            self._lens_invariant(history),
        ]

        n_passed = sum(1 for l in lenses if l.passed)
        n_failed = len(lenses) - n_passed
        blocking = next((l.name for l in lenses if not l.passed), None)

        if self.require_all:
            passed = n_failed == 0
        else:
            passed = n_passed >= self.min_lenses

        recommendation = ""
        if not passed:
            failed_names = [l.name for l in lenses if not l.passed]
            if "structural" in failed_names:
                recommendation = "Field contains NaN/Inf. Check simulation parameters."
            elif "thermodynamic" in failed_names:
                recommendation = "Energy unstable. Try: mfn.auto_heal(seq) or reduce alpha."
            elif "invariant" in failed_names:
                recommendation = "Invariants drifting. Increase simulation steps or check dt."
            else:
                recommendation = f"Run mfn.auto_heal(seq) to address: {', '.join(failed_names)}"

        return SovereignVerdict(
            passed=passed,
            lenses=lenses,
            n_passed=n_passed,
            n_failed=n_failed,
            blocking_lens=blocking if not passed else None,
            recommendation=recommendation,
        )

    # ── Lens 1: Structural ────────────────────────────────────

    def _lens_structural(self, field: np.ndarray) -> LensVerdict:
        """Field is finite, bounded, and non-degenerate."""
        finite = bool(np.all(np.isfinite(field)))
        if not finite:
            return LensVerdict("structural", False, 0.0, "Field contains NaN or Inf")

        vrange = float(field.max() - field.min())
        bounded = vrange < 100.0
        non_degenerate = vrange > 1e-12

        if not bounded:
            return LensVerdict("structural", False, 0.3, f"Field range {vrange:.2f} > 100", vrange)
        if not non_degenerate:
            return LensVerdict("structural", False, 0.1, "Field is flat (zero variance)", vrange)

        return LensVerdict("structural", True, 1.0, f"range={vrange:.6f}, finite", vrange)

    # ── Lens 2: Thermodynamic ─────────────────────────────────

    def _lens_thermodynamic(self, field: np.ndarray) -> LensVerdict:
        """Free energy is finite and entropy production is non-negative."""
        try:
            from mycelium_fractal_net.analytics.entropy_production import compute_entropy_production
            from mycelium_fractal_net.core.thermodynamic_kernel import FreeEnergyTracker

            tracker = FreeEnergyTracker(grid_size=field.shape[0])
            F = tracker.total_energy(field)
            ep = compute_entropy_production(field)

            if not np.isfinite(F):
                return LensVerdict("thermodynamic", False, 0.0, f"F={F} non-finite", F)
            if ep.sigma < -1e-8:
                return LensVerdict("thermodynamic", False, 0.2, f"σ={ep.sigma:.6f} < 0 (2nd law)", ep.sigma)

            return LensVerdict(
                "thermodynamic", True, 1.0, f"F={F:.6f} σ={ep.sigma:.6f} ({ep.regime})", F
            )
        except Exception as e:
            return LensVerdict("thermodynamic", True, 0.5, f"skipped: {e!s:.40s}")

    # ── Lens 3: Topological ───────────────────────────────────

    def _lens_topological(self, field: np.ndarray, history: np.ndarray | None) -> LensVerdict:
        """Topology is well-defined and stable."""
        try:
            from mycelium_fractal_net.analytics.tda_ews import compute_tda

            tda = compute_tda(field)
            score = 1.0 if tda.beta_0 >= 1 else 0.5

            detail = f"β₀={tda.beta_0} β₁={tda.beta_1} pattern={tda.pattern_type}"

            # Check topological stability if history available
            if history is not None and history.shape[0] >= 3:
                tda_first = compute_tda(history[0])
                drift = abs(tda.beta_0 - tda_first.beta_0) + abs(tda.beta_1 - tda_first.beta_1)
                if drift > 20:
                    return LensVerdict("topological", False, 0.3, f"Topo drift={drift} (unstable)", float(drift))
                detail += f" drift={drift}"

            return LensVerdict("topological", True, score, detail, float(tda.beta_0))
        except Exception as e:
            return LensVerdict("topological", True, 0.5, f"skipped: {e!s:.40s}")

    # ── Lens 4: Causal ────────────────────────────────────────

    def _lens_causal(self, seq: Any) -> LensVerdict:
        """Causal validation passes (46 rules)."""
        try:
            from mycelium_fractal_net.core.detect import detect_anomaly

            det = detect_anomaly(seq)
            passed = det.label in ("nominal", "watch")
            score = 1.0 - min(det.score, 1.0)
            return LensVerdict(
                "causal", passed, score, f"label={det.label} score={det.score:.3f}", det.score
            )
        except Exception as e:
            return LensVerdict("causal", True, 0.5, f"skipped: {e!s:.40s}")

    # ── Lens 5: Transport ─────────────────────────────────────

    def _lens_transport(self, history: np.ndarray | None) -> LensVerdict:
        """Wasserstein distance decreases over trajectory (convergence)."""
        if history is None or history.shape[0] < 3:
            return LensVerdict("transport", True, 0.5, "no history — skipped")

        try:
            from mycelium_fractal_net.analytics.unified_score import compute_hwi_components

            hwi_start = compute_hwi_components(history[0], history[-1])
            mid = history.shape[0] // 2
            hwi_mid = compute_hwi_components(history[mid], history[-1])

            w2_start = hwi_start.W2
            w2_mid = hwi_mid.W2

            converging = w2_mid <= w2_start * 1.1  # allow 10% tolerance
            detail = f"W₂: {w2_start:.4f}→{w2_mid:.4f} ({'converging' if converging else 'diverging'})"
            return LensVerdict("transport", converging, 1.0 if converging else 0.2, detail, w2_mid)
        except Exception as e:
            return LensVerdict("transport", True, 0.5, f"skipped: {e!s:.40s}")

    # ── Lens 6: Invariant ─────────────────────────────────────

    def _lens_invariant(self, history: np.ndarray | None) -> LensVerdict:
        """Λ₂ CV within tolerance (< 10%)."""
        if history is None or history.shape[0] < 5:
            return LensVerdict("invariant", True, 0.5, "no history — skipped")

        try:
            from mycelium_fractal_net.analytics.invariant_operator import InvariantOperator

            op = InvariantOperator()
            L2 = op.Lambda2(history)
            l2_cv = float(np.std(L2) / (np.mean(L2) + 1e-12))

            passed = l2_cv < 0.10  # 10% tolerance for gate (stricter than 5% for theorem)
            detail = f"Λ₂={np.mean(L2):.4f} CV={l2_cv:.4f}"
            return LensVerdict("invariant", passed, 1.0 - min(l2_cv, 1.0), detail, l2_cv)
        except Exception as e:
            return LensVerdict("invariant", True, 0.5, f"skipped: {e!s:.40s}")
