"""Neuromodulatory Digital Twin — D_T component of GNC+ program spine.

Replaces the stub LongitudinalDigitalTwin with a live prediction engine.

Prediction strategy:
    Short horizon (h<=3):  linear extrapolation of axis trends
    Medium horizon (h<=10): weighted moving average + Omega interactions
    Long horizon (h>10):   exponential return to attractor (baseline 0.5)

Falsification: F4 — if MAE(predicted) < Var(history) → manifold has predictive power.

Ref: Vasylenko (2026) GNC+ program spine
     Friston et al. (2012) Neural Comput 24:2201
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .gnc import _IDX, _OMEGA, MODULATORS, THETA, GNCState, compute_gnc_state

__all__ = ["NeuromodulatoryDigitalTwin"]


class NeuromodulatoryDigitalTwin:
    """D_T: Longitudinal Digital Twin for GNC+.

    Tracks manifold trajectory and predicts future states.

    Usage:
        twin = NeuromodulatoryDigitalTwin()
        for state in observed_states:
            twin.update(state)
        predicted = twin.predict(horizon=5)
    """

    def __init__(self, window: int = 10) -> None:
        self.window = window
        self.history: list[GNCState] = []
        self.mfn_history: list[dict[str, Any]] = []

    def update(
        self, gnc_state: GNCState, mfn_metrics: dict[str, Any] | None = None
    ) -> NeuromodulatoryDigitalTwin:
        """Add new state to history. Chainable."""
        self.history.append(gnc_state)
        self.mfn_history.append(mfn_metrics or {})
        return self

    def predict(self, horizon: int = 1) -> GNCState:
        """Predict state at t+horizon. Requires min 3 states in history."""
        if len(self.history) < 3:
            msg = f"Need >= 3 history states, got {len(self.history)}"
            raise ValueError(msg)

        if horizon <= 3:
            return self._predict_linear(horizon)
        if horizon <= 10:
            return self._predict_weighted(horizon)
        return self._predict_attractor(horizon)

    def predict_trajectory(self, horizon: int = 5) -> list[GNCState]:
        """Predict sequence of states [t+1, ..., t+horizon]."""
        return [self.predict(h) for h in range(1, horizon + 1)]

    def _predict_linear(self, horizon: int) -> GNCState:
        """Short horizon: linear extrapolation of recent trends."""
        recent = self.history[-min(self.window, len(self.history)) :]
        n = len(recent)

        predicted_mods: dict[str, float] = {}
        for m in MODULATORS:
            values = [s.modulators[m] for s in recent]
            if n >= 2:
                slope = (values[-1] - values[0]) / max(n - 1, 1)
                pred = values[-1] + slope * horizon
            else:
                pred = values[-1]
            predicted_mods[m] = float(np.clip(pred, 0.0, 1.0))

        return compute_gnc_state(predicted_mods)

    def _predict_weighted(self, horizon: int) -> GNCState:
        """Medium horizon: WMA + Omega interactions."""
        recent = self.history[-min(self.window, len(self.history)) :]
        n = len(recent)

        # Weighted average (more recent = higher weight)
        weights = np.linspace(0.5, 1.0, n)
        weights /= weights.sum()

        predicted_mods: dict[str, float] = {}
        for m in MODULATORS:
            values = np.array([s.modulators[m] for s in recent])
            wma = float(np.dot(weights, values))

            # Omega correction: interactions push toward coupled attractors
            levels = np.array([wma if mm == m else recent[-1].modulators[mm] for mm in MODULATORS])
            omega_effect = float((_OMEGA @ levels)[_IDX[m]])
            wma += omega_effect * 0.02 * horizon

            predicted_mods[m] = float(np.clip(wma, 0.0, 1.0))

        return compute_gnc_state(predicted_mods)

    def _predict_attractor(self, horizon: int) -> GNCState:
        """Long horizon: exponential decay toward baseline 0.5."""
        last = self.history[-1]
        decay = np.exp(-0.1 * (horizon - 10))

        predicted_mods: dict[str, float] = {}
        for m in MODULATORS:
            dev = last.modulators[m] - 0.5
            predicted_mods[m] = float(np.clip(0.5 + dev * decay, 0.0, 1.0))

        return compute_gnc_state(predicted_mods)

    def validate(self) -> dict[str, Any]:
        """F4 falsification check: does Psi have predictive power?

        Leave-one-out: predict each state from preceding states.
        If MAE < Var(history) → F4 = True (manifold is predictive).
        """
        if len(self.history) < 5:
            return {
                "f4_pass": False, "mae": 0.0, "variance": 0.0,
                "predictive_power": 0.0, "n_samples": len(self.history),
                "reason": "insufficient history (need >= 5)",
            }

        errors: list[float] = []
        for i in range(3, len(self.history)):
            # Build sub-twin from history[:i]
            sub = NeuromodulatoryDigitalTwin(self.window)
            for s in self.history[:i]:
                sub.update(s)
            predicted = sub.predict(horizon=1)
            actual = self.history[i]

            # MAE across all modulator levels
            mae = np.mean([
                abs(predicted.modulators[m] - actual.modulators[m])
                for m in MODULATORS
            ])
            errors.append(float(mae))

        # Variance of history
        all_levels = np.array([
            [s.modulators[m] for m in MODULATORS]
            for s in self.history
        ])
        variance = float(np.mean(np.var(all_levels, axis=0)))

        mean_mae = float(np.mean(errors))
        f4_pass = mean_mae < variance if variance > 1e-6 else False
        power = float(1.0 - mean_mae / (variance + 1e-12)) if variance > 1e-6 else 0.0

        return {
            "f4_pass": f4_pass,
            "mae": round(mean_mae, 6),
            "variance": round(variance, 6),
            "predictive_power": round(max(0.0, power), 4),
            "n_samples": len(self.history),
        }

    def summary(self) -> str:
        v = self.validate() if len(self.history) >= 5 else {"f4_pass": "N/A", "mae": 0}
        return (
            f"[Digital Twin] history={len(self.history)} "
            f"F4={'PASS' if v['f4_pass'] is True else 'FAIL'} "
            f"MAE={v['mae']}"
        )

    def predict_with_ac(
        self,
        horizon: int = 5,
        ccp_D_f: float | None = None,
        ccp_R: float | None = None,
        seed: int | None = None,
    ) -> tuple[list[GNCState], list[bool]]:
        """Trajectory prediction with A_C integration.

        At each step, generates candidate variations around the predicted state.
        If activation conditions are met, A_C selects the best candidate.

        Returns
        -------
        (trajectory, ac_activated_flags)
        """
        if len(self.history) < 3:
            msg = "Need >= 3 history states for prediction"
            raise ValueError(msg)

        from .axiomatic_choice import AxiomaticChoiceOperator, SelectionStrategy

        operator = AxiomaticChoiceOperator(
            strategy=SelectionStrategy.ENSEMBLE, seed=seed,
        )
        rng = np.random.default_rng(seed)
        trajectory: list[GNCState] = []
        ac_flags: list[bool] = []
        prev_state = self.history[-1]

        for h in range(1, horizon + 1):
            predicted = self.predict(h)

            # Generate variations around prediction
            candidates = [predicted]
            for noise_std in (0.05, 0.10):
                noisy = GNCState(
                    modulators=dict(predicted.modulators),
                    theta={
                        t: float(np.clip(
                            predicted.theta[t] + rng.normal(0, noise_std),
                            0.1, 0.9,
                        ))
                        for t in THETA
                    },
                    context=dict(predicted.context),
                    environment=dict(predicted.environment),
                )
                candidates.append(noisy)

            selected = operator.select(
                candidates=candidates,
                prev_state=prev_state,
                ccp_D_f=ccp_D_f,
                ccp_R=ccp_R,
            )

            if selected is not None:
                trajectory.append(selected)
                ac_flags.append(True)
            else:
                trajectory.append(predicted)
                ac_flags.append(False)

            prev_state = trajectory[-1]

        return trajectory, ac_flags

    @classmethod
    def from_gnc_states(cls, states: list[GNCState], window: int = 10) -> NeuromodulatoryDigitalTwin:
        """Initialize twin from existing sequence."""
        twin = cls(window=window)
        for s in states:
            twin.update(s)
        return twin
