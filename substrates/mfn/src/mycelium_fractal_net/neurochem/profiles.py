from __future__ import annotations

from copy import deepcopy
from typing import Any

_REQUIRED_TOP_LEVEL = {
    "profile",
    "profile_id",
    "evidence_version",
    "enabled",
    "dt_seconds",
    "intrinsic_field_jitter",
    "intrinsic_field_jitter_var",
    "baseline_activation_offset_mv",
    "tonic_inhibition_scale",
    "gain_fluidity_coeff",
    "gabaa_tonic",
    "serotonergic",
    "observation_noise",
}
_REQUIRED_GABAA = {
    "profile",
    "agonist_concentration_um",
    "resting_affinity_um",
    "active_affinity_um",
    "desensitization_rate_hz",
    "recovery_rate_hz",
    "shunt_strength",
    "rest_offset_mv",
    "baseline_activation_offset_mv",
    "tonic_inhibition_scale",
    "k_on",
    "k_off",
    "K_R",
    "c",
    "Q",
    "L",
    "binding_sites",
    "k_leak_reduction_fraction",
}
_REQUIRED_SEROTONERGIC = {
    "profile",
    "gain_fluidity_coeff",
    "reorganization_drive",
    "coherence_bias",
    "plasticity_scale",
    "connectivity_flattening_scale",
    "complexity_gain_scale",
}
_REQUIRED_OBSERVATION_NOISE = {"profile", "std", "temporal_smoothing"}


def _baseline_profile(name: str, *, enabled: bool = False) -> dict[str, Any]:
    return {
        "profile": name,
        "profile_id": name,
        "evidence_version": "mfn-neuromod-evidence-v2",
        "enabled": enabled,
        "dt_seconds": 1.0,
        "intrinsic_field_jitter": False,
        "intrinsic_field_jitter_var": 0.0005,
        "baseline_activation_offset_mv": 0.0,
        "tonic_inhibition_scale": 1.0,
        "gain_fluidity_coeff": 0.0,
        "gabaa_tonic": None,
        "serotonergic": None,
        "observation_noise": None,
    }


PROFILE_REGISTRY: dict[str, dict[str, Any]] = {
    "baseline_nominal": {
        **_baseline_profile("baseline_nominal", enabled=False),
    },
    "gabaa_tonic_muscimol_alpha1beta3": {
        **_baseline_profile("gabaa_tonic_muscimol_alpha1beta3", enabled=True),
        "tonic_inhibition_scale": 1.10,
        "gabaa_tonic": {
            "profile": "gabaa_tonic_muscimol_alpha1beta3",
            "agonist_concentration_um": 10.0,
            "resting_affinity_um": 0.30,
            "active_affinity_um": 0.25,
            "desensitization_rate_hz": 0.05,
            "recovery_rate_hz": 0.02,
            "shunt_strength": 0.42,
            "rest_offset_mv": -0.25,
            "baseline_activation_offset_mv": -0.10,
            "tonic_inhibition_scale": 1.10,
            "k_on": 0.22,
            "k_off": 0.06,
            "K_R": 0.45,
            "c": 1.05,
            "Q": 0.92,
            "L": 1.30,
            "binding_sites": 2,
            "k_leak_reduction_fraction": 0.18,
        },
    },
    "gabaa_tonic_extrasynaptic_delta_high_affinity": {
        **_baseline_profile("gabaa_tonic_extrasynaptic_delta_high_affinity", enabled=True),
        "tonic_inhibition_scale": 1.25,
        "gabaa_tonic": {
            "profile": "gabaa_tonic_extrasynaptic_delta_high_affinity",
            "agonist_concentration_um": 0.35,
            "resting_affinity_um": 0.10,
            "active_affinity_um": 0.08,
            "desensitization_rate_hz": 0.03,
            "recovery_rate_hz": 0.015,
            "shunt_strength": 0.50,
            "rest_offset_mv": -0.40,
            "baseline_activation_offset_mv": -0.15,
            "tonic_inhibition_scale": 1.25,
            "k_on": 0.30,
            "k_off": 0.04,
            "K_R": 0.10,
            "c": 0.95,
            "Q": 0.88,
            "L": 1.45,
            "binding_sites": 3,
            "k_leak_reduction_fraction": 0.24,
        },
    },
    "serotonergic_reorganization_candidate": {
        **_baseline_profile("serotonergic_reorganization_candidate", enabled=True),
        "gain_fluidity_coeff": 0.08,
        "serotonergic": {
            "profile": "serotonergic_reorganization_candidate",
            "gain_fluidity_coeff": 0.08,
            "reorganization_drive": 0.12,
            "coherence_bias": 0.02,
            "plasticity_scale": 1.30,
            "connectivity_flattening_scale": 0.22,
            "complexity_gain_scale": 0.18,
        },
    },
    "balanced_criticality_candidate": {
        **_baseline_profile("balanced_criticality_candidate", enabled=True),
        "intrinsic_field_jitter": True,
        "intrinsic_field_jitter_var": 0.0002,
        "tonic_inhibition_scale": 1.05,
        "gain_fluidity_coeff": 0.05,
        "gabaa_tonic": {
            "profile": "balanced_criticality_candidate",
            "agonist_concentration_um": 0.20,
            "resting_affinity_um": 0.25,
            "active_affinity_um": 0.22,
            "desensitization_rate_hz": 0.015,
            "recovery_rate_hz": 0.03,
            "shunt_strength": 0.18,
            "rest_offset_mv": -0.05,
            "baseline_activation_offset_mv": 0.0,
            "tonic_inhibition_scale": 1.05,
            "k_on": 0.16,
            "k_off": 0.10,
            "K_R": 0.25,
            "c": 1.00,
            "Q": 0.96,
            "L": 1.10,
            "binding_sites": 2,
            "k_leak_reduction_fraction": 0.08,
        },
        "serotonergic": {
            "profile": "balanced_criticality_candidate",
            "gain_fluidity_coeff": 0.05,
            "reorganization_drive": 0.05,
            "coherence_bias": 0.01,
            "plasticity_scale": 1.05,
            "connectivity_flattening_scale": 0.08,
            "complexity_gain_scale": 0.10,
        },
    },
    "observation_noise_gaussian_temporal": {
        **_baseline_profile("observation_noise_gaussian_temporal", enabled=True),
        "observation_noise": {
            "profile": "observation_noise_gaussian_temporal",
            "std": 0.0012,
            "temporal_smoothing": 0.35,
        },
    },
}


def _validate_required(name: str, payload: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"incomplete profile structure for {name}: missing {missing}")


def validate_profile_registry(registry: dict[str, dict[str, Any]] | None = None) -> None:
    registry = PROFILE_REGISTRY if registry is None else registry
    for name, profile in registry.items():
        _validate_required(name, profile, _REQUIRED_TOP_LEVEL)
        if profile["gabaa_tonic"] is not None:
            _validate_required(f"{name}.gabaa_tonic", profile["gabaa_tonic"], _REQUIRED_GABAA)
        if profile["serotonergic"] is not None:
            _validate_required(
                f"{name}.serotonergic", profile["serotonergic"], _REQUIRED_SEROTONERGIC
            )
        if profile["observation_noise"] is not None:
            _validate_required(
                f"{name}.observation_noise",
                profile["observation_noise"],
                _REQUIRED_OBSERVATION_NOISE,
            )


validate_profile_registry()


def list_profiles() -> list[str]:
    return sorted(PROFILE_REGISTRY)


_DEPRECATED_ALIASES: dict[str, str] = {
    "observation_noise_bold_like": "observation_noise_gaussian_temporal",
}


def get_profile(name: str) -> dict[str, Any]:
    if name in _DEPRECATED_ALIASES:
        import warnings

        new_name = _DEPRECATED_ALIASES[name]
        warnings.warn(
            f"Profile {name!r} is deprecated, use {new_name!r} instead.",
            FutureWarning,
            stacklevel=2,
        )
        name = new_name
    if name not in PROFILE_REGISTRY:
        raise KeyError(f"unknown neuromodulation profile: {name}")
    profile = deepcopy(PROFILE_REGISTRY[name])
    validate_profile_registry({name: profile})
    return profile
