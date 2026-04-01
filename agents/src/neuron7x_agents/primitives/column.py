"""
Cortical Column — adversarial multi-role reasoning primitive.

Inspired by cortical minicolumn architecture: multiple competing
processing units whose conflict produces robust output.

    Creator  → synthesize, generate, propose
    Critic   → attack, falsify, find flaws
    Auditor  → meta-assess, calibrate, verify coherence
    Verifier → deterministic check, reproducibility gate

The column scales with task complexity:
    TRIVIAL   → Creator only
    MODERATE  → Creator + Critic
    COMPLEX   → Full column (Creator + Critic + Auditor)
    CRITICAL  → Full column + uncertainty quantification + Verifier
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class Role(enum.Enum):
    """Roles within a cortical column."""

    CREATOR = "creator"
    CRITIC = "critic"
    AUDITOR = "auditor"
    VERIFIER = "verifier"


class Complexity(enum.Enum):
    """Task complexity determines column depth."""

    TRIVIAL = 1
    MODERATE = 2
    COMPLEX = 3
    CRITICAL = 4


@runtime_checkable
class RoleHandler(Protocol):
    """Interface for a role within the column."""

    def process(self, context: dict[str, Any]) -> dict[str, Any]:
        """Process input and return enriched context."""
        ...


@dataclass
class RoleResult:
    """Output from a single role's processing pass."""

    role: Role
    output: Any
    objections: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ColumnResult:
    """Aggregated output from a full column pass."""

    role_results: list[RoleResult]
    final_output: Any = None
    final_confidence: float = 0.0
    complexity: Complexity = Complexity.TRIVIAL
    iterations: int = 0

    @property
    def has_consensus(self) -> bool:
        """True if no unresolved objections remain."""
        return all(len(r.objections) == 0 for r in self.role_results)

    @property
    def min_confidence(self) -> float:
        """Minimum confidence across all roles — the bottleneck."""
        if not self.role_results:
            return 0.0
        return min(r.confidence for r in self.role_results)


class CorticalColumn:
    """
    Adversarial multi-role reasoning unit.

    The column runs Creator → Critic → Auditor → Verifier in sequence,
    where each role can challenge the previous one's output. The number
    of active roles scales with task complexity.

    Parameters
    ----------
    max_iterations : int
        Maximum adversarial loops before forced convergence.
    consensus_threshold : float
        Minimum confidence required for consensus (0.0-1.0).

    Examples
    --------
    >>> column = CorticalColumn()
    >>> result = column.run({"task": "evaluate claim X"}, Complexity.COMPLEX)
    >>> result.has_consensus
    True
    """

    def __init__(
        self,
        max_iterations: int = 3,
        consensus_threshold: float = 0.7,
    ) -> None:
        self.max_iterations = max_iterations
        self.consensus_threshold = consensus_threshold
        self._handlers: dict[Role, RoleHandler | None] = {
            Role.CREATOR: None,
            Role.CRITIC: None,
            Role.AUDITOR: None,
            Role.VERIFIER: None,
        }

    def register(self, role: Role, handler: RoleHandler) -> None:
        """Register a handler for a specific role."""
        self._handlers[role] = handler

    def _active_roles(self, complexity: Complexity) -> list[Role]:
        """Determine which roles are active for given complexity."""
        role_map: dict[Complexity, list[Role]] = {
            Complexity.TRIVIAL: [Role.CREATOR],
            Complexity.MODERATE: [Role.CREATOR, Role.CRITIC],
            Complexity.COMPLEX: [Role.CREATOR, Role.CRITIC, Role.AUDITOR],
            Complexity.CRITICAL: [
                Role.CREATOR,
                Role.CRITIC,
                Role.AUDITOR,
                Role.VERIFIER,
            ],
        }
        return role_map[complexity]

    def run(
        self,
        context: dict[str, Any],
        complexity: Complexity = Complexity.COMPLEX,
    ) -> ColumnResult:
        """
        Execute the column with adversarial role iteration.

        Parameters
        ----------
        context : dict
            Input context for the column to process.
        complexity : Complexity
            Task complexity level determining active roles.

        Returns
        -------
        ColumnResult
            Aggregated results from all active roles.
        """
        active = self._active_roles(complexity)
        results: list[RoleResult] = []
        current_context = dict(context)

        for iteration in range(self.max_iterations):
            results.clear()

            for role in active:
                handler = self._handlers[role]
                if handler is not None:
                    role_output = handler.process(current_context)
                    result = RoleResult(
                        role=role,
                        output=role_output.get("output"),
                        objections=role_output.get("objections", []),
                        confidence=role_output.get("confidence", 0.5),
                        metadata=role_output.get("metadata", {}),
                    )
                else:
                    # Default pass-through for unregistered roles
                    result = RoleResult(
                        role=role,
                        output=current_context.get("output"),
                        confidence=0.5,
                    )
                results.append(result)
                current_context[f"{role.value}_result"] = result

            column_result = ColumnResult(
                role_results=list(results),
                final_output=results[-1].output if results else None,
                final_confidence=min(r.confidence for r in results) if results else 0.0,
                complexity=complexity,
                iterations=iteration + 1,
            )

            if column_result.has_consensus:
                return column_result
            if column_result.min_confidence >= self.consensus_threshold:
                return column_result

        return column_result
