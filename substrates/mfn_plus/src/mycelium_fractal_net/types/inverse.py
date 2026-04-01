"""InverseSynthesisResult — result of reverse parameter synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import SimulationSpec


@dataclass(frozen=True)
class InverseSynthesisResult:
    """Result of inverse_synthesis() — finding parameters that produce a target state."""

    found: bool
    synthesized_spec: SimulationSpec
    achieved_transition_type: str
    achieved_ews_score: float
    target_transition_type: str
    target_ews_score: float
    objective_value: float
    iterations_used: int
    search_trajectory: tuple[dict[str, Any], ...] = ()

    def summary(self) -> str:
        status = "found" if self.found else "not_found"
        params = []
        d = self.synthesized_spec.to_dict()
        if d.get("alpha", 0.18) != 0.18:
            params.append(f"alpha={d['alpha']:.3f}")
        if d.get("spike_probability", 0.25) != 0.25:
            params.append(f"spike={d['spike_probability']:.2f}")
        nm = d.get("neuromodulation")
        if nm:
            gt = nm.get("gabaa_tonic")
            if gt and gt.get("agonist_concentration_um", 0) > 0:
                params.append(f"gabaa={gt['agonist_concentration_um']:.1f}")
            sr = nm.get("serotonergic")
            if sr and sr.get("plasticity_scale", 1.0) != 1.0:
                params.append(f"sero={sr['plasticity_scale']:.1f}")
        via = ", ".join(params) if params else "defaults"
        return (
            f"[INVERSE:{status}] {self.achieved_transition_type} "
            f"ews={self.achieved_ews_score:.2f} via {via} "
            f"({self.iterations_used} iters)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "mfn-inverse-synthesis-v1",
            "found": self.found,
            "achieved_transition_type": self.achieved_transition_type,
            "achieved_ews_score": self.achieved_ews_score,
            "target_transition_type": self.target_transition_type,
            "target_ews_score": self.target_ews_score,
            "objective_value": self.objective_value,
            "iterations_used": self.iterations_used,
            "synthesized_spec": self.synthesized_spec.to_dict(),
        }
