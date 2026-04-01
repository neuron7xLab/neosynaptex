from __future__ import annotations

from dataclasses import dataclass

from .contracts import TaskContract


@dataclass
class ModulationState:
    section_budget: int


class ConstraintModulator:
    def update(self, *, contract: TaskContract, current: ModulationState, delta: float, audit_failed_checks: int) -> tuple[ModulationState, dict[str, object]]:
        max_sections = len(contract.constraints["required_sections"])
        next_budget = current.section_budget
        action = "hold"

        if delta > contract.innovation_band.max_delta:
            next_budget = max(1, current.section_budget - 1)
            action = "tighten"
        elif delta < contract.innovation_band.min_delta:
            next_budget = min(max_sections, current.section_budget + 1)
            action = "expand"
        elif audit_failed_checks > 0:
            next_budget = min(max_sections, current.section_budget + 1)
            action = "repair"

        return ModulationState(section_budget=next_budget), {
            "action": action,
            "from_section_budget": current.section_budget,
            "to_section_budget": next_budget,
            "audit_failed_checks": audit_failed_checks,
        }
