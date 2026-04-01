"""Typed configuration for neuromodulation kinetics.

Frozen dataclasses with explicit defaults replace the previous TypedDict
approach, eliminating all ``dict`` and ``.get()`` usage in neurochem paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mycelium_fractal_net.neurochem.constants import (
    DEFAULT_DES_RATE_HZ,
    DEFAULT_K_OFF_HZ,
    DEFAULT_K_ON_HZ,
    DEFAULT_REC_RATE_HZ,
)


@dataclass(frozen=True)
class GABAAKineticsConfig:
    """GABA-A receptor kinetics configuration.

    All fields have physiologically meaningful defaults from constants.py.
    """

    profile: str = "baseline_nominal"
    agonist_concentration_um: float = 0.0
    resting_affinity_um: float = 0.0
    active_affinity_um: float = 0.0
    k_on: float = DEFAULT_K_ON_HZ
    k_off: float = DEFAULT_K_OFF_HZ
    desensitization_rate_hz: float = DEFAULT_DES_RATE_HZ
    recovery_rate_hz: float = DEFAULT_REC_RATE_HZ
    shunt_strength: float = 0.0
    rest_offset_mv: float = 0.0
    baseline_activation_offset_mv: float = 0.0
    tonic_inhibition_scale: float = 1.0
    K_R: float = 0.0
    c: float = 1.0
    Q: float = 1.0
    L: float = 1.0
    binding_sites: int = 1
    k_leak_reduction_fraction: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GABAAKineticsConfig:
        """Construct from dict, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass(frozen=True)
class SerotonergicKineticsConfig:
    """Serotonergic plasticity configuration."""

    plasticity_scale: float = 1.0
    reorganization_drive: float = 0.0
    gain_fluidity_coeff: float = 0.0
    coherence_bias: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SerotonergicKineticsConfig:
        """Construct from dict, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass(frozen=True)
class ObservationNoiseConfig:
    """Observation noise model configuration."""

    std: float = 0.0
    temporal_smoothing: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ObservationNoiseConfig:
        """Construct from dict, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass(frozen=True)
class NeuromodulationConfig:
    """Top-level neuromodulation configuration.

    Replaces the untyped ``dict[str, Any]`` that was previously passed through
    ``ReactionDiffusionConfig.neuromodulation``.
    """

    profile: str = "baseline_nominal"
    profile_id: str = "baseline_nominal"
    evidence_version: str = "mfn-neuromod-evidence-v2"
    enabled: bool = False
    dt_seconds: float = 1.0
    intrinsic_field_jitter: bool = False
    intrinsic_field_jitter_var: float = 0.0005
    baseline_activation_offset_mv: float = 0.0
    tonic_inhibition_scale: float = 1.0
    gain_fluidity_coeff: float = 0.0
    gabaa_tonic: GABAAKineticsConfig | None = None
    serotonergic: SerotonergicKineticsConfig | None = None
    observation_noise: ObservationNoiseConfig | None = None

    def __post_init__(self) -> None:
        if self.dt_seconds <= 0.0:
            raise ValueError("neuromodulation.dt_seconds must be > 0")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NeuromodulationConfig:
        """Construct from dict, converting sub-configs."""
        clean = dict(d)
        gabaa_raw = clean.pop("gabaa_tonic", None)
        sero_raw = clean.pop("serotonergic", None)
        obs_raw = clean.pop("observation_noise", None)

        gabaa: GABAAKineticsConfig | None = (
            GABAAKineticsConfig.from_dict(gabaa_raw)
            if isinstance(gabaa_raw, dict)
            else gabaa_raw
            if isinstance(gabaa_raw, GABAAKineticsConfig)
            else None
        )
        sero: SerotonergicKineticsConfig | None = (
            SerotonergicKineticsConfig.from_dict(sero_raw)
            if isinstance(sero_raw, dict)
            else sero_raw
            if isinstance(sero_raw, SerotonergicKineticsConfig)
            else None
        )
        obs: ObservationNoiseConfig | None = (
            ObservationNoiseConfig.from_dict(obs_raw)
            if isinstance(obs_raw, dict)
            else obs_raw
            if isinstance(obs_raw, ObservationNoiseConfig)
            else None
        )

        known = {f.name for f in cls.__dataclass_fields__.values()} - {
            "gabaa_tonic",
            "serotonergic",
            "observation_noise",
        }
        kwargs: dict[str, Any] = {k: v for k, v in clean.items() if k in known}
        return cls(gabaa_tonic=gabaa, serotonergic=sero, observation_noise=obs, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for backward compatibility."""
        result = {
            "profile": self.profile,
            "profile_id": self.profile_id,
            "evidence_version": self.evidence_version,
            "enabled": self.enabled,
            "dt_seconds": self.dt_seconds,
            "intrinsic_field_jitter": self.intrinsic_field_jitter,
            "intrinsic_field_jitter_var": self.intrinsic_field_jitter_var,
            "baseline_activation_offset_mv": self.baseline_activation_offset_mv,
            "tonic_inhibition_scale": self.tonic_inhibition_scale,
            "gain_fluidity_coeff": self.gain_fluidity_coeff,
            "gabaa_tonic": None,
            "serotonergic": None,
            "observation_noise": None,
        }
        if self.gabaa_tonic is not None:
            result["gabaa_tonic"] = {
                f.name: getattr(self.gabaa_tonic, f.name)
                for f in self.gabaa_tonic.__dataclass_fields__.values()
            }
        if self.serotonergic is not None:
            result["serotonergic"] = {
                f.name: getattr(self.serotonergic, f.name)
                for f in self.serotonergic.__dataclass_fields__.values()
            }
        if self.observation_noise is not None:
            result["observation_noise"] = {
                f.name: getattr(self.observation_noise, f.name)
                for f in self.observation_noise.__dataclass_fields__.values()
            }
        return result
