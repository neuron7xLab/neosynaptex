from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleState:
    name: str
    domain: str
    objectives: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    output_schema: tuple[str, ...]
    verification_gate: str
    escalation_trigger: str


@dataclass(frozen=True)
class RoleTransition:
    from_role: str
    to_role: str
    trigger: str
    required_input: str
    expected_output: str


class RoleStateEngine:
    def __init__(self, ordered_roles: tuple[str, ...]) -> None:
        self.ordered_roles = ordered_roles

    def validate_transition(self, from_role: str, to_role: str) -> None:
        i = self.ordered_roles.index(from_role)
        if i + 1 >= len(self.ordered_roles) or self.ordered_roles[i + 1] != to_role:
            raise ValueError("role transition is not allowed")
