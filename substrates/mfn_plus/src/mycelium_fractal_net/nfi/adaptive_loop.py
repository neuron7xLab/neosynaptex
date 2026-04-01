"""NFIAdaptiveLoop — closed feedback loop: simulation → contract → theta → new simulation.

The open loop (closure.py) computes coherence and GNC state but does not feed back
into SimulationSpec. This module closes the ring: GNC theta drives the next simulation.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.field import SimulationSpec

from .closure import NFIClosureLoop
from .contract import NFIStateContract
from .gamma_probe import GammaEmergenceProbe, GammaEmergenceReport
from .theta_adapter import ThetaMapping

__all__ = ["AdaptiveRunResult", "NFIAdaptiveLoop"]


@dataclass
class AdaptiveRunResult:
    """Complete result of an adaptive run."""

    contracts: list[NFIStateContract]
    specs_history: list[SimulationSpec]
    coherence_trace: list[float]
    alpha_trace: list[float]
    gamma_report: GammaEmergenceReport
    converged: bool

    def summary(self) -> str:
        lines = [
            "═══ NFI Adaptive Run Result ═══",
            f"  Steps: {len(self.contracts)}",
            f"  Coherence: {self.coherence_trace[-1]:.3f} (final)"
            if self.coherence_trace else "  Coherence: N/A",
            f"  Alpha range: [{min(self.alpha_trace):.4f}, {max(self.alpha_trace):.4f}]"
            if self.alpha_trace else "  Alpha: N/A",
            f"  Converged: {self.converged}",
            f"  Gamma: {self.gamma_report.label}"
            f" (γ={self.gamma_report.gamma_value})",
        ]
        return "\n".join(lines)


class NFIAdaptiveLoop:
    """Closed-loop: simulate → contract → theta → next simulation.

    State:
        current_spec:   SimulationSpec  — current simulation config
        closure_loop:   NFIClosureLoop  — generates contracts
        theta_adapter:  ThetaMapping    — converts theta → spec
        history:        deque           — last capacity contracts
    """

    def __init__(
        self,
        base_spec: SimulationSpec,
        ca1_capacity: int = 64,
        theta_adapter: ThetaMapping | None = None,
        history_capacity: int = 200,
    ) -> None:
        self._base_spec = base_spec
        self._current_spec = base_spec
        self._closure = NFIClosureLoop(ca1_capacity=ca1_capacity)
        self._adapter = theta_adapter or ThetaMapping()
        self._history: deque[NFIStateContract] = deque(maxlen=history_capacity)
        self._step_count = 0

    @property
    def current_spec(self) -> SimulationSpec:
        return self._current_spec

    def step(self) -> tuple[NFIStateContract, SimulationSpec]:
        """Execute one closed-loop step.

        1. simulate(current_spec)
        2. contract = closure_loop.step(seq)
        3. history.append(contract)
        4. new_spec = theta_adapter.apply(contract.modulation.theta, base_spec)
        5. current_spec = new_spec
        6. return (contract, new_spec)
        """
        # Use step count as seed modifier for reproducible diversity
        spec_with_seed = SimulationSpec(
            grid_size=self._current_spec.grid_size,
            steps=self._current_spec.steps,
            alpha=self._current_spec.alpha,
            spike_probability=self._current_spec.spike_probability,
            turing_enabled=self._current_spec.turing_enabled,
            turing_threshold=self._current_spec.turing_threshold,
            quantum_jitter=self._current_spec.quantum_jitter,
            jitter_var=self._current_spec.jitter_var,
            seed=self._step_count * 7 + 13,
            neuromodulation=self._current_spec.neuromodulation,
        )

        seq = mfn.simulate(spec_with_seed)
        contract = self._closure.step(seq)
        self._history.append(contract)

        # Feedback: theta → next spec
        gnc_state = contract.modulation
        new_spec = self._adapter.apply(gnc_state.theta, self._base_spec)
        self._current_spec = new_spec
        self._step_count += 1

        return contract, new_spec

    def run(self, n_steps: int) -> AdaptiveRunResult:
        """Run n_steps of closed-loop adaptation."""
        contracts: list[NFIStateContract] = []
        specs: list[SimulationSpec] = []
        coherence_trace: list[float] = []
        alpha_trace: list[float] = []

        for _ in range(n_steps):
            contract, spec = self.step()
            contracts.append(contract)
            specs.append(spec)
            coherence_trace.append(contract.coherence)
            alpha_trace.append(spec.alpha)

        # Post-hoc gamma analysis over the full series
        probe = GammaEmergenceProbe(n_bootstrap=300, rng_seed=42)
        gamma_report = probe.analyze(contracts)

        # Convergence check: std of coherence over last 10 steps < 0.05
        converged = False
        if len(coherence_trace) >= 10:
            import numpy as np
            tail = coherence_trace[-10:]
            converged = float(np.std(tail)) < 0.05

        return AdaptiveRunResult(
            contracts=contracts,
            specs_history=specs,
            coherence_trace=coherence_trace,
            alpha_trace=alpha_trace,
            gamma_report=gamma_report,
            converged=converged,
        )
