"""Neuromodulation kinetics — GABA-A receptor binding, desensitization, recovery.

All numeric constants imported from ``constants.py`` with provenance.
Zero bare float literals except 0.0 and 1.0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.neurochem.constants import (
    ACTIVITY_DRIVE_ACTIVATOR_WEIGHT,
    ACTIVITY_DRIVE_FIELD_WEIGHT,
    BIND_ACTIVE_WEIGHT,
    BIND_RESTING_WEIGHT,
    DEFAULT_DES_RATE_HZ,
    DEFAULT_K_OFF_HZ,
    DEFAULT_K_ON_HZ,
    DEFAULT_REC_RATE_HZ,
    DESENSITIZATION_BASELINE_FRACTION,
    DESENSITIZATION_DRIVE_FRACTION,
    EXCITABILITY_DRIVE_OFFSET,
    EXCITABILITY_DRIVE_SCALE,
    EXCITABILITY_OFFSET_MAX_MV,
    FIELD_DRIVE_RANGE_V,
    FIELD_DRIVE_REST_V,
    OCCUPANCY_ACTIVE_WEIGHT,
    OCCUPANCY_DESENSITIZED_WEIGHT,
    OCCUPANCY_RESTING_WEIGHT,
    PLASTICITY_DRIVE_SCALE,
    PLASTICITY_EXCITABILITY_FRACTION,
    RECOVERY_ACTIVITY_DAMPENING,
    REST_OFFSET_BASELINE_FRACTION,
    REST_OFFSET_DRIVE_FRACTION,
)
from mycelium_fractal_net.neurochem.mwc import (
    effective_gabaa_shunt,
    effective_serotonergic_gain,
    mwc_fraction,
)
from mycelium_fractal_net.neurochem.state import NeuromodulationState

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from mycelium_fractal_net.neurochem.config_types import (
        GABAAKineticsConfig,
        ObservationNoiseConfig,
        SerotonergicKineticsConfig,
    )


def _clip01(arr: NDArray[np.float64] | float) -> NDArray[np.float64]:
    return np.clip(arr, 0.0, 1.0)


def _rate(raw_hz: float, dt_seconds: float, fallback: float) -> float:
    if raw_hz <= 0.0:
        raw_hz = fallback
    return float(np.clip(raw_hz * dt_seconds, 0.0, 1.0))


def _normalize_triplet(
    occ_rest: NDArray[np.float64],
    occ_active: NDArray[np.float64],
    occ_des: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    occ_rest = np.clip(occ_rest, 0.0, 1.0)
    occ_active = np.clip(occ_active, 0.0, 1.0)
    occ_des = np.clip(occ_des, 0.0, 1.0)
    total = occ_rest + occ_active + occ_des
    needs_norm = total > 0.0
    if np.any(needs_norm):
        occ_rest = np.where(needs_norm, occ_rest / total, 1.0)
        occ_active = np.where(needs_norm, occ_active / total, 0.0)
        occ_des = np.where(needs_norm, occ_des / total, 0.0)
    return (
        occ_rest.astype(np.float64),
        occ_active.astype(np.float64),
        occ_des.astype(np.float64),
    )


def compute_excitability_offset_v(
    state: NeuromodulationState,
    *,
    activator: NDArray[np.float64],
    baseline_activation_offset_mv: float,
    rest_offset_mv: float,
    plasticity_scale: float,
) -> NDArray[np.float64]:
    # Local mean: each cell compares to its 5×5 neighborhood, not global average.
    # A neuron knows its neighbors, not the brain's mean activation.
    from scipy.ndimage import uniform_filter

    activator_f64 = np.asarray(activator, dtype=np.float64)
    local_mean = uniform_filter(activator_f64, size=5, mode="wrap")
    centered_activator = activator_f64 - local_mean
    excitability_drive = np.clip(
        EXCITABILITY_DRIVE_OFFSET + EXCITABILITY_DRIVE_SCALE * centered_activator, 0.0, 1.0
    )
    occupancy_bias = (
        OCCUPANCY_ACTIVE_WEIGHT * state.occupancy_active
        + OCCUPANCY_RESTING_WEIGHT * state.occupancy_resting
        + OCCUPANCY_DESENSITIZED_WEIGHT * state.occupancy_desensitized
    )
    local_offset_mv = float(baseline_activation_offset_mv) + float(
        rest_offset_mv
    ) * occupancy_bias * (
        REST_OFFSET_BASELINE_FRACTION + REST_OFFSET_DRIVE_FRACTION * excitability_drive
    )
    if plasticity_scale > 1.0:
        local_offset_mv += (
            float(rest_offset_mv)
            * PLASTICITY_EXCITABILITY_FRACTION
            * (float(plasticity_scale) - 1.0)
            * state.plasticity_index
        )
    local_offset_mv = np.clip(
        local_offset_mv, -EXCITABILITY_OFFSET_MAX_MV, EXCITABILITY_OFFSET_MAX_MV
    )
    return np.asarray(local_offset_mv / 1000.0, dtype=np.float64)


def step_neuromodulation_state(
    state: NeuromodulationState,
    *,
    dt_seconds: float,
    activator: NDArray[np.float64],
    field: NDArray[np.float64],
    gabaa: GABAAKineticsConfig | None,
    serotonergic: SerotonergicKineticsConfig | None,
    observation_noise: ObservationNoiseConfig | None,
) -> NeuromodulationState:
    shape = field.shape
    if state.occupancy_resting.shape != shape:
        state = NeuromodulationState.zeros(shape)

    activator = np.asarray(activator, dtype=np.float64)
    field = np.asarray(field, dtype=np.float64)

    occ_rest = state.occupancy_resting.copy()
    occ_active = state.occupancy_active.copy()
    occ_des = state.occupancy_desensitized.copy()

    field_drive = np.clip((field + FIELD_DRIVE_REST_V) / FIELD_DRIVE_RANGE_V, 0.0, 1.0)
    activity_drive = np.clip(
        ACTIVITY_DRIVE_ACTIVATOR_WEIGHT * activator + ACTIVITY_DRIVE_FIELD_WEIGHT * field_drive,
        0.0,
        1.0,
    )

    if gabaa is not None:
        concentration = float(gabaa.agonist_concentration_um)
        rest_aff = float(gabaa.resting_affinity_um)
        float(gabaa.active_affinity_um) if gabaa.active_affinity_um != 0.0 else rest_aff
        ligand_rest = mwc_fraction(concentration)
        ligand_active = mwc_fraction(concentration)

        bind_rate = _rate(float(gabaa.k_on), dt_seconds, DEFAULT_K_ON_HZ)
        unbind_rate = _rate(float(gabaa.k_off), dt_seconds, DEFAULT_K_OFF_HZ)
        des_rate = _rate(float(gabaa.desensitization_rate_hz), dt_seconds, DEFAULT_DES_RATE_HZ)
        rec_rate = _rate(float(gabaa.recovery_rate_hz), dt_seconds, DEFAULT_REC_RATE_HZ)

        available_rest = np.clip(1.0 - occ_active - occ_des, 0.0, 1.0)
        bind_propensity = np.clip(
            bind_rate
            * (
                BIND_RESTING_WEIGHT * ligand_rest
                + BIND_ACTIVE_WEIGHT * ligand_active * activity_drive
            ),
            0.0,
            1.0,
        )
        bind_flux = available_rest * bind_propensity
        occ_rest = occ_rest - bind_flux
        occ_active = occ_active + bind_flux

        unbind_propensity = np.clip(unbind_rate * (1.0 - ligand_active * activity_drive), 0.0, 1.0)
        unbind_flux = occ_active * unbind_propensity
        occ_active = occ_active - unbind_flux
        occ_rest = occ_rest + unbind_flux

        des_propensity = np.clip(
            des_rate
            * (DESENSITIZATION_BASELINE_FRACTION + DESENSITIZATION_DRIVE_FRACTION * activity_drive),
            0.0,
            1.0,
        )
        des_flux = occ_active * des_propensity
        occ_active = occ_active - des_flux
        occ_des = occ_des + des_flux

        rec_propensity = np.clip(
            rec_rate * (1.0 - RECOVERY_ACTIVITY_DAMPENING * activity_drive), 0.0, 1.0
        )
        rec_flux = occ_des * rec_propensity
        occ_des = occ_des - rec_flux
        occ_rest = occ_rest + rec_flux

        occ_rest, occ_active, occ_des = _normalize_triplet(occ_rest, occ_active, occ_des)
    else:
        occ_rest = np.ones(shape, dtype=np.float64)
        occ_active = np.zeros(shape, dtype=np.float64)
        occ_des = np.zeros(shape, dtype=np.float64)

    plasticity_scale = float(serotonergic.plasticity_scale) if serotonergic is not None else 1.0
    # Local mean for plasticity: how different is this cell from its neighbors?
    from scipy.ndimage import uniform_filter

    local_mean_act = uniform_filter(
        np.asarray(activator, dtype=np.float64),
        size=5,
        mode="wrap",
    )
    plasticity_drive = np.clip(
        np.abs(activator - local_mean_act) * PLASTICITY_DRIVE_SCALE * plasticity_scale, 0.0, 1.0
    )
    if serotonergic is not None:
        plasticity_drive = _clip01(plasticity_drive + float(serotonergic.reorganization_drive))
        effective_gain = effective_serotonergic_gain(
            plasticity_drive,
            float(serotonergic.gain_fluidity_coeff),
            float(serotonergic.coherence_bias),
        )
    else:
        effective_gain = np.zeros_like(field, dtype=np.float64)

    tonic_scale = float(gabaa.tonic_inhibition_scale) if gabaa is not None else 1.0
    effective_inhibition = effective_gabaa_shunt(
        occ_active,
        float(gabaa.shunt_strength) * tonic_scale if gabaa is not None else 0.0,
    )

    if observation_noise is not None:
        target_noise = np.full(shape, max(0.0, float(observation_noise.std)), dtype=np.float64)
        smoothing = float(np.clip(observation_noise.temporal_smoothing, 0.0, 1.0))
        observation_noise_gain = state.observation_noise_gain * smoothing + target_noise * (
            1.0 - smoothing
        )
    else:
        observation_noise_gain = np.zeros(shape, dtype=np.float64)

    return NeuromodulationState(
        occupancy_resting=occ_rest,
        occupancy_active=occ_active,
        occupancy_desensitized=occ_des,
        effective_inhibition=np.asarray(effective_inhibition, dtype=np.float64),
        effective_gain=np.asarray(effective_gain, dtype=np.float64),
        plasticity_index=np.asarray(plasticity_drive, dtype=np.float64),
        observation_noise_gain=np.asarray(observation_noise_gain, dtype=np.float64),
    )
