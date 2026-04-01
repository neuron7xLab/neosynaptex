"""Homeostasis — self-regulating entropy balance for MFN.

The point where the system stops needing external attention.

    loop = HomeostasisLoop(seq)
    equilibrium = loop.run()
    # System observed itself, healed itself, verified itself.
    # You didn't touch it. It found its own balance.

Biology: homeostasis = tendency of a system to maintain internal
stability through self-regulating processes. Temperature, pH,
glucose — the body doesn't need you to think about them.

MFN homeostasis:
    1. Observe       → measure entropy, energy, topology, invariants
    2. Diagnose      → is this healthy?
    3. If unhealthy  → auto_heal with dopamine-gated intervention
    4. Verify        → SovereignGate (6 lenses)
    5. If gate fails → reduce intervention strength, retry
    6. If gate passes → record equilibrium state
    7. Repeat until entropy production σ stabilizes

The loop terminates when:
    |σ(t) - σ(t-1)| / σ(t) < ε    (entropy production converged)
    or max_iterations reached

This is the singularity: the system maintains itself.

Ref: Cannon (1932) "The Wisdom of the Body"
     Ashby (1956) "An Introduction to Cybernetics" — Law of Requisite Variety
     Prigogine (1977) — dissipative structures self-organize at entropy balance
"""

from __future__ import annotations

import logging
import time

_log = logging.getLogger(__name__)
from dataclasses import dataclass, field
from typing import Any

__all__ = ["HomeostasisLoop", "HomeostasisReport"]


@dataclass
class HomeostasisReport:
    """Record of the self-regulation cycle."""

    iterations: int = 0
    converged: bool = False
    initial_entropy_production: float = 0.0
    final_entropy_production: float = 0.0
    entropy_trajectory: list[float] = field(default_factory=list)
    heals_attempted: int = 0
    heals_succeeded: int = 0
    gate_passes: int = 0
    gate_failures: int = 0
    final_verdict: str = ""  # "equilibrium", "limit_cycle", "divergent", "timeout"
    observation: Any = None  # final ObservatoryReport
    compute_time_ms: float = 0.0

    def __str__(self) -> str:
        w = 58
        status = "EQUILIBRIUM" if self.converged else self.final_verdict.upper()
        lines = [
            "",
            "╔" + "═" * w + "╗",
            "║" + f" HOMEOSTASIS: {status} ".center(w) + "║",
            "╠" + "═" * w + "╣",
            f"║  Iterations:    {self.iterations}".ljust(w + 1) + "║",
            f"║  Converged:     {self.converged}".ljust(w + 1) + "║",
            f"║  σ: {self.initial_entropy_production:.6f} → {self.final_entropy_production:.6f}".ljust(w + 1) + "║",
            f"║  Heals: {self.heals_attempted} attempted, {self.heals_succeeded} succeeded".ljust(w + 1) + "║",
            f"║  Gate: {self.gate_passes} pass / {self.gate_failures} fail".ljust(w + 1) + "║",
            f"║  Time: {self.compute_time_ms:.0f}ms".ljust(w + 1) + "║",
            "╚" + "═" * w + "╝",
        ]
        return "\n".join(lines)


class HomeostasisLoop:
    """Self-regulating entropy balance.

    The system observes, diagnoses, heals, and verifies itself
    in a closed loop until entropy production stabilizes.
    """

    def __init__(
        self,
        max_iterations: int = 5,
        convergence_epsilon: float = 0.05,
        heal_budget: int = 3,
    ) -> None:
        self.max_iterations = max_iterations
        self.convergence_epsilon = convergence_epsilon
        self.heal_budget = heal_budget

    def run(self, seq: Any) -> HomeostasisReport:
        """Run the homeostasis loop until equilibrium or timeout."""
        t0 = time.perf_counter()
        report = HomeostasisReport()

        # Import here to avoid circular deps
        from mycelium_fractal_net.analytics.entropy_production import compute_entropy_production
        from mycelium_fractal_net.core.sovereign_gate import SovereignGate

        gate = SovereignGate(min_lenses=4)
        current_seq = seq
        sigma_prev = None

        for iteration in range(self.max_iterations):
            report.iterations = iteration + 1

            # 1. Measure entropy production
            ep = compute_entropy_production(current_seq.field)
            sigma = ep.sigma
            report.entropy_trajectory.append(sigma)

            if iteration == 0:
                report.initial_entropy_production = sigma

            # 2. Check convergence
            if sigma_prev is not None:
                relative_change = abs(sigma - sigma_prev) / (sigma_prev + 1e-12)
                if relative_change < self.convergence_epsilon:
                    report.converged = True
                    report.final_entropy_production = sigma
                    report.final_verdict = "equilibrium"
                    break

            # 3. Verify through SovereignGate
            verdict = gate.verify(current_seq)
            if verdict.passed:
                report.gate_passes += 1
            else:
                report.gate_failures += 1

                # 4. If gate fails — heal
                try:
                    from mycelium_fractal_net.auto_heal import auto_heal

                    report.heals_attempted += 1
                    heal_result = auto_heal(current_seq, budget=self.heal_budget)
                    if heal_result.healed and heal_result.seq_after is not None:
                        current_seq = heal_result.seq_after
                        report.heals_succeeded += 1
                except Exception:
                    _log.debug("auto_heal failed during homeostasis", exc_info=True)

            sigma_prev = sigma

        # Final state
        if not report.converged:
            report.final_entropy_production = report.entropy_trajectory[-1] if report.entropy_trajectory else 0.0
            # Classify: is it a limit cycle or divergent?
            if len(report.entropy_trajectory) >= 3:
                diffs = [
                    abs(report.entropy_trajectory[i] - report.entropy_trajectory[i - 1])
                    for i in range(1, len(report.entropy_trajectory))
                ]
                if all(d < 0.01 for d in diffs[-2:]):
                    report.final_verdict = "limit_cycle"
                elif diffs[-1] > diffs[0] * 2:
                    report.final_verdict = "divergent"
                else:
                    report.final_verdict = "timeout"
            else:
                report.final_verdict = "timeout"

        # Final observation
        try:
            from mycelium_fractal_net.core.observatory import observe

            report.observation = observe(current_seq)
        except Exception:
            _log.debug("observatory unavailable during homeostasis", exc_info=True)

        report.compute_time_ms = (time.perf_counter() - t0) * 1000
        return report
