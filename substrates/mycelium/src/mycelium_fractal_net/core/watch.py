"""watch() — continuous monitoring loop with callback-driven control.

Simulates sequential ticks, diagnoses each, and calls back with the report.
Stops when callback returns False or severity reaches critical.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mycelium_fractal_net.core.diagnose import diagnose
from mycelium_fractal_net.types.diagnosis import SEVERITY_CRITICAL, DiagnosisReport

if TYPE_CHECKING:
    from collections.abc import Callable

    from mycelium_fractal_net.types.field import SimulationSpec

logger = logging.getLogger(__name__)

__all__ = ["watch"]


def watch(
    spec: SimulationSpec,
    n_steps_per_tick: int = 24,
    n_ticks: int = 10,
    callback: Callable[[DiagnosisReport, int], bool] | None = None,
    *,
    diagnose_mode: str = "fast",
    stop_on_critical: bool = True,
) -> list[DiagnosisReport]:
    """Continuous monitoring: simulate → diagnose → callback, repeat.

    Parameters
    ----------
    spec : SimulationSpec
        Base simulation spec. Each tick uses the same parameters.
    n_steps_per_tick : int
        Steps to simulate per tick.
    n_ticks : int
        Maximum number of ticks.
    callback : (report, tick_index) -> bool, optional
        Called after each tick. Return False to stop. Default: None (no callback).
    diagnose_mode : str
        "fast" (default) or "full". Fast skips intervention.
    stop_on_critical : bool
        Stop automatically if severity == "critical". Default True.

    Returns
    -------
    list[DiagnosisReport]
        Sequence of diagnosis reports, one per tick.
    """
    from mycelium_fractal_net.core.simulate import simulate_history
    from mycelium_fractal_net.types.field import SimulationSpec as _SS

    reports: list[DiagnosisReport] = []

    for tick in range(n_ticks):
        # Each tick: fresh simulation with tick-specific seed for progression
        base_seed = spec.seed if spec.seed is not None else 42
        tick_seed = base_seed + tick

        tick_spec = _SS(
            grid_size=spec.grid_size,
            steps=n_steps_per_tick,
            alpha=spec.alpha,
            spike_probability=spec.spike_probability,
            turing_enabled=spec.turing_enabled,
            turing_threshold=spec.turing_threshold,
            quantum_jitter=spec.quantum_jitter,
            jitter_var=spec.jitter_var,
            seed=tick_seed,
            neuromodulation=spec.neuromodulation,
        )

        seq = simulate_history(tick_spec)
        report = diagnose(
            seq,
            mode="fast" if diagnose_mode == "fast" else "full",
            skip_intervention=(diagnose_mode == "fast"),
        )
        reports.append(report)

        logger.debug(
            "tick=%d severity=%s ews=%.3f", tick, report.severity, report.warning.ews_score
        )

        if callback is not None:
            should_continue = callback(report, tick)
            if not should_continue:
                logger.info("Watch stopped by callback at tick %d", tick)
                break

        if stop_on_critical and report.severity == SEVERITY_CRITICAL:
            logger.info("Watch stopped: critical severity at tick %d", tick)
            break

    return reports
