"""Reaction-Diffusion Engine — Turing Morphogenesis.

This module is the public facade. Implementation split across:
- reaction_diffusion_config.py: Config, metrics, parameter bounds, validation
- reaction_diffusion_compat.py: Legacy compat_ functions for numerics surface
- reaction_diffusion_engine.py (this file): ReactionDiffusionEngine class

Reference: MFN_MATH_MODEL.md Section 2 (Reaction-Diffusion Processes)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.neurochem.kinetics import (
    compute_excitability_offset_v,
    step_neuromodulation_state,
)
from mycelium_fractal_net.neurochem.state import NeuromodulationState
from mycelium_fractal_net.numerics.grid_ops import (
    compute_laplacian as numerics_compute_laplacian,
)

from .exceptions import NumericalInstabilityError
from .reaction_diffusion_compat import (
    compat_activator_inhibitor_step,
    compat_apply_growth_event,
    compat_apply_quantum_jitter,
    compat_apply_turing_to_field,
    compat_clamp_field,
    compat_diffusion_step,
    compat_full_step,
    compat_validate_cfl_condition,
)

# Re-export config, metrics, constants, and compat for backward compatibility
from .reaction_diffusion_config import (
    ALPHA_LTD_RATE,
    ALPHA_LTP_RATE,
    ALPHA_MAX,
    ALPHA_MIN,
    D_ACTIVATOR_MAX,
    D_ACTIVATOR_MIN,
    D_INHIBITOR_MAX,
    D_INHIBITOR_MIN,
    DEFAULT_D_ACTIVATOR,
    DEFAULT_D_INHIBITOR,
    DEFAULT_FIELD_ALPHA,
    DEFAULT_QUANTUM_JITTER_VAR,
    DEFAULT_R_ACTIVATOR,
    DEFAULT_R_INHIBITOR,
    DEFAULT_TURING_THRESHOLD,
    FIELD_V_MAX,
    FIELD_V_MIN,
    GRID_SIZE_MAX,
    GRID_SIZE_MIN,
    INITIAL_POTENTIAL_MEAN,
    INITIAL_POTENTIAL_STD,
    JITTER_VAR_MAX,
    JITTER_VAR_MIN,
    MAX_STABLE_DIFFUSION,
    R_ACTIVATOR_MAX,
    R_ACTIVATOR_MIN,
    R_INHIBITOR_MAX,
    R_INHIBITOR_MIN,
    TURING_THRESHOLD_MAX,
    TURING_THRESHOLD_MIN,
    BoundaryCondition,
    ReactionDiffusionConfig,
    ReactionDiffusionMetrics,
    _validate_diffusion_coefficient,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    # Re-exported from reaction_diffusion_config
    "ALPHA_MAX",
    "ALPHA_MIN",
    "DEFAULT_D_ACTIVATOR",
    "DEFAULT_D_INHIBITOR",
    "DEFAULT_FIELD_ALPHA",
    "DEFAULT_QUANTUM_JITTER_VAR",
    "DEFAULT_R_ACTIVATOR",
    "DEFAULT_R_INHIBITOR",
    "DEFAULT_TURING_THRESHOLD",
    "D_ACTIVATOR_MAX",
    "D_ACTIVATOR_MIN",
    "D_INHIBITOR_MAX",
    "D_INHIBITOR_MIN",
    "FIELD_V_MAX",
    "FIELD_V_MIN",
    "GRID_SIZE_MAX",
    "GRID_SIZE_MIN",
    "INITIAL_POTENTIAL_MEAN",
    "INITIAL_POTENTIAL_STD",
    "JITTER_VAR_MAX",
    "JITTER_VAR_MIN",
    "MAX_STABLE_DIFFUSION",
    "R_ACTIVATOR_MAX",
    "R_ACTIVATOR_MIN",
    "R_INHIBITOR_MAX",
    "R_INHIBITOR_MIN",
    "TURING_THRESHOLD_MAX",
    "TURING_THRESHOLD_MIN",
    "BoundaryCondition",
    "ReactionDiffusionConfig",
    "ReactionDiffusionEngine",
    "ReactionDiffusionMetrics",
    "_validate_diffusion_coefficient",
    # Re-exported from reaction_diffusion_compat
    "compat_activator_inhibitor_step",
    "compat_apply_growth_event",
    "compat_apply_quantum_jitter",
    "compat_apply_turing_to_field",
    "compat_clamp_field",
    "compat_diffusion_step",
    "compat_full_step",
    "compat_validate_cfl_condition",
]


class ReactionDiffusionEngine:
    """Engine for Turing reaction-diffusion pattern formation.

    Implements activator-inhibitor dynamics with spatial diffusion
    on a 2D lattice. Uses explicit Euler integration with CFL-stable
    parameters.

    Reference: MFN_MATH_MODEL.md Section 2
    """

    def __init__(self, config: ReactionDiffusionConfig | None = None) -> None:
        self.config = config or ReactionDiffusionConfig()
        self._metrics = ReactionDiffusionMetrics()
        self._rng = np.random.default_rng(self.config.random_seed)
        self._alpha_field: NDArray[np.floating] | None = None
        self._field: NDArray[np.floating] | None = None
        self._activator: NDArray[np.floating] | None = None
        self._inhibitor: NDArray[np.floating] | None = None
        self._neuro_state: NeuromodulationState | None = None

    @property
    def metrics(self) -> ReactionDiffusionMetrics:
        return self._metrics

    @property
    def field(self) -> NDArray[np.floating] | None:
        return self._field

    @property
    def activator(self) -> NDArray[np.floating] | None:
        return self._activator

    @property
    def inhibitor(self) -> NDArray[np.floating] | None:
        return self._inhibitor

    def reset(self) -> None:
        self._metrics = ReactionDiffusionMetrics()
        self._field = None
        self._activator = None
        self._inhibitor = None
        self._neuro_state = None
        self._alpha_field = None
        self._rng = np.random.default_rng(self.config.random_seed)

    def initialize_field(
        self,
        initial_potential_v: float = INITIAL_POTENTIAL_MEAN,
        initial_std_v: float = INITIAL_POTENTIAL_STD,
    ) -> NDArray[np.floating]:
        n = self.config.grid_size
        self._field = self._rng.normal(
            loc=initial_potential_v,
            scale=initial_std_v,
            size=(n, n),
        ).astype(np.float64)
        self._activator = self._rng.uniform(0, 0.1, size=(n, n)).astype(np.float64)
        self._inhibitor = self._rng.uniform(0, 0.1, size=(n, n)).astype(np.float64)
        self._neuro_state = NeuromodulationState.zeros((n, n))
        # Adaptive alpha field: each cell has its own diffusivity
        self._alpha_field = np.full((n, n), self.config.alpha, dtype=np.float64)
        return self._field

    def simulate(
        self,
        steps: int,
        turing_enabled: bool = True,
        return_history: bool = False,
    ) -> tuple[NDArray[np.floating], ReactionDiffusionMetrics]:
        if steps < 1:
            raise ValueError("steps must be at least 1")
        self.reset()
        if self._field is None:
            self.initialize_field()
        if self._field is None or self._activator is None or self._inhibitor is None:
            raise RuntimeError(
                "Field initialization failed: field, activator, or inhibitor is None"
            )

        history: NDArray[np.floating] | None = None
        if return_history:
            history = np.empty(
                (steps, self.config.grid_size, self.config.grid_size),
                dtype=self._field.dtype,
            )

        for step in range(steps):
            self._simulation_step(step, turing_enabled)
            if return_history and history is not None:
                history[step] = self._export_field()
            self._metrics.steps_computed += 1

        self._update_field_metrics()

        if return_history and history is not None:
            return history, self._metrics
        return self._export_field().copy(), self._metrics

    def _simulation_step(self, step: int, turing_enabled: bool) -> None:
        if self._field is None or self._activator is None or self._inhibitor is None:
            raise RuntimeError("Cannot run simulation step: engine not initialized")

        # Growth events
        if self._rng.random() < self.config.spike_probability:
            i = self._rng.integers(0, self.config.grid_size)
            j = self._rng.integers(0, self.config.grid_size)
            self._field[i, j] += float(self._rng.normal(loc=0.02, scale=0.005))
            self._metrics.growth_events += 1

        # Diffusion + reaction with adaptive alpha guard
        substeps, effective_dt = self._compute_alpha_guard_substeps()
        self._metrics.substeps_used = substeps
        self._metrics.effective_dt = effective_dt
        guard_triggered = substeps > 1
        self._metrics.alpha_guard_triggered = guard_triggered
        if guard_triggered:
            self._metrics.alpha_guard_triggers += 1
        for _ in range(substeps):
            laplacian = self._compute_laplacian(self._field)
            if self.config.adaptive_alpha and self._alpha_field is not None:
                self._field = self._field + self._alpha_field * effective_dt * laplacian
            else:
                self._field = self._field + self.config.alpha * effective_dt * laplacian
            if turing_enabled:
                self._turing_step(dt_scale=effective_dt)
                if self.config.adaptive_alpha:
                    self._adapt_alpha(dt_scale=effective_dt)

        # Neuromodulation
        self._apply_neuromodulation()

        # Intrinsic field jitter
        intrinsic_enabled = bool(self.config.quantum_jitter)
        intrinsic_var = float(self.config.jitter_var)
        spec = self.config.neuromodulation
        if spec is not None:
            intrinsic_enabled = bool(spec.intrinsic_field_jitter)
            intrinsic_var = float(spec.intrinsic_field_jitter_var)
        if intrinsic_enabled:
            safe_var = max(0.0, float(intrinsic_var))
            if safe_var > 0.0:
                self._field = self._field + self._rng.normal(
                    0, np.sqrt(safe_var), size=self._field.shape
                )

        # Soft-boundary damping + hard clamp
        self._field, pressure = self._apply_soft_boundary_damping(self._field)
        self._metrics.soft_boundary_pressure = pressure
        clamped_mask = (self._field > FIELD_V_MAX) | (self._field < FIELD_V_MIN)
        clamped = int(np.count_nonzero(clamped_mask))
        if clamped:
            np.clip(self._field, FIELD_V_MIN, FIELD_V_MAX, out=self._field)
        self._metrics.clamping_events += clamped
        self._metrics.hard_clamp_events += clamped

        if self.config.check_stability:
            self._check_stability(step)

    def _export_field(self) -> NDArray[np.floating]:
        if self._field is None:
            raise RuntimeError("Cannot export field: engine not initialized")
        observed: NDArray[np.floating] = self._field.copy()
        if self._neuro_state is None:
            return observed
        noise_gain = self._neuro_state.observation_noise_gain
        if np.any(noise_gain > 0):
            observed = np.asarray(
                observed + self._rng.normal(0.0, noise_gain, size=observed.shape),
                dtype=np.float64,
            )
            observed = np.clip(observed, FIELD_V_MIN, FIELD_V_MAX)
        return observed

    def _apply_neuromodulation(self) -> None:
        spec = self.config.neuromodulation
        if spec is None:
            return
        if self._field is None or self._activator is None:
            raise RuntimeError("Cannot apply neuromodulation: engine not initialized")
        if self._neuro_state is None:
            self._neuro_state = NeuromodulationState.zeros(self._field.shape)
        if not spec.enabled:
            return
        self._neuro_state = step_neuromodulation_state(
            self._neuro_state,
            dt_seconds=spec.dt_seconds,
            activator=self._activator.astype(np.float64),
            field=self._field.astype(np.float64),
            gabaa=spec.gabaa_tonic,
            serotonergic=spec.serotonergic,
            observation_noise=spec.observation_noise,
        )
        rest_offset_mv = (
            float(spec.gabaa_tonic.rest_offset_mv) if spec.gabaa_tonic is not None else 0.0
        )
        plasticity_scale = (
            float(spec.serotonergic.plasticity_scale) if spec.serotonergic is not None else 1.0
        )
        excitability_offset = compute_excitability_offset_v(
            self._neuro_state,
            activator=self._activator.astype(np.float64),
            baseline_activation_offset_mv=spec.baseline_activation_offset_mv,
            rest_offset_mv=rest_offset_mv,
            plasticity_scale=plasticity_scale,
        )
        centered = self._field - INITIAL_POTENTIAL_MEAN
        gain = np.clip(1.0 + self._neuro_state.effective_gain, 0.70, 1.30)
        shunt = np.clip(1.0 - self._neuro_state.effective_inhibition, 0.05, 1.0)
        self._field = INITIAL_POTENTIAL_MEAN + excitability_offset + centered * gain * shunt
        self._metrics.plasticity_index_mean = float(np.mean(self._neuro_state.plasticity_index))
        self._metrics.effective_inhibition_mean = float(
            np.mean(self._neuro_state.effective_inhibition)
        )
        self._metrics.effective_gain_mean = float(np.mean(self._neuro_state.effective_gain))
        self._metrics.observation_noise_gain_mean = float(
            np.mean(self._neuro_state.observation_noise_gain)
        )
        self._metrics.occupancy_resting_mean = float(np.mean(self._neuro_state.occupancy_resting))
        self._metrics.occupancy_active_mean = float(np.mean(self._neuro_state.occupancy_active))
        self._metrics.occupancy_desensitized_mean = float(
            np.mean(self._neuro_state.occupancy_desensitized)
        )
        self._metrics.occupancy_mass_error_max = self._neuro_state.occupancy_mass_error_max()
        self._metrics.excitability_offset_mean_v = float(np.mean(excitability_offset))

    def _compute_alpha_guard_substeps(self) -> tuple[int, float]:
        if not self.config.alpha_guard_enabled:
            return 1, 1.0
        threshold = float(np.clip(self.config.alpha_guard_threshold, 1e-6, 1.0))
        alpha_max = (
            float(np.max(self._alpha_field))
            if self.config.adaptive_alpha and self._alpha_field is not None
            else float(self.config.alpha)
        )
        max_coeff = max(
            alpha_max,
            float(self.config.d_activator),
            float(self.config.d_inhibitor),
        )
        allowed = MAX_STABLE_DIFFUSION * threshold
        if max_coeff <= allowed:
            return 1, 1.0
        substeps = int(np.ceil(max_coeff / allowed))
        return max(1, substeps), 1.0 / max(1, substeps)

    def _adapt_alpha(self, dt_scale: float = 1.0) -> None:
        """STDP-like adaptation of diffusivity field.

        Where Turing pattern is active (activator > threshold):
            strengthen diffusion (LTP) — pattern reinforces its own propagation.
        Where dormant (activator < threshold):
            weaken diffusion (LTD) — unused connections fade.

        Asymmetric A-/A+ = 1.2 (Bi & Poo 1998): LTD slightly stronger
        than LTP prevents runaway diffusion. Only genuinely active patterns
        maintain high diffusivity.
        """
        if self._alpha_field is None or self._activator is None:
            return
        above = self._activator - self.config.turing_threshold
        ltp = ALPHA_LTP_RATE * np.maximum(above, 0.0)
        ltd = ALPHA_LTD_RATE * np.maximum(-above, 0.0)
        self._alpha_field += (ltp - ltd) * dt_scale
        np.clip(self._alpha_field, ALPHA_MIN, ALPHA_MAX, out=self._alpha_field)

    def _apply_soft_boundary_damping(
        self, field: NDArray[np.floating]
    ) -> tuple[NDArray[np.floating], float]:
        damping = float(np.clip(self.config.soft_boundary_damping, 0.0, 1.0))
        upper_excess = np.maximum(field - FIELD_V_MAX, 0.0)
        lower_excess = np.maximum(FIELD_V_MIN - field, 0.0)
        pressure = float(np.mean(upper_excess + lower_excess))
        if damping <= 0.0:
            return field, pressure
        adjusted = field - damping * upper_excess + damping * lower_excess
        return np.asarray(adjusted, dtype=np.float64), pressure

    def _turing_step(self, dt_scale: float = 1.0) -> None:
        if self._activator is None or self._inhibitor is None or self._field is None:
            raise RuntimeError("Cannot run Turing step: engine not initialized")
        a_lap = self._compute_laplacian(self._activator)
        i_lap = self._compute_laplacian(self._inhibitor)
        da = (
            self.config.d_activator * a_lap
            + self.config.r_activator * (self._activator * (1 - self._activator) - self._inhibitor)
        ) * float(dt_scale)
        di = (
            self.config.d_inhibitor * i_lap
            + self.config.r_inhibitor * (self._activator - self._inhibitor)
        ) * float(dt_scale)
        self._activator = self._activator + da
        self._inhibitor = self._inhibitor + di
        turing_mask = self._activator > self.config.turing_threshold
        activation_count = int(np.sum(turing_mask))
        if activation_count > 0:
            self._field[turing_mask] += 0.005 * float(dt_scale)
            self._metrics.turing_activations += activation_count
        self._activator = np.clip(self._activator, 0.0, 1.0)
        self._inhibitor = np.clip(self._inhibitor, 0.0, 1.0)

    def _compute_laplacian(self, field: NDArray[np.floating]) -> NDArray[np.floating]:
        result: NDArray[np.floating] = numerics_compute_laplacian(
            field,
            boundary=self.config.boundary_condition.value,  # type: ignore[arg-type]  # BoundaryCondition enum compat
            check_stability=False,
            use_accel=self.config.accel_laplacian,
        )
        return result

    def _check_stability(self, step: int) -> None:
        for name, arr in [
            ("field", self._field),
            ("activator", self._activator),
            ("inhibitor", self._inhibitor),
        ]:
            if arr is None:
                continue
            nan_count = int(np.sum(np.isnan(arr)))
            inf_count = int(np.sum(np.isinf(arr)))
            if nan_count > 0:
                self._metrics.nan_detected = True
                if self._metrics.steps_to_instability is None:
                    self._metrics.steps_to_instability = step
                raise NumericalInstabilityError(
                    f"NaN values detected in {name}",
                    step=step,
                    field_name=name,
                    nan_count=nan_count,
                )
            if inf_count > 0:
                self._metrics.inf_detected = True
                if self._metrics.steps_to_instability is None:
                    self._metrics.steps_to_instability = step
                raise NumericalInstabilityError(
                    f"Inf values detected in {name}",
                    step=step,
                    field_name=name,
                    inf_count=inf_count,
                )

    def _update_field_metrics(self) -> None:
        if self._field is not None:
            self._metrics.field_min_v = float(np.min(self._field))
            self._metrics.field_max_v = float(np.max(self._field))
            self._metrics.field_mean_v = float(np.mean(self._field))
            self._metrics.field_std_v = float(np.std(self._field))
        if self._activator is not None:
            self._metrics.activator_mean = float(np.mean(self._activator))
        if self._inhibitor is not None:
            self._metrics.inhibitor_mean = float(np.mean(self._inhibitor))
        if self._neuro_state is not None:
            self._metrics.plasticity_index_mean = float(np.mean(self._neuro_state.plasticity_index))
            self._metrics.effective_inhibition_mean = float(
                np.mean(self._neuro_state.effective_inhibition)
            )
            self._metrics.effective_gain_mean = float(np.mean(self._neuro_state.effective_gain))
            self._metrics.observation_noise_gain_mean = float(
                np.mean(self._neuro_state.observation_noise_gain)
            )
            self._metrics.occupancy_resting_mean = float(
                np.mean(self._neuro_state.occupancy_resting)
            )
            self._metrics.occupancy_active_mean = float(np.mean(self._neuro_state.occupancy_active))
            self._metrics.occupancy_desensitized_mean = float(
                np.mean(self._neuro_state.occupancy_desensitized)
            )
            self._metrics.occupancy_mass_error_max = self._neuro_state.occupancy_mass_error_max()

    def validate_cfl_condition(self) -> bool:
        max_d = max(self.config.d_activator, self.config.d_inhibitor, self.config.alpha)
        return max_d <= MAX_STABLE_DIFFUSION
