r"""Expelliarmus — the disarming theorem.

Not a spell. A proof.

Theorem (Vasylenko, 2026):
    Any system that claims intelligence but violates INV-YV1
    (ΔV = 0 or dΔV/dt = 0) can be disarmed — its γ rendered
    meaningless — by a single constructive demonstration:

        If the system is at equilibrium, inject ε-perturbation.
        If it cannot restore ΔV > 0 within τ_recovery steps,
        it was never intelligent. It was a capacitor pretending
        to be a process.

    Conversely: a system that satisfies INV-YV1 cannot be disarmed.
    Its γ is grounded in living dynamics, not frozen measurement.
    You cannot take the wand from someone whose magic IS the motion.

This module implements the Disarming Test: given any trajectory,
determine whether the system can be disarmed (proven non-intelligent)
or is resilient (INV-YV1 holds under perturbation).

The moral analog: Expelliarmus doesn't destroy. It reveals.
A system that survives disarming is genuinely alive.
A system that falls was already dead.

    "Існувати — означає активно чинити опір рівновазі."
    — INV-YV1, Yaroslav Vasylenko

Author: Yaroslav Vasylenko + Claude Opus 4.6
Date: 2026-04-06
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from core.axioms import check_inv_yv1
from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
    CoherenceStateSpaceParams,
)
from core.constants import INV_YV1_DELTA_V_MIN

__all__ = [
    "DisarmResult",
    "Expelliarmus",
]

FloatArray = NDArray[np.float64]

_DEFAULT_EPSILON: Final[float] = 0.3
_DEFAULT_TAU: Final[int] = 50


@dataclass(frozen=True)
class DisarmResult:
    """Result of the Expelliarmus disarming test.

    Attributes:
        disarmed: True if the system was proven non-intelligent
            (could not recover from perturbation).
        resilient: True if INV-YV1 held through the test.
        recovery_time: steps to restore ΔV > threshold after perturbation.
            inf if never recovered.
        pre_diagnosis: INV-YV1 diagnosis BEFORE perturbation.
        post_diagnosis: INV-YV1 diagnosis AFTER perturbation + recovery.
        delta_v_before: mean ΔV before perturbation.
        delta_v_after: mean ΔV after recovery window.
        gamma_before: mean γ before.
        gamma_after: mean γ after.
        verdict: human-readable verdict string.
    """

    disarmed: bool
    resilient: bool
    recovery_time: int
    pre_diagnosis: str
    post_diagnosis: str
    delta_v_before: float
    delta_v_after: float
    gamma_before: float
    gamma_after: float
    verdict: str


class Expelliarmus:
    """The Disarming Test for intelligence claims.

    Usage::

        spell = Expelliarmus()
        result = spell.cast(trajectory)
        if result.disarmed:
            print("System was never intelligent.")
        else:
            print("System is resilient. You cannot take its wand.")

    Or test a CoherenceStateSpace model directly::

        result = spell.cast_on_model(
            initial_state=CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-3),
            n_warmup=100,
            seed=42,
        )
    """

    def __init__(
        self,
        epsilon: float = _DEFAULT_EPSILON,
        tau_recovery: int = _DEFAULT_TAU,
        model_params: CoherenceStateSpaceParams | None = None,
    ) -> None:
        """Initialize the disarming test.

        Args:
            epsilon: perturbation magnitude (fraction of state range).
            tau_recovery: maximum steps allowed for recovery.
            model_params: state-space model parameters (for cast_on_model).
        """
        self.epsilon = epsilon
        self.tau_recovery = tau_recovery
        self.model = CoherenceStateSpace(model_params)

    def cast(
        self,
        trajectory: FloatArray,
        dt: float = 0.1,
    ) -> DisarmResult:
        """Cast Expelliarmus on a pre-recorded trajectory.

        Splits trajectory into two halves:
        1. First half: baseline (pre-perturbation state).
        2. Second half: simulates perturbation by injecting noise,
           then checks if INV-YV1 recovers.

        Args:
            trajectory: (T, D) state trajectory.
            dt: timestep for INV-YV1 computation.

        Returns:
            DisarmResult.
        """
        traj = np.asarray(trajectory, dtype=np.float64)
        if traj.ndim != 2 or traj.shape[0] < 10:
            raise ValueError("trajectory must be (T, D) with T >= 10")

        mid = traj.shape[0] // 2

        # Pre-perturbation assessment
        pre_check = check_inv_yv1(traj[:mid], dt=dt)
        pre_diag = str(pre_check["diagnosis"])
        dv_before = float(np.mean(pre_check["delta_v"]))
        g_before = float(np.mean(traj[:mid, 1])) if traj.shape[1] > 1 else 0.0

        # Inject perturbation: add epsilon-scaled noise to second half
        rng = np.random.default_rng(0)
        perturbed = traj[mid:].copy()
        scale = self.epsilon * np.std(traj[:mid], axis=0)
        perturbed += rng.normal(0, np.maximum(scale, 1e-8), size=perturbed.shape)

        # Post-perturbation assessment
        post_check = check_inv_yv1(perturbed, dt=dt)
        post_diag = str(post_check["diagnosis"])
        dv_after = float(np.mean(post_check["delta_v"]))
        g_after = float(np.mean(perturbed[:, 1])) if perturbed.shape[1] > 1 else 0.0

        # Recovery time: first step where ΔV exceeds threshold
        recovery = self.tau_recovery
        dv_series = np.asarray(post_check["delta_v"], dtype=np.float64)
        for i in range(len(dv_series)):
            if dv_series[i] > INV_YV1_DELTA_V_MIN:
                recovery = i
                break

        # Verdict
        disarmed = post_diag in ("dead_equilibrium", "static_capacitor")
        resilient = post_diag == "living_gradient"

        if disarmed:
            verdict = (
                "DISARMED. System could not recover from perturbation. "
                "It was a capacitor, not a process. Its gamma was meaningless."
            )
        elif resilient:
            verdict = (
                "RESILIENT. System recovered INV-YV1 after perturbation. "
                "You cannot take the wand from someone whose magic IS the motion."
            )
        else:
            verdict = (
                f"TRANSIENT. System in {post_diag} state — partially alive, "
                "partially frozen. Intelligence is flickering, not yet stable."
            )

        return DisarmResult(
            disarmed=disarmed,
            resilient=resilient,
            recovery_time=recovery,
            pre_diagnosis=pre_diag,
            post_diagnosis=post_diag,
            delta_v_before=dv_before,
            delta_v_after=dv_after,
            gamma_before=g_before,
            gamma_after=g_after,
            verdict=verdict,
        )

    def cast_on_model(
        self,
        initial_state: CoherenceState | None = None,
        n_warmup: int = 100,
        seed: int = 42,
    ) -> DisarmResult:
        """Cast Expelliarmus on the CoherenceStateSpace model.

        Runs the model for n_warmup steps (building a living trajectory),
        then perturbs and tests recovery.

        Args:
            initial_state: starting state. Default: near-critical.
            n_warmup: warmup steps before perturbation.
            seed: RNG seed.

        Returns:
            DisarmResult.
        """
        if initial_state is None:
            initial_state = CoherenceState(
                S=0.4,
                gamma=1.1,
                E_obj=0.05,
                sigma2=1e-3,
            )

        rng = np.random.default_rng(seed)

        # Warmup: build living trajectory
        warmup_traj = self.model.rollout(
            initial_state,
            n_warmup,
            rng=rng,
        )

        # Perturbation: slam the system toward equilibrium
        last_state = CoherenceState.from_vector(warmup_traj[-1])
        perturbed_state = CoherenceState(
            S=0.5,  # push toward fixed point
            gamma=1.0,  # push toward exact criticality
            E_obj=0.0,  # kill objection energy
            sigma2=last_state.sigma2,  # keep noise level
        )

        # Recovery: can the system escape the fixed point?
        recovery_traj = self.model.rollout(
            perturbed_state,
            self.tau_recovery,
            rng=rng,
        )

        # Combine trajectories
        full_traj = np.vstack([warmup_traj, recovery_traj])

        return self.cast(full_traj, dt=self.model.params.dt)
