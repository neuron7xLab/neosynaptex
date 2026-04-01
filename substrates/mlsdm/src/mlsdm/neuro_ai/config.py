from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mlsdm.utils.config_schema import SystemConfig


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class NeuroHybridFlags:
    hybrid_enabled: bool = False
    learning_enabled: bool = False
    regime_enabled: bool = False
    module_overrides: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_env_and_config(cls, config: SystemConfig | None = None) -> NeuroHybridFlags:
        config_overrides = config.neuro_hybrid.module_overrides if config and hasattr(config, "neuro_hybrid") else {}
        hybrid = _env_bool("MLSDM_NEURO_HYBRID_ENABLE", False)
        learning = _env_bool("MLSDM_NEURO_LEARNING_ENABLE", False)
        regime = _env_bool("MLSDM_NEURO_REGIME_ENABLE", False)

        if config and hasattr(config, "neuro_hybrid"):
            hybrid = hybrid or bool(getattr(config.neuro_hybrid, "enable_hybrid", False))
            learning = learning or bool(getattr(config.neuro_hybrid, "enable_learning", False))
            regime = regime or bool(getattr(config.neuro_hybrid, "enable_regime", False))

        return cls(
            hybrid_enabled=hybrid,
            learning_enabled=learning and hybrid,
            regime_enabled=regime and hybrid,
            module_overrides=dict(config_overrides),
        )


__all__ = ["NeuroHybridFlags", " _env_bool".strip()]
