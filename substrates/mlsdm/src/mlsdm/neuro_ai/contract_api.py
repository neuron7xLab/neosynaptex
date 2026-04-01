from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mlsdm.neuro_ai.adapters import NeuroAIStepMetrics

if TYPE_CHECKING:
    from collections.abc import Mapping

    import numpy as np


@dataclass(frozen=True)
class NeuroSignalPack:
    observation: np.ndarray | float
    prediction: np.ndarray | float | None = None
    risk: float | None = None
    dt: float = 1.0
    context: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class NeuroOutputPack:
    output: Any
    regime: Any | None
    prediction_error: Any | None
    stability: float | None
    metadata: NeuroContractMetadata | None = None


@dataclass(frozen=True)
class NeuroContractMetadata:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    invariants: tuple[str, ...]
    bounds: tuple[float, float] | None
    time_constant: float | None
    failure_mode: str


class NeuroModuleAdapter:
    """
    Thin compatibility wrapper that enforces the hybrid contract without changing legacy APIs.

    - When `enable` is False, the wrapped module is invoked in its legacy mode.
    - When `enable` is True, the module receives prediction/risk context when supported.
    """

    def __init__(self, module: Any, *, metadata: NeuroContractMetadata, enable: bool = False) -> None:
        self.module = module
        self.metadata = metadata
        self.enable = enable

    def _invoke(self, signals: NeuroSignalPack) -> NeuroAIStepMetrics | Any:
        event = signals.observation
        predicted = signals.prediction
        risk = signals.risk

        try:
            return self.module.update(event, predicted=predicted, observed=event, risk=risk)
        except TypeError:
            return self.module.update(event)

    def step(self, signals: NeuroSignalPack) -> NeuroOutputPack:
        regime = None
        prediction_error = None
        stability = None
        output_state: Any = None

        restore_flags = None
        has_adapt = hasattr(self.module, "enable_adaptation")
        has_regime = hasattr(self.module, "enable_regime_switching")
        if not self.enable and (has_adapt or has_regime):
            restore_flags = (
                getattr(self.module, "enable_adaptation", None) if has_adapt else None,
                getattr(self.module, "enable_regime_switching", None) if has_regime else None,
            )
            if has_adapt:
                self.module.enable_adaptation = False
            if has_regime:
                self.module.enable_regime_switching = False

        try:
            result = self._invoke(signals)
        finally:
            if restore_flags is not None:
                if has_adapt:
                    self.module.enable_adaptation = restore_flags[0]
                if has_regime:
                    self.module.enable_regime_switching = restore_flags[1]

        if isinstance(result, NeuroAIStepMetrics):
            regime = result.regime
            prediction_error = result.prediction_error
            stability = result.oscillation_score
        elif isinstance(result, tuple):
            output_state = result

        if output_state is None and hasattr(self.module, "state"):
            output_state = self.module.state()
        if output_state is None and hasattr(self.module, "get_state"):
            output_state = self.module.get_state()

        return NeuroOutputPack(
            output=output_state,
            regime=regime,
            prediction_error=prediction_error,
            stability=stability,
            metadata=self.metadata,
        )


__all__ = [
    "NeuroContractMetadata",
    "NeuroModuleAdapter",
    "NeuroOutputPack",
    "NeuroSignalPack",
]
