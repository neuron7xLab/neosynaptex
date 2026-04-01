from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_MEMORY_BYTES = int(1.4 * 1024**3)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class HomeostasisLimits:
    """Safe operating bounds for long-term stability."""

    max_memory_bytes: int = DEFAULT_MAX_MEMORY_BYTES
    memory_pressure_threshold: float = 0.8
    learning_rate_range: tuple[float, float] = (0.001, 0.5)
    modulation_range: tuple[float, float] = (0.0, 1.0)
    policy_strictness_range: tuple[float, float] = (0.0, 1.0)


def compute_memory_pressure(memory_used_bytes: float | None, limits: HomeostasisLimits) -> float:
    if memory_used_bytes is None or memory_used_bytes <= 0:
        return 0.0
    return _clamp(memory_used_bytes / float(limits.max_memory_bytes), 0.0, 1.0)


def apply_homeostatic_brake(value: float, pressure: float, threshold: float) -> float:
    if pressure <= threshold:
        return value
    reduction = 1.0 - min(0.4, (pressure - threshold) * 0.5)
    return value * reduction
