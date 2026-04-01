"""Lever Registry — all modifiable parameters for interventions.

Every lever has bounds, default, step size, and cost model.
No parameter can be modified outside this registry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeverDefinition:
    """Definition of a single intervention lever."""

    name: str
    description: str
    default: float
    bounds: tuple[float, float]
    step: float
    cost_per_unit: float  # Cost per unit change from default
    plausibility: str = "physiological"

    def cost(self, proposed: float) -> float:
        """Compute cost of moving from default to proposed value."""
        return abs(proposed - self.default) * self.cost_per_unit

    def clamp(self, value: float) -> float:
        """Clamp value to bounds."""
        return max(self.bounds[0], min(self.bounds[1], value))

    def is_in_bounds(self, value: float) -> bool:
        return self.bounds[0] <= value <= self.bounds[1]


# ═══════════════════════════════════════════════════════════════
#  CANONICAL LEVER DEFINITIONS
# ═══════════════════════════════════════════════════════════════

_LEVER_REGISTRY: dict[str, LeverDefinition] = {
    "gabaa_concentration": LeverDefinition(
        name="gabaa_concentration",
        description="GABA-A agonist concentration (μM) — muscimol-like tonic inhibition",
        default=0.0,
        bounds=(0.0, 100.0),
        step=0.5,
        cost_per_unit=0.1,
        plausibility="pharmacological",
    ),
    "gabaa_shunt_strength": LeverDefinition(
        name="gabaa_shunt_strength",
        description="GABA-A shunting inhibition strength [0, 1]",
        default=0.0,
        bounds=(0.0, 1.0),
        step=0.05,
        cost_per_unit=0.5,
        plausibility="pharmacological",
    ),
    "serotonergic_gain": LeverDefinition(
        name="serotonergic_gain",
        description="Serotonergic gain fluidity coefficient",
        default=0.0,
        bounds=(0.0, 0.3),
        step=0.02,
        cost_per_unit=1.0,
        plausibility="pharmacological",
    ),
    "serotonergic_plasticity": LeverDefinition(
        name="serotonergic_plasticity",
        description="Serotonergic plasticity scale",
        default=1.0,
        bounds=(0.5, 3.0),
        step=0.1,
        cost_per_unit=0.3,
        plausibility="pharmacological",
    ),
    "diffusion_alpha": LeverDefinition(
        name="diffusion_alpha",
        description="Diffusion coefficient (CFL-bounded)",
        default=0.18,
        bounds=(0.05, 0.24),
        step=0.02,
        cost_per_unit=2.0,
        plausibility="computational",
    ),
    "spike_probability": LeverDefinition(
        name="spike_probability",
        description="Growth event probability per step",
        default=0.25,
        bounds=(0.0, 1.0),
        step=0.05,
        cost_per_unit=0.2,
        plausibility="physiological",
    ),
    "noise_std": LeverDefinition(
        name="noise_std",
        description="Observation noise standard deviation",
        default=0.0,
        bounds=(0.0, 0.01),
        step=0.001,
        cost_per_unit=0.1,
        plausibility="computational",
    ),
}


def get_lever(name: str) -> LeverDefinition:
    """Get lever definition by name. Raises KeyError if not registered."""
    if name not in _LEVER_REGISTRY:
        raise KeyError(f"Unknown lever {name!r}. Available: {sorted(_LEVER_REGISTRY)}")
    return _LEVER_REGISTRY[name]


def list_levers() -> list[str]:
    """List all registered lever names."""
    return sorted(_LEVER_REGISTRY)


def get_all_levers() -> dict[str, LeverDefinition]:
    """Get a copy of the full registry."""
    return dict(_LEVER_REGISTRY)


def validate_lever_values(values: dict[str, float]) -> list[str]:
    """Validate proposed lever values against registry bounds."""
    errors = []
    for name, value in values.items():
        if name not in _LEVER_REGISTRY:
            errors.append(f"Unknown lever: {name}")
            continue
        lever = _LEVER_REGISTRY[name]
        if not lever.is_in_bounds(value):
            errors.append(f"{name}={value} outside bounds [{lever.bounds[0]}, {lever.bounds[1]}]")
    return errors
