"""Layer 3 — InterpretabilityLayer. Window W. Why is the system in this state?

Traces state shifts and operator attributions. Read-only.
Does NOT use gamma. Reads field states directly.

Ref: Vasylenko (2026), Sundararajan et al. (2017)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

__all__ = ["InterpretabilityLayer", "InterpretabilityTrace"]


@dataclass(frozen=True)
class InterpretabilityTrace:
    """Read-only trace of state evolution in a window."""

    dominant_operator: str
    operator_attributions: dict[str, float]
    critical_node: str
    state_shift_at: int  # step where max ||delta_state|| occurred
    shift_magnitude: float
    causal_chain: list[str] = field(default_factory=list)

    def explain(self) -> str:
        """Human-readable explanation of the state shift."""
        parts = [
            f"State shift detected at step {self.state_shift_at} "
            f"(magnitude={self.shift_magnitude:.4f}).",
            f"Dominant operator: {self.dominant_operator}.",
        ]
        if self.operator_attributions:
            top = sorted(
                self.operator_attributions.items(),
                key=lambda kv: abs(kv[1]),
                reverse=True,
            )[:3]
            attr_str = ", ".join(f"{k} ({v:+.3f})" for k, v in top)
            parts.append(f"Top attributions: {attr_str}.")
        if self.causal_chain:
            parts.append(f"Causal chain: {' -> '.join(self.causal_chain[:5])}.")
        return " ".join(parts)


class InterpretabilityLayer:
    """Traces why the system arrived at its current state.

    Does NOT use gamma. Reads activation vectors directly.
    """

    def trace(
        self,
        sequences: list[FieldSequence],
        window: int = 50,
    ) -> InterpretabilityTrace:
        """Analyze state evolution over a window.

        1. Find step with max ||delta_state|| -> state_shift_at
        2. Attribution: correlation(feature_delta, state_delta)
        3. Identify dominant operator and critical node
        """
        recent = sequences[-window:] if len(sequences) >= window else sequences

        if len(recent) < 2:
            return InterpretabilityTrace(
                dominant_operator="none",
                operator_attributions={},
                critical_node="none",
                state_shift_at=0,
                shift_magnitude=0.0,
            )

        fields = [np.asarray(s.field, dtype=np.float64) for s in recent]

        # Find max state shift
        deltas = []
        for i in range(1, len(fields)):
            delta = float(np.linalg.norm(fields[i] - fields[i - 1]))
            deltas.append(delta)

        max_idx = int(np.argmax(deltas))
        shift_magnitude = deltas[max_idx]
        state_shift_at = max_idx + 1  # relative to window start

        # Operator attribution via spatial analysis of the shift
        shift_field = fields[max_idx + 1] - fields[max_idx]
        attributions: dict[str, float] = {}

        # Diffusion operator: Laplacian contribution
        lap = (
            np.roll(shift_field, 1, 0) + np.roll(shift_field, -1, 0)
            + np.roll(shift_field, 1, 1) + np.roll(shift_field, -1, 1)
            - 4 * shift_field
        )
        attributions["diffusion"] = float(np.mean(np.abs(lap)))

        # Reaction operator: pointwise nonlinearity
        attributions["reaction"] = float(np.std(shift_field))

        # Gradient operator: spatial structure of shift
        grad_x = np.gradient(shift_field, axis=1)
        grad_y = np.gradient(shift_field, axis=0)
        attributions["gradient"] = float(np.mean(np.sqrt(grad_x**2 + grad_y**2)))

        # Stochastic: high-frequency component
        fft = np.fft.fft2(shift_field)
        hf_energy = float(np.sum(np.abs(fft[fft.shape[0] // 4 :, :]) ** 2))
        total_energy = float(np.sum(np.abs(fft) ** 2)) + 1e-12
        attributions["stochastic"] = hf_energy / total_energy

        # Dominant operator
        dominant = max(attributions, key=attributions.get)  # type: ignore[arg-type]

        # Critical node: pixel with largest shift
        flat_idx = int(np.argmax(np.abs(shift_field)))
        _h, w = shift_field.shape
        ci, cj = divmod(flat_idx, w)
        critical_node = f"pixel({ci},{cj})"

        # Causal chain: operators ordered by attribution
        chain = sorted(attributions, key=lambda k: abs(attributions[k]), reverse=True)

        return InterpretabilityTrace(
            dominant_operator=dominant,
            operator_attributions=attributions,
            critical_node=critical_node,
            state_shift_at=state_shift_at,
            shift_magnitude=shift_magnitude,
            causal_chain=chain,
        )
